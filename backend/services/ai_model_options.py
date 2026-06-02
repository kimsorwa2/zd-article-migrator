"""
AI OCR Vision API에서 선택 가능한 모델 목록과 기본값.
"""

from __future__ import annotations

from typing import Literal

AiVisionProvider = Literal["gemini", "openai"]

DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
DEFAULT_OPENAI_MODEL = "gpt-4o"

# (API model id, UI 라벨)
GEMINI_VISION_MODELS: tuple[tuple[str, str], ...] = (
    ("gemini-2.5-pro", "Gemini 2.5 Pro (권장·복잡 표/매뉴얼)"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash (빠름)"),
    ("gemini-2.0-flash", "Gemini 2.0 Flash"),
    ("gemini-1.5-flash", "Gemini 1.5 Flash (구형)"),
)

OPENAI_VISION_MODELS: tuple[tuple[str, str], ...] = (
    ("gpt-4o", "GPT-4o (권장)"),
    ("gpt-4o-mini", "GPT-4o mini (빠름·저렴)"),
    ("gpt-4.1", "GPT-4.1"),
    ("gpt-4.1-mini", "GPT-4.1 mini"),
)

_GEMINI_MODEL_IDS = frozenset(model_id for model_id, _ in GEMINI_VISION_MODELS)
_OPENAI_MODEL_IDS = frozenset(model_id for model_id, _ in OPENAI_VISION_MODELS)

# thinking 토큰 예산은 Pro 계열만 지원
_GEMINI_THINKING_MODELS = frozenset({"gemini-2.5-pro"})


def list_models_for_api() -> dict[str, list[dict[str, str]]]:
    """
    /**
     * 프론트 셀렉트용 모델 옵션 목록을 반환한다.
     * @returns {dict} gemini·openai 각각 {value, label} 배열
     */
    """
    return {
        "gemini": [{"value": model_id, "label": label} for model_id, label in GEMINI_VISION_MODELS],
        "openai": [{"value": model_id, "label": label} for model_id, label in OPENAI_VISION_MODELS],
        "defaults": {
            "gemini": DEFAULT_GEMINI_MODEL,
            "openai": DEFAULT_OPENAI_MODEL,
        },
    }


def resolve_gemini_model(stored: str | None) -> str:
    """저장된 Gemini 모델 ID를 검증해 반환한다."""
    if stored and stored.strip() in _GEMINI_MODEL_IDS:
        return stored.strip()
    return DEFAULT_GEMINI_MODEL


def resolve_openai_model(stored: str | None) -> str:
    """저장된 OpenAI 모델 ID를 검증해 반환한다."""
    if stored and stored.strip() in _OPENAI_MODEL_IDS:
        return stored.strip()
    return DEFAULT_OPENAI_MODEL


def normalize_model_for_save(provider: AiVisionProvider, model: str | None) -> str | None:
    """
    /**
     * 저장 요청의 모델 값을 검증한다. None이면 변경 없음을 의미하지 않고 호출부에서 처리.
     * @raises ValueError 지원하지 않는 모델 ID
     */
    """
    if model is None:
        return None
    cleaned = model.strip()
    if not cleaned:
        return None
    if provider == "gemini":
        if cleaned not in _GEMINI_MODEL_IDS:
            raise ValueError(f"지원하지 않는 Gemini 모델입니다: {cleaned}")
        return cleaned
    if cleaned not in _OPENAI_MODEL_IDS:
        raise ValueError(f"지원하지 않는 OpenAI 모델입니다: {cleaned}")
    return cleaned


def gemini_supports_thinking(model: str) -> bool:
    """Gemini 모델이 thinkingConfig를 지원하는지 여부."""
    return model in _GEMINI_THINKING_MODELS
