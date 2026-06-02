"""
AI OCR Vision API에서 선택 가능한 모델 목록과 기본값.
Bedrock inference profile ID는 모델·소스 리전마다 AWS 문서와 다르다(apac.만으로는 부족).
"""

from __future__ import annotations

from typing import Literal

AiVisionProvider = Literal["gemini", "openai", "bedrock"]

DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
DEFAULT_OPENAI_MODEL = "gpt-4o"
# Bedrock: foundation model ID (호출 시 inference profile ID 필요)
DEFAULT_BEDROCK_MODEL = "anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_BEDROCK_REGION = "ap-northeast-2"

# inference profile ID 접두사 (긴 것부터 매칭)
_INFERENCE_PROFILE_PREFIXES: tuple[str, ...] = (
    "global.",
    "apac.",
    "us.",
    "eu.",
    "au.",
    "jp.",
)

_CLAUDE_HAIKU_45 = "anthropic.claude-haiku-4-5-20251001-v1:0"
_CLAUDE_SONNET_45 = "anthropic.claude-sonnet-4-5-20250929-v1:0"
_CLAUDE_SONNET_37 = "anthropic.claude-3-7-sonnet-20250219-v1:0"

# Bedrock foundation model ID
_BEDROCK_FOUNDATION_MODELS: frozenset[str] = frozenset(
    {
        _CLAUDE_HAIKU_45,
        _CLAUDE_SONNET_45,
        _CLAUDE_SONNET_37,
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
    }
)

# 모델별 AWS에 실제 존재하는 system inference profile ID
_BEDROCK_KNOWN_PROFILE_IDS: dict[str, frozenset[str]] = {
    _CLAUDE_HAIKU_45: frozenset(
        {
            "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "au.anthropic.claude-haiku-4-5-20251001-v1:0",
            "jp.anthropic.claude-haiku-4-5-20251001-v1:0",
            "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        }
    ),
    _CLAUDE_SONNET_45: frozenset(
        {
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "au.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "jp.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        }
    ),
    _CLAUDE_SONNET_37: frozenset(
        {
            "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "eu.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
        }
    ),
    "anthropic.claude-3-5-sonnet-20241022-v2:0": frozenset(
        {
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
        }
    ),
}

# Claude 4.5 계열(Haiku·Sonnet) Geo AU/JP 소스 리전 (AWS model card)
_AU_SOURCE_REGIONS = frozenset(
    {
        "ap-southeast-2",
        "ap-southeast-4",
        "ap-southeast-6",
    }
)

_JP_SOURCE_REGIONS = frozenset(
    {
        "ap-northeast-1",
        "ap-northeast-3",
    }
)

# (저장/UI용 foundation model id, 라벨)
BEDROCK_VISION_MODELS: tuple[tuple[str, str], ...] = (
    (
        _CLAUDE_SONNET_45,
        "Claude Sonnet 4.5 (권장·서울 등 APAC → global 프로필)",
    ),
    (
        _CLAUDE_HAIKU_45,
        "Claude Haiku 4.5 (서울 등 APAC → global 프로필)",
    ),
    (
        _CLAUDE_SONNET_37,
        "Claude 3.7 Sonnet (cross-region inference profile)",
    ),
    ("anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet v2 (구형)"),
)


def _build_bedrock_model_id_set() -> frozenset[str]:
    """foundation ID + 모델별 실제 inference profile ID."""
    ids: set[str] = set(_BEDROCK_FOUNDATION_MODELS)
    for profiles in _BEDROCK_KNOWN_PROFILE_IDS.values():
        ids.update(profiles)
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
    inference profile ID에서 foundation model ID만 추출한다.
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
    Claude 3.x·3.7 등 apac·us·eu Geo 프로필용 접두사.
    Claude 4.5는 resolve_bedrock_inference_profile_id에서 global 등으로 분기한다.
    @param aws_region 예: ap-northeast-2, us-east-1
    @returns us | eu | apac
    """
    region = (aws_region or DEFAULT_BEDROCK_REGION).strip().lower()
    if region.startswith("us-"):
        return "us"
    if region.startswith("eu-"):
        return "eu"
    return "apac"


def _resolve_anthropic_claude_45_geo_profile(foundation: str, region: str) -> str:
    """
    Claude Haiku 4.5 / Sonnet 4.5 — us·eu·au·jp·global Geo inference profile (apac 없음).
  """
    if region.startswith("us-"):
        return f"us.{foundation}"
    if region.startswith("eu-"):
        return f"eu.{foundation}"
    if region in _AU_SOURCE_REGIONS:
        return f"au.{foundation}"
    if region in _JP_SOURCE_REGIONS:
        return f"jp.{foundation}"
    return f"global.{foundation}"


def resolve_bedrock_inference_profile_id(foundation: str, aws_region: str | None) -> str:
    """
    Bedrock Converse에 넘길 system inference profile model ID.
    AWS model card 기준 — apac.{model}이 없는 모델은 us./jp./global. 등으로 분기한다.
    @param foundation foundation model ID
    @param aws_region Bedrock API 호출 소스 리전(연동 설정)
    """
    region = (aws_region or DEFAULT_BEDROCK_REGION).strip().lower()

    if foundation in (_CLAUDE_HAIKU_45, _CLAUDE_SONNET_45):
        return _resolve_anthropic_claude_45_geo_profile(foundation, region)

    prefix = bedrock_inference_profile_prefix(aws_region)
    return f"{prefix}.{foundation}"


def resolve_bedrock_runtime_region(aws_region: str | None, foundation: str) -> str:
    """
    bedrock-runtime HTTP 엔드포인트 리전.
    @param aws_region 연동에 저장된 리전
    @param foundation foundation model ID (호환용, 현재 리전 분기 없음)
    @returns bedrock-runtime.{region}.amazonaws.com 에 쓸 리전 코드
    """
    _ = foundation
    return (aws_region or DEFAULT_BEDROCK_REGION).strip().lower()


def resolve_bedrock_model(stored: str | None, aws_region: str | None = None) -> str:
    """
    Bedrock Converse API에 넘길 inference profile model ID를 만든다.
    @param stored DB/UI에 저장된 모델 ID (foundation 또는 profile)
    @param aws_region Bedrock 호출 리전
    @returns 예: global.anthropic.claude-haiku-4-5-20251001-v1:0 (서울 + Haiku 4.5)
    """
    foundation = bedrock_to_foundation_model_id(stored or DEFAULT_BEDROCK_MODEL)
    if foundation not in _BEDROCK_FOUNDATION_MODELS:
        foundation = DEFAULT_BEDROCK_MODEL
    return resolve_bedrock_inference_profile_id(foundation, aws_region)


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
    bedrock_inference_examples = [
        {
            "value": resolve_bedrock_model(model_id, DEFAULT_BEDROCK_REGION),
            "label": f"{label} — 호출 ID (기본 리전 {DEFAULT_BEDROCK_REGION})",
        }
        for model_id, label in BEDROCK_VISION_MODELS
    ]
    profile_prefix = bedrock_inference_profile_prefix(DEFAULT_BEDROCK_REGION)
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
