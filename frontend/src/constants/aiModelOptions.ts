import type { AiOcrProvider } from "../api/client";

/** Vision 모델 셀렉트 옵션 */
export interface AiModelOption {
  value: string;
  label: string;
}

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
 * ap-northeast-2 등 APAC 리전 호출 시 백엔드가 apac.* inference profile ID로 자동 변환한다.
 */
export const BEDROCK_MODEL_OPTIONS: AiModelOption[] = [
  { value: "amazon.nova-pro-v1:0", label: "Amazon Nova Pro (권장)" },
  { value: "amazon.nova-lite-v1:0", label: "Amazon Nova Lite" },
  { value: "anthropic.claude-3-5-sonnet-20241022-v2:0", label: "Claude 3.5 Sonnet v2" },
  { value: "anthropic.claude-3-haiku-20240307-v1:0", label: "Claude 3 Haiku" },
];

/**
 * AWS 리전에 맞는 Bedrock inference profile 접두사를 반환한다.
 * @param awsRegion 예: ap-northeast-2, us-east-1
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
 * foundation model ID를 Bedrock Converse API용 inference profile ID로 변환한다.
 * @param foundationModel foundation model ID (셀렉트 value)
 * @param awsRegion Bedrock 호출 리전
 */
export function bedrockInferenceProfileId(foundationModel: string, awsRegion: string): string {
  const raw = foundationModel.trim();
  const stripped = raw.replace(/^(us|eu|apac)\./, "");
  const prefix = bedrockInferenceProfilePrefix(awsRegion);
  return `${prefix}.${stripped}`;
}

export const DEFAULT_GEMINI_MODEL = "gemini-2.5-pro";
export const DEFAULT_OPENAI_MODEL = "gpt-4o";
export const DEFAULT_BEDROCK_MODEL = "amazon.nova-pro-v1:0";
export const DEFAULT_BEDROCK_REGION = "ap-northeast-2";

/**
 * 제공자별 모델 옵션 목록을 반환한다.
 * @param provider AI 제공자
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
