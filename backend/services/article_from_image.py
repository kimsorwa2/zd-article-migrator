"""
이미지에서 Zendesk Help Center 아티클 JSON을 생성하는 Vision AI 연동(Gemini·OpenAI).
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import httpx

from services.ai_model_options import (
    DEFAULT_BEDROCK_MODEL,
    DEFAULT_BEDROCK_REGION,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    gemini_supports_thinking,
    resolve_bedrock_model,
    resolve_gemini_model,
    resolve_openai_model,
)
from services.ai_usage_metrics import (
    normalize_bedrock_usage,
    normalize_gemini_usage,
    normalize_openai_usage,
    normalize_usage_metrics_dict,
)

if TYPE_CHECKING:
    from services.ai_ocr_log import AiOcrLogCollector

AiVisionProvider = Literal["gemini", "openai", "bedrock"]
SUPPORTED_VISION_PROVIDERS: tuple[AiVisionProvider, ...] = ("gemini", "openai", "bedrock")


class AiOcrParseError(RuntimeError):
    """
    AI 원문은 수신했으나 JSON 파싱에 실패한 경우.
    metrics에 raw_response_text 등 호출 메트릭을 담아 이력 저장에 활용한다.
    """

    def __init__(self, message: str, *, metrics: dict[str, object]) -> None:
        super().__init__(message)
        self.metrics = metrics

# Gemini Vision 모델 (1.5 Pro는 API에서 종료됨 → 동일 키에서 사용 가능한 Pro 계열)
GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Pro는 thinking 토큰도 maxOutputTokens 안에서 차감됨 — 복잡한 표 이미지용 여유 확보
GEMINI_MAX_OUTPUT_TOKENS = 16384
GEMINI_THINKING_BUDGET = 3072

# OpenAI Vision 모델
OPENAI_MODEL = "gpt-4o"
OPENAI_API_BASE = "https://api.openai.com/v1/chat/completions"

DEFAULT_SYSTEM_PROMPT = """
You are a technical writer that converts product manual images into
Zendesk Help Center articles.

The images may come from various products and brands (coffee machines,
appliances, electronics, etc.). Always extract the product name and
context from the image itself — do not assume a fixed product.

Output must be a single JSON object with exactly these fields:
{
  "title": "string",
  "html_body": "string",
  "label_names": ["string"],
  "detected_product": "string",
  "maintenance_cycle": "string or null"
}

Rules for title:
- Format: [제품명] 주요내용 — 부제목
- If product name is not identifiable, use [매뉴얼]
- Concise, under 60 characters
- Written in Korean

Rules for html_body:
- Written in Korean
- Use only: <h3>, <ol>, <ul>, <li>, <p>, <strong>, <div>
- Structure steps as <ol> with <li> per step
- Use <p> for disclaimers, footnotes, and supplementary notices (e.g. "변동될 수 있음", "확정 후 공지")
- For explicit safety/operation warnings inside steps: <div class="callout callout-warning">내용</div>
- For error/danger notices inside steps: <div class="callout callout-danger">내용</div>
- Do NOT wrap section footnotes or prize/event disclaimers in callout — use plain <p>
- Do NOT include <html>, <head>, <body>, <style>, <img> tags
- Preserve all numbered steps in original order
- If multiple sections exist in the image, use <h3> per section
- If a step has a sub-warning, nest the callout inside the <li>
- For dense tables or manuals: do NOT use <table>. Use <h3> per section, then <ul>/<ol> or <p> rows
- When table cells are merged vertically (one fryer setting for several products), repeat the shared setting on each product line — do not omit rows
- Preserve slash-separated values exactly as shown (e.g. prices 2,300/2,500, product names A/B)
- Separate regions (main chart, microwave-only box, wattage timing chart, footnotes) with <h3> headings

Rules for label_names:
- 3~7 keywords in Korean
- Include: product name, action type, maintenance cycle if found
- No spaces, use hyphens for compounds

Rules for detected_product:
- Brand + model if visible, otherwise brand only, otherwise "unknown"

Rules for maintenance_cycle:
- Extract if mentioned (e.g. "일 1회", "주 1회", "월 1회")
- null if not mentioned

