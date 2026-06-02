"""
AI OCR Vision API에서 선택 가능한 모델 목록과 기본값.
"""

from __future__ import annotations

from typing import Literal

AiVisionProvider = Literal["gemini", "openai", "bedrock"]

DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
DEFAULT_OPENAI_MODEL = "gpt-4o"
# Bedrock: foundation model ID (호출 시 리전에 맞는 inference profile 접두사가 붙음)
DEFAULT_BEDROCK_MODEL = "amazon.nova-pro-v1:0"
DEFAULT_BEDROCK_REGION = "ap-northeast-2"

_INFERENCE_PROFILE_PREFIXES = ("us.", "eu.", "apac.")

# Bedrock foundation model ID (on-demand 직접 호출 불가 → inference profile 필요)
_BEDROCK_FOUNDATION_MODELS: frozenset[str] = frozenset(
    {
        "amazon.nova-pro-v1:0",
        "amazon.nova-lite-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    }
)

# (저장/UI용 foundation model id, 라벨)
BEDROCK_VISION_MODELS: tuple[tuple[str, str], ...] = (
    ("amazon.nova-pro-v1:0", "Amazon Nova Pro (권장)"),
    ("amazon.nova-lite-v1:0", "Amazon Nova Lite"),
    ("anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet v2"),
    ("anthropic.claude-3-haiku-20240307-v1:0", "Claude 3 Haiku"),
)


def _build_bedrock_model_id_set() -> frozenset[str]:
    """foundation ID와 us/eu/apac inference profile ID를 모두 허용 목록에 넣는다."""
    ids: set[str] = set(_BEDROCK_FOUNDATION_MODELS)
    for foundation in _BEDROCK_FOUNDATION_MODELS:
        for geo in _INFERENCE_PROFILE_PREFIXES:
            ids.add(f"{geo}{foundation}")
    return frozenset(ids)


_BEDROCK_MODEL_IDS = _build_bedrock_model_id_set()

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
_ALL_PROVIDERS = frozenset({"gemini", "openai", "bedrock"})

# thinking 토큰 예산은 Pro 계열만 지원
_GEMINI_THINKING_MODELS = frozenset({"gemini-2.5-pro"})


def bedrock_to_foundation_model_id(model_id: str) -> str:
    """
    inference profile ID(us./eu./apac.)에서 foundation model ID만 추출한다.
    @param model_id 저장값 또는 API 호출용 ID
    @returns foundation model ID
    """
    cleaned = model_id.strip()
    for prefix in _INFERENCE_PROFILE_PREFIXES:
        if cleaned.startswith(prefix):
            return cleaned[len(prefix) :]
    return cleaned


def bedrock_inference_profile_prefix(aws_region: str | None) -> str:
    """
    AWS 리전 코드에 맞는 Bedrock cross-region inference profile 접두사를 반환한다.
    @param aws_region 예: ap-northeast-2, us-east-1
    @returns us | eu | apac
    """
    region = (aws_region or DEFAULT_BEDROCK_REGION).strip().lower()
    if region.startswith("us-"):
        return "us"
    if region.startswith("eu-"):
        return "eu"
    # ap-northeast-*, ap-southeast-*, ap-south-* 등 APAC
    return "apac"


def resolve_bedrock_model(stored: str | None, aws_region: str | None = None) -> str:
    """
    Bedrock Converse API에 넘길 inference profile model ID를 만든다.
    foundation model ID만 저장돼 있어도 리전에 맞는 접두사를 붙인다.
    @param stored DB/UI에 저장된 모델 ID (foundation 또는 profile)
    @param aws_region Bedrock 호출 리전
    @returns 예: apac.anthropic.claude-3-5-sonnet-20241022-v2:0
    """
    foundation = bedrock_to_foundation_model_id(stored or DEFAULT_BEDROCK_MODEL)
    if foundation not in _BEDROCK_FOUNDATION_MODELS:
        foundation = DEFAULT_BEDROCK_MODEL
    prefix = bedrock_inference_profile_prefix(aws_region)
    return f"{prefix}.{foundation}"


def list_models_for_api() -> dict[str, list[dict[str, str]]]:
    """
    /**
     * 프론트 셀렉트용 모델 옵션 목록을 반환한다.
     * @returns {dict} gemini·openai·bedrock 각각 {value, label} 배열
     */
    """
    bedrock_options = [
        {"value": model_id, "label": label} for model_id, label in BEDROCK_VISION_MODELS
    ]
    # Bedrock은 리전별 inference profile ID 예시를 함께 제공한다.
    profile_prefix = bedrock_inference_profile_prefix(DEFAULT_BEDROCK_REGION)
    bedrock_inference_examples = [
        {
            "value": f"{profile_prefix}.{model_id}",
            "label": f"{label} — 호출 ID ({profile_prefix}.*)",
        }
        for model_id, label in BEDROCK_VISION_MODELS
    ]
    return {
        "gemini": [{"value": model_id, "label": label} for model_id, label in GEMINI_VISION_MODELS],
        "openai": [{"value": model_id, "label": label} for model_id, label in OPENAI_VISION_MODELS],
        "bedrock": bedrock_options,
        "bedrock_inference_profiles": bedrock_inference_examples,
        "defaults": {
            "gemini": DEFAULT_GEMINI_MODEL,
            "openai": DEFAULT_OPENAI_MODEL,
            "bedrock": DEFAULT_BEDROCK_MODEL,
            "bedrock_region": DEFAULT_BEDROCK_REGION,
            "bedrock_inference_profile_prefix": profile_prefix,
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


def normalize_provider(provider: str) -> AiVisionProvider:
    """제공자 문자열을 검증한다."""
    cleaned = provider.strip().lower()
    if cleaned not in _ALL_PROVIDERS:
        raise ValueError(f"지원하지 않는 AI 제공자입니다: {provider}")
    return cleaned  # type: ignore[return-value]


def normalize_model_for_save(provider: AiVisionProvider, model: str | None) -> str | None:
    """
    /**
     * 저장 요청의 모델 값을 검증한다. Bedrock은 foundation model ID만 DB에 저장한다.
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
    if provider == "openai":
        if cleaned not in _OPENAI_MODEL_IDS:
            raise ValueError(f"지원하지 않는 OpenAI 모델입니다: {cleaned}")
        return cleaned
    if cleaned not in _BEDROCK_MODEL_IDS:
        raise ValueError(f"지원하지 않는 Bedrock 모델입니다: {cleaned}")
    return bedrock_to_foundation_model_id(cleaned)


def gemini_supports_thinking(model: str) -> bool:
    """Gemini 모델이 thinkingConfig를 지원하는지 여부."""
    return model in _GEMINI_THINKING_MODELS
