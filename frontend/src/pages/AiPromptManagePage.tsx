import { useCallback, useEffect, useMemo, useState } from "react";
import { MessageSquareText, Plus, RotateCcw, Trash2 } from "lucide-react";
import {
  apiClient,
  type AiOcrPromptTemplate,
  type AiOcrSettings,
} from "../api/client";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import { formatAiOcrPromptLabel } from "../utils/formatAiOcrPromptLabel";

/** 새 프롬프트 작성 모드 식별자 */
const NEW_PROMPT_ID = "new" as const;

type SelectedPromptId = number | typeof NEW_PROMPT_ID | "";

/**
 * OCR Vision 프롬프트 템플릿 전용 관리 페이지.
 */
export default function AiPromptManagePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [settings, setSettings] = useState<AiOcrSettings | null>(null);

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
        text: error instanceof Error ? error.message : "프롬프트 목록을 불러오지 못했습니다.",
      });
    } finally {
      setLoading(false);
    }
  }, [applySettingsToForm]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

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

    setSaving(true);
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
      setSaving(false);
    }
  }

  async function handleDeletePrompt() {
    if (!settings || typeof selectedPromptId !== "number" || selectedTemplate?.is_builtin) {
      return;
    }

    if (!window.confirm(`「${selectedTemplate?.name}」 프롬프트를 삭제할까요?`)) {
      return;
    }

    setSaving(true);
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
      setSaving(false);
    }
  }

  const selectValue =
    selectedPromptId === NEW_PROMPT_ID ? NEW_PROMPT_ID : selectedPromptId === "" ? "" : String(selectedPromptId);

  return (
    <section className="page ai-prompt-manage-page">
      <header className="page-top">
        <h2 className="page-title">
          <MessageSquareText size={24} aria-hidden="true" />
          프롬프트 관리
        </h2>
        <p className="page-lead">
          이미지 OCR·아티클 변환에 쓸 Vision 프롬프트 템플릿을 등록·수정합니다. 이름은 중복해도 되며
          ID(#번호)로 구분합니다. AI 설정에서 연동마다 사용할 프롬프트를 선택할 수 있습니다.
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
        <LoadingPanel variant="panel" message="프롬프트를 불러오는 중..." showSpinner={false} />
      ) : (
        <div className="card ai-settings-card" style={{ maxWidth: "none" }}>
          <div className="ai-settings-card-header-row">
            <h3 className="title-with-icon" style={{ margin: 0 }}>
              저장된 프롬프트
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

          <label>
            프롬프트 선택
            <select value={selectValue} onChange={(event) => handlePromptSelect(event.target.value)}>
              <option value="" disabled>
                프롬프트 선택
              </option>
              {settings?.prompt_templates.map((template) => (
                <option key={template.id} value={String(template.id)}>
                  {formatAiOcrPromptLabel(template)}
                </option>
              ))}
              <option value={NEW_PROMPT_ID}>+ 새 프롬프트 작성</option>
            </select>
          </label>

          {isNewPromptMode ? (
            <p className="muted ai-settings-prompt-badge">새 프롬프트 작성 중</p>
          ) : selectedTemplate ? (
            <p className="muted ai-settings-prompt-badge">
              편집 중 — ID #{selectedTemplate.id}
              {selectedTemplate.is_builtin ? " · 기본 프롬프트(이름·설명만 저장 가능)" : ""}
            </p>
          ) : null}

          <label>
            프롬프트 이름
            <input
              type="text"
              value={promptName}
              onChange={(event) => setPromptName(event.target.value)}
              placeholder="예: 가전 매뉴얼용 (동일 이름 가능)"
              disabled={selectedPromptId === ""}
            />
          </label>

          <label>
            설명 (선택)
            <input
              type="text"
              value={promptDescription}
              onChange={(event) => setPromptDescription(event.target.value)}
              placeholder="용도·버전 메모"
              disabled={selectedPromptId === ""}
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
              rows={16}
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
            <p className="muted ai-ocr-settings-hint">
              기본 프롬프트 본문(시스템·사용자)은 읽기 전용입니다. 이름·설명만 수정하거나, 복사 후 새
              프롬프트로 저장하세요.
            </p>
          ) : null}

          <div className="ai-settings-prompt-actions">
            <button
              type="button"
              className="button-primary"
              disabled={saving || selectedPromptId === ""}
              onClick={() => void handleSavePrompt()}
            >
              {saving ? "저장 중..." : isNewPromptMode ? "프롬프트 추가" : "프롬프트 저장"}
            </button>
            <button
              type="button"
              className="button-ghost ai-settings-delete-button"
              disabled={saving || isNewPromptMode || !selectedTemplate || selectedTemplate.is_builtin}
              onClick={() => void handleDeletePrompt()}
            >
              <Trash2 size={16} aria-hidden="true" />
              삭제
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
