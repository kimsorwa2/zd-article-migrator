import type { AiOcrProvider, AiOcrProviderConfig } from "../api/client";
import { AI_PROVIDER_OPTIONS } from "./AiOcrSettingsModal";
import { modelOptionsForProvider } from "../constants/aiModelOptions";

interface AiProviderModelFieldsProps {
  provider: AiOcrProvider;
  /** 계정 표시명 */
  account: string;
  onAccountChange: (value: string) => void;
  /** API 키 입력(비우면 유지) */
  apiKey: string;
  onApiKeyChange: (value: string) => void;
  /** Vision 모델 ID */
  model: string;
  onModelChange: (value: string) => void;
  /** 서버에서 불러온 설정(마스킹 키·has_api_key) */
  savedConfig: AiOcrProviderConfig | undefined;
}

/**
 * AI 제공자별 계정·모델·API 키 입력 필드 묶음.
 */
export default function AiProviderModelFields({
  provider,
  account,
  onAccountChange,
  apiKey,
  onApiKeyChange,
  model,
  onModelChange,
  savedConfig,
}: AiProviderModelFieldsProps) {
  const label = AI_PROVIDER_OPTIONS.find((option) => option.value === provider)?.label ?? provider;
  const modelOptions = modelOptionsForProvider(provider);

  return (
    <div className="ai-ocr-provider-block">
      <p className="ai-ocr-provider-fields-title">{label}</p>

      <label>
        Vision 모델
        <select value={model} onChange={(event) => onModelChange(event.target.value)}>
          {modelOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label>
        계정 (표시용)
        <input
          type="text"
          value={account}
          onChange={(event) => onAccountChange(event.target.value)}
          placeholder={provider === "gemini" ? "예: gsneotek-dev" : "예: my-org"}
        />
      </label>

      <label>
        API 키
        <input
          type="password"
          value={apiKey}
          onChange={(event) => onApiKeyChange(event.target.value)}
          placeholder={
            savedConfig?.has_api_key
              ? "변경할 때만 입력 (비우면 유지)"
              : provider === "gemini"
                ? "AIza..."
                : "sk-..."
          }
          autoComplete="off"
        />
      </label>

      <p className="muted ai-ocr-settings-hint">
        {provider === "gemini"
          ? "Google AI Studio에서 발급한 API 키를 입력하세요."
          : "OpenAI Platform에서 발급한 API 키를 입력하세요."}
      </p>

      {savedConfig?.api_key_masked ? (
        <p className="muted ai-ocr-settings-hint">저장된 키: {savedConfig.api_key_masked}</p>
      ) : (
        <p className="muted ai-ocr-settings-hint ai-ocr-provider-status-warn">API 키가 아직 등록되지 않았습니다.</p>
      )}
    </div>
  );
}
