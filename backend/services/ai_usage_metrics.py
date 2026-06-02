"""
Vision AI 제공자별 usage 응답을 공통 메트릭 형식으로 정규화한다.
"""

from __future__ import annotations

from typing import Any


def _int_or_zero(value: object | None) -> int:
    """정수로 변환한다. 없거나 잘못된 값이면 0."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _optional_positive_int(value: object | None) -> int | None:
    """양의 정수만 반환하고, 없으면 None."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return int(value)
    return None


def normalize_usage_metrics_dict(metrics: dict[str, Any]) -> dict[str, int | str | None]:
    """
    /**
     * 저장·이력용 metrics dict를 정규화한다(추론 토큰 0, 총 토큰 계산).
     * @param metrics article_from_image 등에서 만든 _metrics
     * @returns input_tokens, output_tokens, thinking_tokens, total_tokens, …
     */
    """
    input_tokens = _optional_positive_int(metrics.get("input_tokens"))
    output_tokens = _optional_positive_int(metrics.get("output_tokens"))
    thinking_raw = metrics.get("thinking_tokens")
    thinking_tokens = _int_or_zero(thinking_raw) if thinking_raw is not None else 0

    total_tokens: int | None = None
    if input_tokens is not None or output_tokens is not None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0) + thinking_tokens

    normalized: dict[str, int | str | None] = dict(metrics)  # type: ignore[assignment]
    normalized["input_tokens"] = input_tokens
    normalized["output_tokens"] = output_tokens
    normalized["thinking_tokens"] = thinking_tokens
    normalized["total_tokens"] = total_tokens
    return normalized


def normalize_gemini_usage(usage: dict[str, Any]) -> dict[str, int]:
    """
    Gemini usageMetadata → 공통 토큰 메트릭.
    @param usage usageMetadata 객체
    """
    input_tokens = _int_or_zero(usage.get("promptTokenCount"))
    output_tokens = _int_or_zero(usage.get("candidatesTokenCount"))
    thinking_tokens = _int_or_zero(usage.get("thoughtsTokenCount"))
    total_from_api = usage.get("totalTokenCount")
    total_tokens = (
        _int_or_zero(total_from_api)
        if total_from_api is not None
        else input_tokens + output_tokens + thinking_tokens
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": total_tokens,
    }


def normalize_openai_usage(usage: dict[str, Any]) -> dict[str, int]:
    """
    OpenAI chat completions usage → 공통 토큰 메트릭.
    @param usage usage 객체
    """
    input_tokens = _int_or_zero(usage.get("prompt_tokens"))
    output_tokens = _int_or_zero(usage.get("completion_tokens"))
    details = usage.get("completion_tokens_details") or {}
    thinking_tokens = _int_or_zero(details.get("reasoning_tokens"))
    total_from_api = usage.get("total_tokens")
    total_tokens = (
        _int_or_zero(total_from_api)
        if total_from_api is not None
        else input_tokens + output_tokens
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": total_tokens,
    }


def normalize_bedrock_usage(usage: dict[str, Any]) -> dict[str, int]:
    """
    Bedrock Converse usage → 공통 토큰 메트릭.
    inputTokens는 캐시 미포함 분량이므로 cache* 토큰을 합산한다.
    @param usage Converse 응답의 usage 객체
    """
    input_base = _int_or_zero(usage.get("inputTokens"))
    cache_read = _int_or_zero(usage.get("cacheReadInputTokens"))
    cache_write = _int_or_zero(usage.get("cacheWriteInputTokens"))
    input_tokens = input_base + cache_read + cache_write
    output_tokens = _int_or_zero(usage.get("outputTokens"))
    total_from_api = usage.get("totalTokens")
    total_tokens = (
        _int_or_zero(total_from_api)
        if total_from_api is not None
        else input_tokens + output_tokens
    )
    # Claude 3.5 Sonnet v2 등 일반 호출은 extended thinking 미사용 → 0
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": 0,
        "total_tokens": total_tokens,
    }


def enrich_history_token_fields(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    thinking_tokens: int | None,
) -> dict[str, int | None]:
    """
    /**
     * DB 이력 행을 API/화면용으로 보정한다(추론 null → 0, 총 토큰 계산).
     */
    """
    thinking = thinking_tokens if thinking_tokens is not None else 0
    total: int | None = None
    if input_tokens is not None or output_tokens is not None:
        total = (input_tokens or 0) + (output_tokens or 0) + thinking
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking,
        "total_tokens": total,
    }
