"""
Amazon Bedrock Runtime Converse API — Bedrock API 키(Bearer) HTTP 호출.
boto3는 구버전에서 AWS_BEARER_TOKEN_BEDROCK를 인식하지 못하므로 httpx를 사용한다.
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT_SEC = 90.0


def _build_converse_url(region: str, model_id: str) -> str:
    """Bedrock Converse 엔드포인트 URL을 만든다."""
    return f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/converse"


def _encode_binary_fields_for_json(value: Any) -> Any:
    """
    /**
     * Converse REST API는 image.source.bytes를 base64 문자열로 받는다.
     * SDK(boto3)와 달리 httpx JSON 직렬화 전에 변환이 필요하다.
     */
    """
    if isinstance(value, dict):
        encoded: dict[str, Any] = {}
        for key, item in value.items():
            if key == "bytes" and isinstance(item, (bytes, bytearray)):
                encoded[key] = base64.b64encode(item).decode("ascii")
            else:
                encoded[key] = _encode_binary_fields_for_json(item)
        return encoded
    if isinstance(value, list):
        return [_encode_binary_fields_for_json(item) for item in value]
    return value


def mask_bedrock_api_key(api_key: str) -> str:
    """
    /**
     * 로그용 API 키 마스킹(앞 4자 + 길이).
     */
    """
    trimmed = api_key.strip()
    if not trimmed:
        return "(empty)"
    if len(trimmed) <= 8:
        return "****"
    return f"{trimmed[:4]}…({len(trimmed)}자)"


def bedrock_converse(
    *,
    api_key: str,
    region: str,
    model_id: str,
    messages: list[dict[str, Any]],
    system: list[dict[str, str]] | None = None,
    inference_config: dict[str, Any] | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT_SEC,
    log_context: str = "Bedrock",
) -> dict[str, Any]:
    """
    /**
     * Bedrock Converse API를 Bearer 토큰으로 호출한다.
     * @raises RuntimeError HTTP 오류 또는 응답 파싱 실패 시
     */
    """
    url = _build_converse_url(region, model_id)
    body: dict[str, Any] = {"messages": _encode_binary_fields_for_json(copy.deepcopy(messages))}
    if system:
        body["system"] = system
    if inference_config:
        body["inferenceConfig"] = inference_config

    logger.info(
        "%s 요청 시작 | region=%s | modelId=%s | key=%s | timeout=%ss",
        log_context,
        region,
        model_id,
        mask_bedrock_api_key(api_key),
        timeout,
    )

    t_start = time.perf_counter()
    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=timeout,
        )
    except httpx.HTTPError as error:
        elapsed_ms = int((time.perf_counter() - t_start) * 1000)
        logger.exception(
            "%s 네트워크 오류 (%dms) | region=%s | modelId=%s | %s",
            log_context,
            elapsed_ms,
            region,
            model_id,
            error,
        )
        raise RuntimeError(f"Bedrock 네트워크 오류: {error}") from error

    elapsed_ms = int((time.perf_counter() - t_start) * 1000)
    logger.info(
        "%s HTTP 응답 | status=%s | %dms | region=%s | modelId=%s",
        log_context,
        response.status_code,
        elapsed_ms,
        region,
        model_id,
    )

    if response.status_code >= 400:
        try:
            error_payload = response.json()
            detail = json.dumps(error_payload, ensure_ascii=False)[:2000]
        except ValueError:
            detail = (response.text or response.reason_phrase or "")[:2000]
        logger.error(
            "%s API 오류 | status=%s | %dms | body=%s",
            log_context,
            response.status_code,
            elapsed_ms,
            detail,
        )
        raise RuntimeError(f"Bedrock API 오류 ({response.status_code}): {detail}")

    try:
        payload = response.json()
    except ValueError as error:
        logger.error(
            "%s JSON 파싱 실패 | %dms | raw=%s",
            log_context,
            elapsed_ms,
            (response.text or "")[:500],
        )
        raise RuntimeError("Bedrock 응답 JSON 파싱 실패") from error

    logger.info("%s 성공 | %dms | stopReason=%s", log_context, elapsed_ms, payload.get("stopReason"))
    return payload
