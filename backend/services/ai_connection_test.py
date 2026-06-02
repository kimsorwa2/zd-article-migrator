"""
AI Vision 연동 프로필 연결 테스트 — 최소 토큰으로 API 인증·모델 호출을 검증한다.
"""

from __future__ import annotations

import logging
import time

import httpx

from services.ai_model_options import (
    DEFAULT_BEDROCK_REGION,
    bedrock_to_foundation_model_id,
    resolve_bedrock_runtime_region,
)
from services.article_from_image import GEMINI_API_BASE
from services.bedrock_runtime import bedrock_converse, mask_bedrock_api_key

logger = logging.getLogger(__name__)

# 연결 테스트용 짧은 프롬프트
_TEST_PROMPT = "ping"
_TEST_MAX_OUTPUT_TOKENS = 8
_TEST_HTTP_TIMEOUT_SEC = 30.0


def test_gemini_connection(*, api_key: str, model: str) -> tuple[bool, str, int]:
    """
    /**
     * Gemini generateContent로 텍스트 1회 호출해 연결을 검증한다.
     * @returns (성공 여부, 메시지, 지연 ms)
     */
    """
    t_start = time.perf_counter()
    url = f"{GEMINI_API_BASE}/{model}:generateContent"
    logger.info("Gemini 연결 테스트 시작 | model=%s | key_len=%d", model, len(api_key))
    try:
        response = httpx.post(
            url,
            params={"key": api_key},
            json={
                "contents": [{"role": "user", "parts": [{"text": _TEST_PROMPT}]}],
                "generationConfig": {"maxOutputTokens": _TEST_MAX_OUTPUT_TOKENS},
            },
            timeout=_TEST_HTTP_TIMEOUT_SEC,
        )
    except httpx.HTTPError as error:
        latency_ms = int((time.perf_counter() - t_start) * 1000)
        logger.exception("Gemini 연결 테스트 네트워크 오류 (%dms): %s", latency_ms, error)
        return False, f"네트워크 오류: {error}", latency_ms

    latency_ms = int((time.perf_counter() - t_start) * 1000)
    if response.status_code >= 400:
        try:
            payload = response.json()
            message = (
                payload.get("error", {}).get("message")
                if isinstance(payload.get("error"), dict)
                else response.text
            )
        except ValueError:
            message = response.text or response.reason_phrase or "unknown error"
        logger.error(
            "Gemini 연결 테스트 실패 | status=%s | %dms | %s",
            response.status_code,
            latency_ms,
            message,
        )
        return False, f"Gemini API 오류 ({response.status_code}): {message}", latency_ms

    payload = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        block_reason = payload.get("promptFeedback", {}).get("blockReason")
        detail = f" (blockReason: {block_reason})" if block_reason else ""
        logger.error("Gemini 연결 테스트 빈 응답 | %dms%s", latency_ms, detail)
        return False, f"Gemini 응답이 비어 있습니다.{detail}", latency_ms

    logger.info("Gemini 연결 테스트 성공 | model=%s | %dms", model, latency_ms)
    return True, f"Gemini 연결 성공 (모델: {model})", latency_ms


