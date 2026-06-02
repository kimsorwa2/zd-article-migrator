import type { AiOcrSettings } from "../api/client";
import { AI_PROVIDER_OPTIONS } from "../components/AiOcrSettingsModal";

/** 분석 AI 제공자 상태 표시용 */
export interface AiProviderStatusDisplay {
  /** 상태 한 줄 문구 */
  text: string;
  /** 경고 스타일 여부 */
  warn: boolean;
  /** OCR 실행 가능 여부(API 키 등록됨) */
  ready: boolean;
  modelId: string | null;
  promptName: string | null;
}

/**
 * AI 설정 로딩·키 등록 상태에 맞는 표시 문구를 만든다.
 * @param aiSettings 서버에서 불러온 설정 (로딩 중이면 null)
 * @param loading 설정 API 요청 진행 중 여부
 */
export function buildAiProviderStatusDisplay(
  aiSettings: AiOcrSettings | null,
  loading: boolean,
): AiProviderStatusDisplay {
  if (loading || aiSettings === null) {
    return {
      text: "AI 설정을 불러오는 중...",
      warn: false,
      ready: false,
      modelId: null,
      promptName: null,
    };
  }

  const label =
    AI_PROVIDER_OPTIONS.find((option) => option.value === aiSettings.active_provider)?.label ?? "—";
  const ready =
    aiSettings.active_provider === "openai"
      ? aiSettings.openai.has_api_key
      : aiSettings.gemini.has_api_key;
  const modelId =
    aiSettings.active_provider === "openai" ? aiSettings.openai.model : aiSettings.gemini.model;
  const promptName = aiSettings.active_prompt_id
    ? (aiSettings.prompt_templates.find((item) => item.id === aiSettings.active_prompt_id)?.name ?? null)
    : null;

  return {
    text: ready
      ? `${label} API 키 설정됨`
      : `${label} API 키 미설정 — AI 설정 메뉴에서 키를 저장하세요`,
    warn: !ready,
    ready,
    modelId,
    promptName,
  };
}
