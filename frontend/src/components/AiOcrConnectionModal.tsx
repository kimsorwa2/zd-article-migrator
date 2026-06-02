import { useEffect, useState } from "react";
import { X } from "lucide-react";
import {
  apiClient,
  type AiOcrConnection,
  type AiOcrPromptTemplate,
  type AiOcrProvider,
} from "../api/client";
import { AI_PROVIDER_OPTIONS } from "./AiOcrSettingsModal";
import {
  bedrockInferenceProfileId,
  DEFAULT_BEDROCK_MODEL,
  DEFAULT_BEDROCK_REGION,
  DEFAULT_GEMINI_MODEL,
  DEFAULT_OPENAI_MODEL,
  modelOptionsForProvider,
} from "../constants/aiModelOptions";

interface AiOcrConnectionModalProps {
  open: boolean;
  onClose: () => void;
  /** 수정 대상(없으면 추가 모드) */
  connection?: AiOcrConnection | null;
  /** OCR 프롬프트 템플릿 목록 */
  promptTemplates?: AiOcrPromptTemplate[];
  /** 추가 시 기본 선택할 프롬프트 ID */
  defaultPromptTemplateId?: number | null;
  onSaved: () => void;
}

/**
 * AI Vision 연동 프로필 추가·수정 모달.
 */