def test_openai_connection(*, api_key: str, model: str) -> tuple[bool, str, int]:
    """
    /**
     * OpenAI Chat Completions로 텍스트 1회 호출해 연결을 검증한다.
     * @returns (성공 여부, 메시지, 지연 ms)
     */
    """
    t_start = time.perf_counter()
    logger.info("OpenAI 연결 테스트 시작 | model=%s | key_len=%d", model, len(api_key))
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": _TEST_PROMPT}],
                "max_tokens": _TEST_MAX_OUTPUT_TOKENS,
            },
            timeout=_TEST_HTTP_TIMEOUT_SEC,
        )
    except httpx.HTTPError as error:
        latency_ms = int((time.perf_counter() - t_start) * 1000)
        logger.exception("OpenAI 연결 테스트 네트워크 오류 (%dms): %s", latency_ms, error)
        return False, f"네트워크 오류: {error}", latency_ms

    latency_ms = int((time.perf_counter() - t_start) * 1000)
    if response.status_code >= 400:
        try:
            payload = response.json()
            message = payload.get("error", {}).get("message", response.text)
        except ValueError:
            message = response.text or response.reason_phrase or "unknown error"
        logger.error(
            "OpenAI 연결 테스트 실패 | status=%s | %dms | %s",
            response.status_code,
            latency_ms,
            message,
        )
        return False, f"OpenAI API 오류 ({response.status_code}): {message}", latency_ms

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        logger.error("OpenAI 연결 테스트 빈 응답 | %dms", latency_ms)
        return False, "OpenAI 응답이 비어 있습니다.", latency_ms

    logger.info("OpenAI 연결 테스트 성공 | model=%s | %dms", model, latency_ms)
    return True, f"OpenAI 연결 성공 (모델: {model})", latency_ms


def test_bedrock_connection(
    *,
    api_key: str,
    model: str,
    aws_region: str = DEFAULT_BEDROCK_REGION,
) -> tuple[bool, str, int]:
    """
    /**
     * Bedrock Converse API(Bearer)로 텍스트 1회 호출해 연결을 검증한다.
     * @returns (성공 여부, 메시지, 지연 ms)
     */
    """
    foundation = bedrock_to_foundation_model_id(model)
    runtime_region = resolve_bedrock_runtime_region(aws_region, foundation)
    t_start = time.perf_counter()
    logger.info(
        "Bedrock 연결 테스트 시작 | runtime_region=%s | model=%s | key=%s",
        runtime_region,
        model,
        mask_bedrock_api_key(api_key),
    )
    try:
        response = bedrock_converse(
            api_key=api_key,
            region=runtime_region,
            model_id=model,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": _TEST_PROMPT}],
                }
            ],
            inference_config={"maxTokens": _TEST_MAX_OUTPUT_TOKENS, "temperature": 0},
            timeout=_TEST_HTTP_TIMEOUT_SEC,
            log_context="Bedrock 연결 테스트",
        )
    except RuntimeError as error:
        latency_ms = int((time.perf_counter() - t_start) * 1000)
        return False, str(error), latency_ms

    output_message = response.get("output", {}).get("message", {})
    parts = output_message.get("content") or []
    has_text = any(isinstance(part.get("text"), str) for part in parts)
    latency_ms = int((time.perf_counter() - t_start) * 1000)
    if not has_text:
        stop_reason = response.get("stopReason")
        logger.error(
            "Bedrock 연결 테스트 텍스트 없음 | %dms | stopReason=%s",
            latency_ms,
            stop_reason,
        )
        return False, f"Bedrock 응답에 텍스트가 없습니다. (stopReason: {stop_reason})", latency_ms

    logger.info("Bedrock 연결 테스트 성공 | %dms", latency_ms)
    return (
        True,
        f"Bedrock 연결 성공 (모델: {model}, 리전: {aws_region})",
        latency_ms,
    )


def run_connection_test(
    *,
    provider: str,
    api_key: str,
    model: str,
    aws_region: str | None = None,
) -> tuple[bool, str, int]:
    """
    /**
     * 제공자별 연결 테스트를 실행한다.
     * @returns (성공 여부, 메시지, 지연 ms)
     */
    """
    logger.info("AI 연동 테스트 | provider=%s | model=%s", provider, model)
    if provider == "gemini":
        return test_gemini_connection(api_key=api_key, model=model)
    if provider == "openai":
        return test_openai_connection(api_key=api_key, model=model)
    if provider == "bedrock":
        return test_bedrock_connection(
            api_key=api_key,
            model=model,
            aws_region=aws_region or DEFAULT_BEDROCK_REGION,
        )
    logger.error("AI 연동 테스트 — 지원하지 않는 제공자: %s", provider)
    return False, f"지원하지 않는 제공자입니다: {provider}", 0