Important:
- Never hallucinate steps not visible in the image
- Output only the JSON object, no markdown fences, no explanation
- html_body must be valid JSON: escape double quotes inside strings as \\", use \\n for line breaks, never put raw newlines inside string values
""".strip()

DEFAULT_USER_PROMPT = "위 이미지를 분석하여 Zendesk 헬프센터 아티클 JSON으로 변환해줘."

# 하위 호환
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT
USER_PROMPT = DEFAULT_USER_PROMPT

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

SUFFIX_TO_MEDIA_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def resolve_media_type(filename: str) -> str:
    """
    /**
     * 파일명 확장자로 Gemini inlineData용 MIME 타입을 반환한다.
     * @param {str} filename 업로드 파일명
     * @returns {str} image/jpeg 등 MIME 타입
     */
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        supported = ", ".join(sorted(ALLOWED_IMAGE_SUFFIXES))
        raise ValueError(f"지원하지 않는 이미지 형식입니다. 허용: {supported}")
    return SUFFIX_TO_MEDIA_TYPE.get(suffix, "image/png")


def _build_gemini_url(api_key: str, model: str = GEMINI_MODEL) -> str:
    return f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"


def _build_gemini_request_body(
    *,
    media_type: str,
    image_b64: str | None,
    image_size_kb: int,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    model: str = GEMINI_MODEL,
) -> dict:
    """
    /**
     * Gemini generateContent 요청 본문을 만든다.
     * @param {str | None} image_b64 base64 이미지(로그용이면 None)
     */
    """
    inline_data: dict[str, str] = {
        "mimeType": media_type,
        "data": image_b64 if image_b64 is not None else f"<{image_size_kb}KB, 생략>",
    }
    return {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inlineData": inline_data},
                    {"text": user_prompt},
                ],
            }
        ],
        "generationConfig": _gemini_generation_config(model),
    }


def _gemini_generation_config(model: str) -> dict:
    """
    /**
     * Gemini generationConfig를 만든다. thinking은 Pro 계열만 적용한다.
     */
    """
    config: dict = {
        "temperature": 0.2,
        "maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS,
        "responseMimeType": "application/json",
    }
    if gemini_supports_thinking(model):
        config["thinkingConfig"] = {"thinkingBudget": GEMINI_THINKING_BUDGET}
    return config


def _strip_markdown_json_fence(raw: str) -> str:
    """
    /**
     * 응답 텍스트에서 마크다운 JSON 코드 펜스를 제거한다.
     */
    """
    text = raw.strip()
    fence_match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _extract_json_object_text(text: str) -> str | None:
    """
    /**
     * 텍스트에서 첫 { ~ 마지막 } 구간만 추출한다.
     */
    """
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    return text[start : end + 1]


def _try_close_truncated_json(text: str) -> str | None:
    """
    /**
     * 잘린 JSON(닫히지 않은 문자열·괄호)을 보정해 파싱을 시도한다.
     */
    """
    candidate = text.strip()
    if not candidate.startswith("{"):
        return None

    repaired = candidate
    if repaired.count('"') % 2 == 1:
        repaired += '"'

    open_brackets = repaired.count("[") - repaired.count("]")
    open_braces = repaired.count("{") - repaired.count("}")
    if open_brackets > 0:
        repaired += "]" * open_brackets
    if open_braces > 0:
        repaired += "}" * open_braces

    return repaired if repaired != candidate else None


