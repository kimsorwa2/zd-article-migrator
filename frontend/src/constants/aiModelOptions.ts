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

export const DEFAULT_GEMINI_MODEL = "gemini-2.5-pro";
export const DEFAULT_OPENAI_MODEL = "gpt-4o";

/**
 * 제공자별 모델 옵션 목록을 반환한다.
 * @param provider AI 제공자
 */
export function modelOptionsForProvider(provider: AiOcrProvider): AiModelOption[] {
  return provider === "openai" ? OPENAI_MODEL_OPTIONS : GEMINI_MODEL_OPTIONS;
}