export default function AiOcrConnectionModal({
  open,
  onClose,
  connection,
  promptTemplates = [],
  defaultPromptTemplateId = null,
  onSaved,
}: AiOcrConnectionModalProps) {
  const isEdit = connection != null;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [provider, setProvider] = useState<AiOcrProvider>("gemini");
  const [model, setModel] = useState(DEFAULT_GEMINI_MODEL);
  const [account, setAccount] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [awsRegion, setAwsRegion] = useState(DEFAULT_BEDROCK_REGION);
  const [promptTemplateId, setPromptTemplateId] = useState<number | "">("");

  useEffect(() => {
    if (!open) {
      return;
    }
    setError("");
    setApiKey("");
    if (connection) {
      setProvider(connection.provider);
      setModel(connection.model);
      setAccount(connection.account ?? "");
      setAwsRegion(connection.aws_region ?? DEFAULT_BEDROCK_REGION);
      setPromptTemplateId(connection.prompt_template_id ?? defaultPromptTemplateId ?? "");
      return;
    }
    setProvider("gemini");
    setModel(DEFAULT_GEMINI_MODEL);
    setAccount("");
    setAwsRegion(DEFAULT_BEDROCK_REGION);
    setPromptTemplateId(defaultPromptTemplateId ?? promptTemplates[0]?.id ?? "");
  }, [open, connection, defaultPromptTemplateId, promptTemplates]);

  function handleProviderChange(next: AiOcrProvider) {
    setProvider(next);
    setApiKey("");
    if (next === "openai") {
      setModel(DEFAULT_OPENAI_MODEL);
      return;
    }
    if (next === "bedrock") {
      setModel(DEFAULT_BEDROCK_MODEL);
      return;
    }
    setModel(DEFAULT_GEMINI_MODEL);
  }

  if (!open) {
    return null;
  }

  async function handleSubmit() {
    const trimmedKey = apiKey.trim();
    if (!isEdit && !trimmedKey) {
      setError(
        provider === "bedrock"
          ? "Bedrock API 키를 입력하세요."
          : "API 키를 입력하세요.",
      );
      return;
    }
    if (promptTemplateId === "") {
      setError("OCR 프롬프트를 선택하세요.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      if (isEdit && connection) {
        await apiClient.updateAiOcrConnection(connection.id, {
          model,
          account: account.trim() || null,
          api_key: trimmedKey || undefined,
          aws_region: provider === "bedrock" ? awsRegion.trim() || DEFAULT_BEDROCK_REGION : undefined,
          prompt_template_id: Number(promptTemplateId),
        });
      } else {
        await apiClient.createAiOcrConnection({
          provider,
          model,
          account: account.trim() || null,
          api_key: trimmedKey,
          aws_region: provider === "bedrock" ? awsRegion.trim() || DEFAULT_BEDROCK_REGION : null,
          prompt_template_id: Number(promptTemplateId),
          set_active: true,
        });
      }
      onSaved();
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const modelOptions = modelOptionsForProvider(provider);
  const providerLabel = AI_PROVIDER_OPTIONS.find((item) => item.value === provider)?.label ?? provider;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ margin: 0 }}>{isEdit ? "AI 연동 수정" : "AI 연동 추가"}</h3>
          <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <p className="muted" style={{ marginTop: 0 }}>
          같은 AI 제공자라도 계정·API 키가 다르면 여러 개 등록할 수 있습니다.
        </p>

        {error ? <p className="ai-ocr-settings-error">{error}</p> : null}

        <div className="form-grid">
          <label>
            AI 종류
            <select
              value={provider}
              disabled={isEdit}
              onChange={(event) => handleProviderChange(event.target.value as AiOcrProvider)}
            >
              {AI_PROVIDER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            AI 모델
            <select value={model} onChange={(event) => setModel(event.target.value)}>
              {modelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {provider === "bedrock" ? (
            <p className="muted ai-ocr-settings-hint" style={{ gridColumn: "1 / -1", margin: 0 }}>
              실제 API 호출 ID (리전 {awsRegion.trim() || DEFAULT_BEDROCK_REGION}):{" "}
              <code>
                {bedrockInferenceProfileId(model, awsRegion.trim() || DEFAULT_BEDROCK_REGION)}
              </code>
              {" — "}Nova·Claude는 foundation model ID 직접 호출이 불가하여 백엔드가 inference profile로 변환합니다.
            </p>
          ) : null}

          {promptTemplates.length > 0 ? (
            <label>
              OCR 프롬프트
              <select
                value={promptTemplateId === "" ? "" : String(promptTemplateId)}
                onChange={(event) => {
                  const value = event.target.value;
                  setPromptTemplateId(value === "" ? "" : Number(value));
                }}
              >
                <option value="" disabled>
                  프롬프트 선택
                </option>
                {promptTemplates.map((template) => (
                  <option key={template.id} value={String(template.id)}>
                    {template.name}
                    {template.is_builtin ? " · 기본" : ""}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label>
            계정 (표시용)
            <input
              type="text"
              value={account}
              onChange={(event) => setAccount(event.target.value)}
              placeholder={
                provider === "bedrock" ? "예: prod-bedrock" : provider === "gemini" ? "예: gsneotek-dev" : "예: my-org"
              }
            />
          </label>

          {provider === "bedrock" ? (
            <label>
              AWS 리전
              <input
                type="text"
                value={awsRegion}
                onChange={(event) => setAwsRegion(event.target.value)}
                placeholder={DEFAULT_BEDROCK_REGION}
              />
            </label>
          ) : null}

          <label>
            {provider === "bedrock" ? "Bedrock API 키" : "API 키"}
            <input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={
                isEdit && connection?.has_api_key
                  ? "변경할 때만 입력"
                  : provider === "bedrock"
                    ? "Bedrock 콘솔에서 생성한 API 키"
                    : provider === "gemini"
                      ? "AIza..."
                      : "sk-..."
              }
              autoComplete="off"
            />
          </label>
        </div>

        <p className="muted ai-ocr-settings-hint">
          {provider === "bedrock"
            ? "Amazon Bedrock 콘솔 → API keys에서 생성한 Bedrock API 키를 입력하세요. (Bearer 토큰 방식, IAM Access Key 불필요)"
            : provider === "gemini"
              ? "Google AI Studio에서 발급한 API 키를 입력하세요."
              : "OpenAI Platform에서 발급한 API 키를 입력하세요."}
        </p>

        {isEdit && connection ? (
          <p className="muted ai-ocr-settings-hint">
            {providerLabel} · 키: {connection.api_key_masked ?? "—"}
          </p>
        ) : null}

        <div className="ai-settings-card-actions" style={{ marginTop: 16 }}>
          <button type="button" className="button-primary" disabled={saving} onClick={() => void handleSubmit()}>
            {saving ? "저장 중..." : isEdit ? "수정 저장" : "추가"}
          </button>
          <button type="button" className="button-ghost" disabled={saving} onClick={onClose}>
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
