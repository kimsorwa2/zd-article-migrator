import { useEffect, useState } from "react";
import { Settings, X } from "lucide-react";
import { apiClient, type AiOcrProvider, type AiOcrSettings } from "../api/client";
import AiProviderModelFields from "./AiProviderModelFields";
import { DEFAULT_GEMINI_MODEL, DEFAULT_OPENAI_MODEL } from "../constants/aiModelOptions";

interface AiOcrSettingsModalProps {
  open: boolean;
  onClose: () => void;
  onSaved?: (settings: AiOcrSettings) => void;
}

/** AI 제공자 UI 라벨 */
export const AI_PROVIDER_OPTIONS: Array<{ value: AiOcrProvider; label: string }> = [
  { value: "gemini", label: "Google Gemini" },
  { value: "openai", label: "ChatGPT (OpenAI)" },
  { value: "bedrock", label: "AWS Bedrock" },
];

/**
 * AI 제공자·계정·API 키 설정 모달.
 * 선택한 제공자의 입력 필드만 동적으로 표시한다.
 * @param open 모달 표시 여부
 * @param onClose 닫기 콜백
 * @param onSaved 저장 완료 콜백
 */
export default function AiOcrSettingsModal({ open, onClose, onSaved }: AiOcrSettingsModalProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [settings, setSettings] = useState<AiOcrSettings | null>(null);
  const [activeProvider, setActiveProvider] = useState<AiOcrProvider>("gemini");
  const [geminiAccount, setGeminiAccount] = useState("");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [openaiAccount, setOpenaiAccount] = useState("");
  const [openaiApiKey, setOpenaiApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState(DEFAULT_GEMINI_MODEL);
  const [openaiModel, setOpenaiModel] = useState(DEFAULT_OPENAI_MODEL);

  useEffect(() => {
    if (!open) {
      return;
    }
    setError("");
    setGeminiApiKey("");
    setOpenaiApiKey("");
    setLoading(true);
    void apiClient
      .getAiOcrSettings()
      .then((data) => {
        setSettings(data);
        setActiveProvider(data.active_provider);
        setGeminiAccount(data.gemini.account ?? "");
        setOpenaiAccount(data.openai.account ?? "");
        setGeminiModel(data.gemini.model);
        setOpenaiModel(data.openai.model);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "설정을 불러오지 못했습니다.");
      })
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) {
    return null;
  }

  function handleProviderChange(provider: AiOcrProvider) {
    setActiveProvider(provider);
    setGeminiApiKey("");
    setOpenaiApiKey("");
    setError("");
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const updated = await apiClient.updateAiOcrSettings({
        active_provider: activeProvider,
        gemini_account: geminiAccount.trim() || null,
        gemini_api_key: geminiApiKey.trim() || null,
        gemini_model: geminiModel,
        openai_account: openaiAccount.trim() || null,
        openai_api_key: openaiApiKey.trim() || null,
        openai_model: openaiModel,
      });
      setSettings(updated);
      setGeminiApiKey("");
      setOpenaiApiKey("");
      onSaved?.(updated);
      onClose();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "설정 저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel ai-ocr-settings-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3 className="title-with-icon">
            <Settings size={18} aria-hidden="true" />
            AI 설정
          </h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="닫기">
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="modal-body">
        {loading ? <p className="muted">설정 불러오는 중...</p> : null}

        {!loading ? (
          <div className="ai-ocr-settings-form">
            <label>
              분석에 사용할 AI
              <select
                value={activeProvider}
                onChange={(event) => handleProviderChange(event.target.value as AiOcrProvider)}
              >
                {AI_PROVIDER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            {activeProvider === "gemini" ? (
                <AiProviderModelFields
                  key="gemini"
                  provider="gemini"
                  account={geminiAccount}
                  onAccountChange={setGeminiAccount}
                  apiKey={geminiApiKey}
                  onApiKeyChange={setGeminiApiKey}
                  model={geminiModel}
                  onModelChange={setGeminiModel}
                  savedConfig={settings?.gemini}
                />
            ) : (
                <AiProviderModelFields
                  key="openai"
                  provider="openai"
                  account={openaiAccount}
                  onAccountChange={setOpenaiAccount}
                  apiKey={openaiApiKey}
                  onApiKeyChange={setOpenaiApiKey}
                  model={openaiModel}
                  onModelChange={setOpenaiModel}
                  savedConfig={settings?.openai}
                />
            )}

            {error ? <p className="form-error">{error}</p> : null}
            <button type="button" className="button-primary" disabled={saving} onClick={() => void handleSave()}>
              {saving ? "저장 중..." : "저장"}
            </button>
          </div>
        ) : null}
        </div>
      </div>
    </div>
  );
}
