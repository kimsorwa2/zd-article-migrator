import { useCallback, useEffect, useMemo, useState } from "react";
import { Bot, KeyRound, MessageSquareText, Plus, RotateCcw, Trash2 } from "lucide-react";
import {
  apiClient,
  type AiOcrPromptTemplate,
  type AiOcrProvider,
  type AiOcrSettings,
} from "../api/client";
import AiProviderModelFields from "../components/AiProviderModelFields";
import { AI_PROVIDER_OPTIONS } from "../components/AiOcrSettingsModal";
import { DEFAULT_GEMINI_MODEL, DEFAULT_OPENAI_MODEL } from "../constants/aiModelOptions";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";

/** 새 프롬프트 작성 모드 식별자 */
const NEW_PROMPT_ID = "new" as const;

type SelectedPromptId = number | typeof NEW_PROMPT_ID | "";

/**
 * AI 설정 상세 페이지 — API 연동·다중 프롬프트 템플릿 관리.
 */
export default function AiSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [savingApi, setSavingApi] = useState(false);
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [settings, setSettings] = useState<AiOcrSettings | null>(null);

  const [activeProvider, setActiveProvider] = useState<AiOcrProvider>("gemini");
  const [geminiAccount, setGeminiAccount] = useState("");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [openaiAccount, setOpenaiAccount] = useState("");
  const [openaiApiKey, setOpenaiApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState(DEFAULT_GEMINI_MODEL);
  const [openaiModel, setOpenaiModel] = useState(DEFAULT_OPENAI_MODEL);

  const [selectedPromptId, setSelectedPromptId] = useState<SelectedPromptId>("");
  const [promptName, setPromptName] = useState("");
  const [promptDescription, setPromptDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [userPrompt, setUserPrompt] = useState("");

  const selectedTemplate = useMemo(() => {
    if (!settings || selectedPromptId === "" || selectedPromptId === NEW_PROMPT_ID) {
      return null;
    }
    return settings.prompt_templates.find((item) => item.id === selectedPromptId) ?? null;
  }, [settings, selectedPromptId]);

  const isNewPromptMode = selectedPromptId === NEW_PROMPT_ID;
  const isActivePrompt =
    settings !== null &&
    selectedTemplate !== null &&
    settings.active_prompt_id === selectedTemplate.id;

  const applyTemplateToForm = useCallback((template: AiOcrPromptTemplate | null, defaults: AiOcrSettings) => {
    if (template) {
      setPromptName(template.name);
      setPromptDescription(template.description ?? "");
      setSystemPrompt(template.system_prompt);
      setUserPrompt(template.user_prompt);
      return;
    }
    setPromptName("");
    setPromptDescription("");
    setSystemPrompt(defaults.default_system_prompt);
    setUserPrompt(defaults.default_user_prompt);
  }, []);

  const applySettingsToForm = useCallback(
    (data: AiOcrSettings, preferredPromptId?: SelectedPromptId) => {
      setSettings(data);
      setActiveProvider(data.active_provider);
      setGeminiAccount(data.gemini.account ?? "");
      setOpenaiAccount(data.openai.account ?? "");
      setGeminiModel(data.gemini.model);
      setOpenaiModel(data.openai.model);
      setGeminiApiKey("");
      setOpenaiApiKey("");

      let nextId: SelectedPromptId = preferredPromptId ?? "";
      if (nextId === "" && data.active_prompt_id) {
        nextId = data.active_prompt_id;
      }
      if (nextId === NEW_PROMPT_ID) {
        setSelectedPromptId(NEW_PROMPT_ID);
        applyTemplateToForm(null, data);
        return;
      }

      const template =
        typeof nextId === "number"
          ? data.prompt_templates.find((item) => item.id === nextId) ?? null
          : data.prompt_templates.find((item) => item.id === data.active_prompt_id) ??
            data.prompt_templates[0] ??
            null;

      if (template) {
        setSelectedPromptId(template.id);
        applyTemplateToForm(template, data);
        return;
      }

      setSelectedPromptId(NEW_PROMPT_ID);
      applyTemplateToForm(null, data);
    },
    [applyTemplateToForm],
  );

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getAiOcrSettings();
      applySettingsToForm(data);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "AI 설정을 불러오지 못했습니다.",
      });
    } finally {
      setLoading(false);
    }
  }, [applySettingsToForm]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  function handleProviderChange(provider: AiOcrProvider) {
    setActiveProvider(provider);
    setGeminiApiKey("");
    setOpenaiApiKey("");
  }

  function handlePromptSelect(promptId: string) {
    if (!settings) {
      return;
    }
    if (promptId === String(NEW_PROMPT_ID)) {
      setSelectedPromptId(NEW_PROMPT_ID);
      applyTemplateToForm(null, settings);
      return;
    }
    const id = Number(promptId);
    const template = settings.prompt_templates.find((item) => item.id === id);
    if (!template) {
      return;
    }
    setSelectedPromptId(id);
    applyTemplateToForm(template, settings);
  }

  function handleResetPrompts() {
    if (!settings) {
      return;
    }
    setSystemPrompt(settings.default_system_prompt);
    setUserPrompt(settings.default_user_prompt);
    setMessage({ type: "ok", text: "편집 중인 프롬프트가 기본값으로 채워졌습니다. 저장하면 반영됩니다." });
  }

  async function handleSaveApi() {
    setSavingApi(true);
    setMessage(null);
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
      applySettingsToForm(updated, selectedPromptId);
      setMessage({ type: "ok", text: "API 연동 설정이 저장되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "API 설정 저장에 실패했습니다.",
      });
    } finally {
      setSavingApi(false);
    }
  }

  async function handleSavePrompt() {
    if (!settings) {
      return;
    }
    const name = promptName.trim();
    if (!name) {
      setMessage({ type: "error", text: "프롬프트 이름을 입력하세요." });
      return;
    }
    if (!systemPrompt.trim() || !userPrompt.trim()) {
      setMessage({ type: "error", text: "시스템·사용자 프롬프트를 모두 입력하세요." });
      return;
    }

    setSavingPrompt(true);
    setMessage(null);
    try {
      if (isNewPromptMode) {
        const created = await apiClient.createAiOcrPrompt({
          name,
          description: promptDescription.trim() || null,
          system_prompt: systemPrompt,
          user_prompt: userPrompt,
          set_active: false,
        });
        const refreshed = await apiClient.getAiOcrSettings();
        applySettingsToForm(refreshed, created.id);
        setMessage({ type: "ok", text: `프롬프트 「${created.name}」이(가) 추가되었습니다.` });
        return;
      }

      if (typeof selectedPromptId !== "number") {
        return;
      }

      await apiClient.updateAiOcrPrompt(selectedPromptId, {
        name,
        description: promptDescription.trim() || null,
        system_prompt: systemPrompt,
        user_prompt: userPrompt,
      });
      const refreshed = await apiClient.getAiOcrSettings();
      applySettingsToForm(refreshed, selectedPromptId);
      setMessage({ type: "ok", text: "프롬프트가 저장되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "프롬프트 저장에 실패했습니다.",
      });
    } finally {
      setSavingPrompt(false);
    }
  }

  async function handleSetActivePrompt() {
    if (!settings || typeof selectedPromptId !== "number") {
      setMessage({ type: "error", text: "OCR에 사용할 프롬프트를 선택하세요." });
      return;
    }

    setSavingPrompt(true);
    setMessage(null);
    try {
      const updated = await apiClient.updateAiOcrSettings({ active_prompt_id: selectedPromptId });
      applySettingsToForm(updated, selectedPromptId);
      setMessage({ type: "ok", text: "이 프롬프트가 OCR 분석에 사용됩니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "활성 프롬프트 지정에 실패했습니다.",
      });
    } finally {
      setSavingPrompt(false);
    }
  }

  async function handleDeletePrompt() {
    if (!settings || typeof selectedPromptId !== "number" || selectedTemplate?.is_builtin) {
      return;
    }

    if (!window.confirm(`「${selectedTemplate?.name}」 프롬프트를 삭제할까요?`)) {
      return;
    }

    setSavingPrompt(true);
    setMessage(null);
    try {
      await apiClient.deleteAiOcrPrompt(selectedPromptId);
      const refreshed = await apiClient.getAiOcrSettings();
      applySettingsToForm(refreshed);
      setMessage({ type: "ok", text: "프롬프트가 삭제되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "프롬프트 삭제에 실패했습니다.",
      });
    } finally {
      setSavingPrompt(false);
    }
  }

  const selectValue =
    selectedPromptId === NEW_PROMPT_ID ? NEW_PROMPT_ID : selectedPromptId === "" ? "" : String(selectedPromptId);

  return (
    <section className="page ai-settings-page">
      <header className="page-top">
        <h2 className="page-title">
          <Bot size={24} aria-hidden="true" />
          AI 설정
        </h2>
        <p className="page-lead">
          이미지 OCR 분석에 사용할 AI 제공자·API 키와 Vision 프롬프트 템플릿을 관리합니다. 여러 프롬프트를
          저장해 두고 「OCR에 사용」으로 분석에 적용할 항목을 선택할 수 있습니다.
        </p>
      </header>

      {message ? (
        <NoticeBanner
          variant={message.type === "error" ? "error" : "info"}
          message={message.text}
          onDismiss={() => setMessage(null)}
        />
      ) : null}

      {loading ? (
        <LoadingPanel variant="panel" message="AI 설정을 불러오는 중..." showSpinner={false} />
      ) : (
        <div className="ai-settings-grid">
          <div className="card ai-settings-card">
            <h3 className="title-with-icon">
              <KeyRound size={18} aria-hidden="true" />
              API 연동
            </h3>
            <p className="muted ai-settings-card-lead">
              분석에 사용할 AI를 선택한 뒤, 해당 제공자의 Vision 모델·계정·API 키를 등록하세요.
            </p>

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

            <div className="ai-settings-card-actions">
              <button type="button" className="button-primary" disabled={savingApi} onClick={() => void handleSaveApi()}>
                {savingApi ? "저장 중..." : "API 설정 저장"}
              </button>
            </div>
          </div>

          <div className="card ai-settings-card">
            <div className="ai-settings-card-header-row">
              <h3 className="title-with-icon">
                <MessageSquareText size={18} aria-hidden="true" />
                프롬프트 관리
              </h3>
              <button
                type="button"
                className="button-ghost"
                onClick={() => settings && handlePromptSelect(NEW_PROMPT_ID)}
              >
                <Plus size={16} aria-hidden="true" />
                새 프롬프트
              </button>
            </div>
            <p className="muted ai-settings-card-lead">
              프롬프트를 여러 개 저장해 두고, OCR 분석에 쓸 템플릿을 선택하세요.
            </p>

            <label>
              저장된 프롬프트
              <select value={selectValue} onChange={(event) => handlePromptSelect(event.target.value)}>
                <option value="" disabled>
                  프롬프트 선택
                </option>
                {settings?.prompt_templates.map((template) => (
                  <option key={template.id} value={String(template.id)}>
                    {template.name}
                    {settings.active_prompt_id === template.id ? " (OCR 사용 중)" : ""}
                    {template.is_builtin ? " · 기본" : ""}
                  </option>
                ))}
                <option value={NEW_PROMPT_ID}>+ 새 프롬프트 작성</option>
              </select>
            </label>

            {isActivePrompt ? (
              <p className="ai-settings-prompt-badge">OCR 분석에 사용 중</p>
            ) : isNewPromptMode ? (
              <p className="muted ai-settings-prompt-badge">새 프롬프트 작성 중</p>
            ) : selectedTemplate ? (
              <p className="muted ai-settings-prompt-badge">편집 중 — 저장 후 「OCR에 사용」으로 적용하세요</p>
            ) : null}

            <label>
              프롬프트 이름
              <input
                type="text"
                value={promptName}
                onChange={(event) => setPromptName(event.target.value)}
                placeholder="예: 가전 매뉴얼용"
                disabled={selectedTemplate?.is_builtin}
              />
            </label>

            <label>
              설명 (선택)
              <input
                type="text"
                value={promptDescription}
                onChange={(event) => setPromptDescription(event.target.value)}
                placeholder="용도 메모"
                disabled={selectedTemplate?.is_builtin}
              />
            </label>

            <div className="ai-settings-prompt-toolbar">
              <button type="button" className="button-ghost" onClick={handleResetPrompts}>
                <RotateCcw size={16} aria-hidden="true" />
                기본값으로
              </button>
            </div>

            <label>
              시스템 프롬프트
              <textarea
                className="ai-settings-prompt-textarea"
                value={systemPrompt}
                onChange={(event) => setSystemPrompt(event.target.value)}
                rows={14}
                spellCheck={false}
                readOnly={selectedTemplate?.is_builtin}
              />
            </label>

            <label>
              사용자 프롬프트
              <textarea
                className="ai-settings-prompt-textarea ai-settings-prompt-textarea-sm"
                value={userPrompt}
                onChange={(event) => setUserPrompt(event.target.value)}
                rows={3}
                spellCheck={false}
                readOnly={selectedTemplate?.is_builtin}
              />
            </label>

            {selectedTemplate?.is_builtin ? (
              <p className="muted ai-ocr-settings-hint">기본 프롬프트는 읽기 전용입니다. 복사 후 새 프롬프트로 저장하세요.</p>
            ) : null}

            <div className="ai-settings-prompt-actions">
              <button
                type="button"
                className="button-primary"
                disabled={savingPrompt || selectedPromptId === ""}
                onClick={() => void handleSavePrompt()}
              >
                {savingPrompt ? "저장 중..." : isNewPromptMode ? "프롬프트 추가" : "프롬프트 저장"}
              </button>
              <button
                type="button"
                className="button-secondary"
                disabled={savingPrompt || isNewPromptMode || typeof selectedPromptId !== "number"}
                onClick={() => void handleSetActivePrompt()}
              >
                OCR에 사용
              </button>
              <button
                type="button"
                className="button-ghost ai-settings-delete-button"
                disabled={
                  savingPrompt ||
                  isNewPromptMode ||
                  !selectedTemplate ||
                  selectedTemplate.is_builtin
                }
                onClick={() => void handleDeletePrompt()}
              >
                <Trash2 size={16} aria-hidden="true" />
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
