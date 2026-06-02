import type { AiOcrConnection, AiOcrSettings } from "../api/client";

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
 * 활성 연동 프로필을 반환한다.
 * @param aiSettings 서버 설정
 */
export function resolveActiveConnection(aiSettings: AiOcrSettings): AiOcrConnection | null {
  if (aiSettings.active_connection_id == null) {
    return aiSettings.connections.find((item) => item.is_active) ?? aiSettings.connections[0] ?? null;
  }
  return (
    aiSettings.connections.find((item) => item.id === aiSettings.active_connection_id) ??
    aiSettings.connections[0] ??
    null
  );
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

  const active = resolveActiveConnection(aiSettings);
  if (!active) {
    return {
      text: "AI 연동이 없습니다 — AI 설정에서 연동을 추가하세요",
      warn: true,
      ready: false,
      modelId: null,
      promptName: null,
    };
  }

  const ready = active.has_api_key;
  const promptName = aiSettings.active_prompt_id
    ? (aiSettings.prompt_templates.find((item) => item.id === aiSettings.active_prompt_id)?.name ?? null)
    : null;

  return {
    text: ready
      ? `${active.label} — API 키 설정됨`
      : `${active.label} — API 키 미설정`,
    warn: !ready,
    ready,
    modelId: active.model,
    promptName,
  };
}