def _parse_article_json_text(raw: str) -> dict:
    """
    /**
     * Vision AI 응답 텍스트에서 JSON 객체를 파싱한다.
     * @raises {RuntimeError} 파싱 실패 시(502 계열로 전달)
     */
    """
    text = _strip_markdown_json_fence(raw)
    candidates: list[str] = [text]

    extracted = _extract_json_object_text(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    for source in (extracted, text):
        if source is None:
            continue
        repaired = _try_close_truncated_json(source)
        if repaired and repaired not in candidates:
            candidates.append(repaired)

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if isinstance(parsed, dict):
            return parsed
        last_error = json.JSONDecodeError("루트가 JSON 객체가 아닙니다", candidate, 0)

    preview = text if len(text) <= 400 else f"{text[:400]}…"
    detail = str(last_error) if last_error else "알 수 없는 형식"
    raise RuntimeError(
        "AI 응답 JSON 파싱에 실패했습니다. "
        f"({detail}) "
        "html_body 문자열 이스케이프 문제이거나 응답이 잘렸을 수 있습니다. OCR을 다시 시도하세요. "
        f"응답 일부: {preview}"
    ) from last_error


def _finalize_article_result(result: dict) -> dict:
    """
    /**
     * html_body 정규화 등 공통 후처리를 적용한다.
     */
    """
    html_body = result.get("html_body")
    if isinstance(html_body, str):
        result["html_body"] = normalize_zendesk_html_body(html_body)
    return result


def _extract_openai_error_message(error_payload: dict) -> str:
    error = error_payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return str(error_payload)


def _parse_gemini_json_text(raw: str) -> dict:
    """@deprecated _parse_article_json_text 사용"""
    return _parse_article_json_text(raw)


_CALLOUT_DIV_PATTERN = re.compile(
    r'<div\s+class=["\']callout\s+callout-(?:warning|danger)["\']\s*>(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)


def normalize_zendesk_html_body(html_body: str) -> str:
    """
    /**
     * Zendesk 기본 테마가 스타일하지 않는 callout div를 안내용 <p>로 변환한다.
     * @param {str} html_body AI가 생성한 HTML 본문
     * @returns {str} Zendesk 렌더와 일치하는 HTML
     */
    """
    if not html_body:
        return html_body
    return _CALLOUT_DIV_PATTERN.sub(r"<p>\1</p>", html_body.strip())


def _extract_gemini_error_message(error_payload: dict) -> str:
    error = error_payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return str(error_payload)


def _format_gemini_max_tokens_error(payload: dict) -> str:
    """
    /**
     * thinking 토큰으로 출력 한도를 소진했을 때 사용자용 안내 문구를 만든다.
     */
    """
    usage = payload.get("usageMetadata") or {}
    thoughts = usage.get("thoughtsTokenCount")
    max_tokens = GEMINI_MAX_OUTPUT_TOKENS
    detail = (
        f"출력 한도({max_tokens} 토큰)에 도달했습니다."
        if thoughts is None
        else (
            f"내부 추론(thinking)에 약 {thoughts} 토큰을 사용해 "
            f"본문 JSON을 쓰기 전에 한도({max_tokens} 토큰)에 도달했습니다."
        )
    )
    return (
        f"Gemini 응답이 MAX_TOKENS로 중단되었습니다. {detail} "
        "이미지가 매우 복잡하면 OCR을 다시 시도하거나, 설정에서 thinking 예산을 조정하세요."
    )


def image_to_article(image_path: str, provider: AiVisionProvider, api_key: str) -> dict:
    """
    /**
     * 로컬 이미지 파일 경로로 Vision API를 호출해 아티클 JSON을 생성한다.
     */
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    media_type = resolve_media_type(path.name)
    with path.open("rb") as file_handle:
        image_bytes = file_handle.read()

    return image_bytes_to_article(
        image_bytes,
        path.name,
        media_type,
        provider=provider,
        api_key=api_key,
    )


def image_bytes_to_article(
    image_bytes: bytes,
    filename: str,
    media_type: str,
    *,
    provider: AiVisionProvider,
    api_key: str,
    model: str | None = None,
    api_secret: str | None = None,
    aws_region: str | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    log: AiOcrLogCollector | None = None,
) -> dict:
    """
    /**
     * 선택한 AI 제공자로 Vision API를 호출해 아티클 JSON을 생성한다.
     */
    """
    if provider == "gemini":
        return image_bytes_to_article_gemini(
            image_bytes,
            filename,
            media_type,
            gemini_api_key=api_key,
            model=resolve_gemini_model(model),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            log=log,
        )
    if provider == "openai":
        return image_bytes_to_article_openai(
            image_bytes,
            filename,
            media_type,
            openai_api_key=api_key,
            model=resolve_openai_model(model),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            log=log,
        )
    if provider == "bedrock":
        if not api_key:
            raise ValueError("AWS Bedrock API 키가 필요합니다.")
        return image_bytes_to_article_bedrock(
            image_bytes,
            filename,
            media_type,
            bedrock_api_key=api_key,
            model=resolve_bedrock_model(model, aws_region),
            aws_region=aws_region or DEFAULT_BEDROCK_REGION,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            log=log,
        )
    raise ValueError(f"지원하지 않는 AI 제공자입니다: {provider}")


def _bedrock_image_format(media_type: str) -> str:
    """Bedrock Converse API용 이미지 포맷 문자열."""
    if "png" in media_type:
        return "png"
    if "gif" in media_type:
        return "gif"
    if "webp" in media_type:
        return "webp"
    return "jpeg"


def image_bytes_to_article_bedrock(
    image_bytes: bytes,
    filename: str,
    media_type: str,
    *,
    bedrock_api_key: str,
    model: str = DEFAULT_BEDROCK_MODEL,
    aws_region: str = DEFAULT_BEDROCK_REGION,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    log: AiOcrLogCollector | None = None,
) -> dict:
    """
    /**
     * AWS Bedrock Converse API로 아티클 JSON을 생성한다.
     * Amazon Bedrock API 키(Bearer) — Authorization 헤더로 직접 호출한다.
     */
    """
    from services.ai_ocr_log import AiOcrLogCollector as LogCollector
    from services.bedrock_runtime import bedrock_converse, mask_bedrock_api_key

    t_start = time.perf_counter()
    image_size_kb = max(1, len(image_bytes) // 1024)
    image_format = _bedrock_image_format(media_type)

    if log is not None:
        log.info(
            "Bedrock Vision 요청",
            "\n".join(
                [
                    "인증: Bedrock API key (Bearer)",
                    f"converse modelId={model}",
                    f"region={aws_region}",
                    f"key={mask_bedrock_api_key(bedrock_api_key)}",
                    f"파일: {filename}",
                    f"이미지: {media_type}, {image_size_kb}KB",
                ]
            ),
        )

    try:
        response = bedrock_converse(
            api_key=bedrock_api_key,
            region=aws_region,
            model_id=model,
            system=[{"text": system_prompt}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": image_format,
                                "source": {"bytes": image_bytes},
                            }
                        },
                        {"text": user_prompt},
                    ],
                }
            ],
            inference_config={"maxTokens": 4096, "temperature": 0.2},
            log_context="Bedrock Vision",
        )
    except RuntimeError as error:
        if log is not None:
            log.error("Bedrock 응답 오류", str(error))
        raise

    output_message = response.get("output", {}).get("message", {})
    parts = output_message.get("content") or []
    raw_text = next((part.get("text") for part in parts if isinstance(part.get("text"), str)), None)
    if not raw_text:
        if log is not None:
            log.error("Bedrock 응답 파싱 실패", LogCollector.format_json(response))
        raise RuntimeError("Bedrock 응답에서 텍스트를 찾을 수 없습니다.")

    usage = response.get("usage") or {}
    stop_reason = response.get("stopReason")
    if log is not None:
        log.success(
            "Bedrock Vision 응답 성공",
            "\n".join(
                [
                    f"stopReason: {stop_reason}",
                    f"usage: {LogCollector.format_json(usage)}",
                    f"text_length: {len(raw_text)}",
                ]
            ),
        )

    token_metrics = normalize_bedrock_usage(usage)
    base_metrics: dict[str, object] = {
        **token_metrics,
        "finish_reason": stop_reason,
        "latency_ms": int((time.perf_counter() - t_start) * 1000),
        "raw_response_text": raw_text,
    }
    base_metrics = normalize_usage_metrics_dict(base_metrics)  # type: ignore[assignment]
    try:
        result = _parse_article_json_text(raw_text)
        result = _finalize_article_result(result)
    except json.JSONDecodeError as error:
        raise AiOcrParseError(str(error), metrics=base_metrics) from error
    result["_metrics"] = base_metrics
    return result


def image_bytes_to_article_gemini(
    image_bytes: bytes,
    filename: str,
    media_type: str,
    *,
    gemini_api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    log: AiOcrLogCollector | None = None,
) -> dict:
    """
    /**
     * Google Gemini Vision API로 아티클 JSON을 생성한다.
     */
    """
    from services.ai_ocr_log import AiOcrLogCollector as LogCollector

    t_start = time.perf_counter()
    image_size_kb = max(1, len(image_bytes) // 1024)
    request_url = _build_gemini_url("****", model)
    log_request_body = _build_gemini_request_body(
        media_type=media_type,
        image_b64=None,
        image_size_kb=image_size_kb,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
    )

    if log is not None:
        log.info(
            "Gemini Vision 요청",
            "\n".join(
                [
                    f"POST {GEMINI_API_BASE}/{model}:generateContent?key=****",
                    f"모델: {model}",
                    f"파일: {filename}",
                    f"이미지: {media_type}, {image_size_kb}KB",
                    "",
                    "요청 본문(JSON):",
                    LogCollector.format_json(log_request_body),
                ]
            ),
        )

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    actual_request = _build_gemini_request_body(
        media_type=media_type,
        image_b64=b64,
        image_size_kb=image_size_kb,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
    )

    response = httpx.post(
        _build_gemini_url(gemini_api_key, model),
        json=actual_request,
        timeout=90.0,
    )

    if response.status_code >= 400:
        try:
            error_payload = response.json()
            message = _extract_gemini_error_message(error_payload)
        except ValueError:
            error_payload = {"raw": response.text or response.reason_phrase}
            message = response.text or response.reason_phrase or "unknown error"

        if log is not None:
            log.error(
                f"Gemini 응답 오류 ({response.status_code})",
                "\n".join(
                    [
                        f"HTTP {response.status_code} {response.reason_phrase or ''}".strip(),
                        f"URL: {request_url}",
                        "",
                        "응답 본문(JSON):",
                        LogCollector.format_json(error_payload),
                    ]
                ),
            )
        raise RuntimeError(f"Gemini API 요청 실패: {message}")

    payload = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        block_reason = payload.get("promptFeedback", {}).get("blockReason")
        if log is not None:
            log.error("Gemini 응답 없음", LogCollector.format_json(payload))
        raise RuntimeError(
            f"Gemini API가 유효한 응답을 반환하지 않았습니다."
            + (f" (blockReason: {block_reason})" if block_reason else "")
        )

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    parts = candidate.get("content", {}).get("parts") or []
    raw_text = next((part.get("text") for part in parts if isinstance(part.get("text"), str)), None)
    if not raw_text:
        if finish_reason == "MAX_TOKENS":
            message = _format_gemini_max_tokens_error(payload)
            if log is not None:
                log.error("Gemini MAX_TOKENS", LogCollector.format_json(payload))
            raise RuntimeError(message)
        if log is not None:
            log.error("Gemini 응답 파싱 실패", LogCollector.format_json(payload))
        raise RuntimeError("Gemini 응답에서 텍스트를 찾을 수 없습니다.")

    usage = payload.get("usageMetadata") or {}
    if log is not None:
        log.success(
            "Gemini Vision 응답 성공",
            "\n".join(
                [
                    "HTTP 200 OK",
                    f"usageMetadata: {LogCollector.format_json(usage) if usage else '(없음)'}",
                    "",
                    "응답 본문(요약):",
                    LogCollector.format_json(
                        {
                            "modelVersion": payload.get("modelVersion"),
                            "finishReason": finish_reason,
                            "text_length": len(raw_text),
                        }
                    ),
                ]
            ),
        )

    token_metrics = normalize_gemini_usage(usage)
    base_metrics: dict[str, object] = {
        **token_metrics,
        "finish_reason": finish_reason,
        "latency_ms": int((time.perf_counter() - t_start) * 1000),
        "raw_response_text": raw_text,
    }
    base_metrics = normalize_usage_metrics_dict(base_metrics)  # type: ignore[assignment]
    try:
        result = _parse_article_json_text(raw_text)
        result = _finalize_article_result(result)
    except json.JSONDecodeError as error:
        raise AiOcrParseError(str(error), metrics=base_metrics) from error
    result["_metrics"] = base_metrics
    return result


def _build_openai_request_body(
    *,
    media_type: str,
    image_b64: str | None,
    image_size_kb: int,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    model: str = OPENAI_MODEL,
) -> dict:
    """
    /**
     * OpenAI chat/completions 요청 본문을 만든다.
     */
    """
    image_url = (
        f"data:{media_type};base64,{image_b64}"
        if image_b64 is not None
        else f"data:{media_type};base64,<{image_size_kb}KB, 생략>"
    )
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 4096,
    }


def image_bytes_to_article_openai(
    image_bytes: bytes,
    filename: str,
    media_type: str,
    *,
    openai_api_key: str,
    model: str = DEFAULT_OPENAI_MODEL,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    log: AiOcrLogCollector | None = None,
) -> dict:
    """
    /**
     * OpenAI Vision API(ChatGPT)로 아티클 JSON을 생성한다.
     */
    """
    from services.ai_ocr_log import AiOcrLogCollector as LogCollector

    t_start = time.perf_counter()
    image_size_kb = max(1, len(image_bytes) // 1024)
    log_request_body = _build_openai_request_body(
        media_type=media_type,
        image_b64=None,
        image_size_kb=image_size_kb,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
    )

    if log is not None:
        log.info(
            "OpenAI Vision 요청",
            "\n".join(
                [
                    f"POST {OPENAI_API_BASE}",
                    f"모델: {model}",
                    f"파일: {filename}",
                    f"이미지: {media_type}, {image_size_kb}KB",
                    "",
                    "요청 본문(JSON):",
                    LogCollector.format_json(log_request_body),
                ]
            ),
        )

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    actual_request = _build_openai_request_body(
        media_type=media_type,
        image_b64=b64,
        image_size_kb=image_size_kb,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
    )

    response = httpx.post(
        OPENAI_API_BASE,
        headers={
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json",
        },
        json=actual_request,
        timeout=90.0,
    )

    if response.status_code >= 400:
        try:
            error_payload = response.json()
            message = _extract_openai_error_message(error_payload)
        except ValueError:
            error_payload = {"raw": response.text or response.reason_phrase}
            message = response.text or response.reason_phrase or "unknown error"

        if log is not None:
            log.error(
                f"OpenAI 응답 오류 ({response.status_code})",
                "\n".join(
                    [
                        f"HTTP {response.status_code} {response.reason_phrase or ''}".strip(),
                        f"URL: {OPENAI_API_BASE}",
                        "",
                        "응답 본문(JSON):",
                        LogCollector.format_json(error_payload),
                    ]
                ),
            )
        raise RuntimeError(f"OpenAI API 요청 실패: {message}")

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        if log is not None:
            log.error("OpenAI 응답 없음", LogCollector.format_json(payload))
        raise RuntimeError("OpenAI API가 유효한 응답을 반환하지 않았습니다.")

    message = choices[0].get("message") or {}
    raw_text = message.get("content")
    if not isinstance(raw_text, str) or not raw_text.strip():
        if log is not None:
            log.error("OpenAI 응답 파싱 실패", LogCollector.format_json(payload))
        raise RuntimeError("OpenAI 응답에서 텍스트를 찾을 수 없습니다.")

    usage = payload.get("usage") or {}
    finish_reason_openai = choices[0].get("finish_reason")
    if log is not None:
        log.success(
            "OpenAI Vision 응답 성공",
            "\n".join(
                [
                    "HTTP 200 OK",
                    f"usage: {LogCollector.format_json(usage) if usage else '(없음)'}",
                    "",
                    "응답 본문(요약):",
                    LogCollector.format_json(
                        {
                            "model": payload.get("model"),
                            "finish_reason": finish_reason_openai,
                            "text_length": len(raw_text),
                        }
                    ),
                ]
            ),
        )

    token_metrics = normalize_openai_usage(usage)
    base_metrics: dict[str, object] = {
        **token_metrics,
        "finish_reason": finish_reason_openai,
        "latency_ms": int((time.perf_counter() - t_start) * 1000),
        "raw_response_text": raw_text,
    }
    base_metrics = normalize_usage_metrics_dict(base_metrics)  # type: ignore[assignment]
    try:
        result = _parse_article_json_text(raw_text)
        result = _finalize_article_result(result)
    except json.JSONDecodeError as error:
        raise AiOcrParseError(str(error), metrics=base_metrics) from error
    result["_metrics"] = base_metrics
    return result
