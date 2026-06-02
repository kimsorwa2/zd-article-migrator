import type { AiOcrProvider } from "../api/client";

/** Vision 모델 셀렉트 옵션 */
export interface AiModelOption {
  value: string;
  label: string;
}

const CLAUDE_HAIKU_45 = "anthropic.claude-haiku-4-5-20251001-v1:0";
const CLAUDE_SONNET_45 = "anthropic.claude-sonnet-4-5-20250929-v1:0";
const CLAUDE_SONNET_37 = "anthropic.claude-3-7-sonnet-20250219-v1:0";

const AU_SOURCE_REGIONS = new Set(["ap-southeast-2", "ap-southeast-4", "ap-southeast-6"]);
const JP_SOURCE_REGIONS = new Set(["ap-northeast-1", "ap-northeast-3"]);

/** Gemini Vision 모델 (백엔드 ai_model_options.py와 동기화) */
export const GEMINI_MODEL_OPTIONS: AiModelOption[] = [
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro (권장·복잡 표/매뉴얼)" },
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash (빠름)" },
  { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
  { value: "gemini-1.5-flash", label: "Gemini 1.5 Flash (구형)" },
];

/** OpenAI Vision 모델 */
export const OPENAI_MODEL_OPTIONS: AiModelOption[] = [
  { value: "gpt-4o", label: "GPT-4o (권장)" },
  { value: "gpt-4o-mini", label: "GPT-4o mini (빠름·저렴)" },
  { value: "gpt-4.1", label: "GPT-4.1" },
  { value: "gpt-4.1-mini", label: "GPT-4.1 mini" },
];

/**
 * AWS Bedrock Vision 모델 (foundation model ID).
 * inference profile ID는 bedrockInferenceProfileId()로 리전·모델별 변환한다.
 */
export const BEDROCK_MODEL_OPTIONS: AiModelOption[] = [
  {
    value: CLAUDE_SONNET_45,
    label: "Claude Sonnet 4.5 (권장·서울 등 APAC → global 프로필)",
  },
  {
    value: CLAUDE_HAIKU_45,
    label: "Claude Haiku 4.5 (서울 등 APAC → global 프로필)",
  },
  {
    value: CLAUDE_SONNET_37,
    label: "Claude 3.7 Sonnet (cross-region inference profile)",
  },
  { value: "anthropic.claude-3-5-sonnet-20241022-v2:0", label: "Claude 3.5 Sonnet v2 (구형)" },
];

/**
 * inference profile / foundation ID에서 foundation model ID만 추출한다.
 */
export function bedrockToFoundationModelId(modelId: string): string {
  const cleaned = modelId.trim();
  const prefixes = ["global.", "apac.", "us.", "eu.", "au.", "jp."];
  for (const prefix of prefixes) {
    if (cleaned.startsWith(prefix)) {
      return cleaned.slice(prefix.length);
    }
  }
  return cleaned;
}

/**
 * Claude 3.x·3.7 등 apac·us·eu Geo 프로필용 접두사.
 */
export function bedrockInferenceProfilePrefix(awsRegion: string): string {
  const region = awsRegion.trim().toLowerCase();
  if (region.startsWith("us-")) {
    return "us";
  }
  if (region.startsWith("eu-")) {
    return "eu";
  }
  return "apac";
}

/**
 * Bedrock Converse API용 inference profile model ID (백엔드 resolve_bedrock_model과 동일 로직).
 */
export function bedrockInferenceProfileId(foundationModel: string, awsRegion: string): string {
  const foundation = bedrockToFoundationModelId(foundationModel);
  const region = awsRegion.trim().toLowerCase() || DEFAULT_BEDROCK_REGION;

  if (foundation === CLAUDE_HAIKU_45 || foundation === CLAUDE_SONNET_45) {
    if (region.startsWith("us-")) {
      return `us.${foundation}`;
    }
    if (region.startsWith("eu-")) {
      return `eu.${foundation}`;
    }
    if (AU_SOURCE_REGIONS.has(region)) {
      return `au.${foundation}`;
    }
    if (JP_SOURCE_REGIONS.has(region)) {
      return `jp.${foundation}`;
    }
    return `global.${foundation}`;
  }

  const prefix = bedrockInferenceProfilePrefix(region);
  return `${prefix}.${foundation}`;
}

/**
 * bedrock-runtime 엔드포인트 리전 (연동 AWS 리전과 동일).
 */
export function bedrockRuntimeRegion(_foundationModel: string, awsRegion: string): string {
  return awsRegion.trim().toLowerCase() || DEFAULT_BEDROCK_REGION;
}

export const DEFAULT_GEMINI_MODEL = "gemini-2.5-pro";
export const DEFAULT_OPENAI_MODEL = "gpt-4o";
export const DEFAULT_BEDROCK_MODEL = "anthropic.claude-sonnet-4-5-20250929-v1:0";
export const DEFAULT_BEDROCK_REGION = "ap-northeast-2";

/**
 * 제공자별 모델 옵션 목록을 반환한다.
 */
export function modelOptionsForProvider(provider: AiOcrProvider): AiModelOption[] {
  if (provider === "openai") {
    return OPENAI_MODEL_OPTIONS;
  }
  if (provider === "bedrock") {
    return BEDROCK_MODEL_OPTIONS;
  }
  return GEMINI_MODEL_OPTIONS;
}
