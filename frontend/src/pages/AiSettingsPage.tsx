import { useCallback, useEffect, useState } from "react";
import { Bot, KeyRound, Plus, Trash2, Zap } from "lucide-react";
import { apiClient, type AiOcrConnection, type AiOcrSettings } from "../api/client";
import { modelOptionsForProvider } from "../constants/aiModelOptions";
import AiOcrConnectionModal from "../components/AiOcrConnectionModal";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import { formatAiOcrPromptLabel } from "../utils/formatAiOcrPromptLabel";

/**
 * AI 설정 페이지 — Vision API 연동 프로필 및 연동별 OCR 프롬프트 선택.
 */
export default function AiSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [connectionBusy, setConnectionBusy] = useState(false);
  const [testingConnectionId, setTestingConnectionId] = useState<number | null>(null);
  const [updatingPromptConnectionId, setUpdatingPromptConnectionId] = useState<number | null>(null);
  const [updatingModelConnectionId, setUpdatingModelConnectionId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [settings, setSettings] = useState<AiOcrSettings | null>(null);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<AiOcrConnection | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getAiOcrSettings();
      setSettings(data);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "AI 설정을 불러오지 못했습니다.",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  async function handleActivateConnection(connectionId: number) {
    setConnectionBusy(true);
    setMessage(null);
    try {
      const updated = await apiClient.activateAiOcrConnection(connectionId);
      setSettings(updated);
      setMessage({ type: "ok", text: "OCR 분석에 사용할 연동이 변경되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "활성 연동 변경에 실패했습니다.",
      });
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleConnectionModelChange(connectionId: number, model: string) {
    setUpdatingModelConnectionId(connectionId);
    setMessage(null);
    try {
      await apiClient.updateAiOcrConnection(connectionId, { model });
      const updated = await apiClient.getAiOcrSettings();
      setSettings(updated);
      setMessage({ type: "ok", text: "연동 AI 모델이 저장되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "모델 변경에 실패했습니다.",
      });
    } finally {
      setUpdatingModelConnectionId(null);
    }
  }

  async function handleConnectionPromptChange(connectionId: number, promptTemplateId: number) {
    setUpdatingPromptConnectionId(connectionId);
    setMessage(null);
    try {
      await apiClient.updateAiOcrConnection(connectionId, {
        prompt_template_id: promptTemplateId,
      });
      const updated = await apiClient.getAiOcrSettings();
      setSettings(updated);
      setMessage({ type: "ok", text: "연동에 사용할 프롬프트가 저장되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "프롬프트 지정에 실패했습니다.",
      });
    } finally {
      setUpdatingPromptConnectionId(null);
    }
  }

  async function handleTestConnection(connection: AiOcrConnection) {
    setTestingConnectionId(connection.id);
    setMessage(null);
    try {
      const result = await apiClient.testAiOcrConnection(connection.id);
      const latency = result.latency_ms != null ? ` (${result.latency_ms}ms)` : "";
      setMessage({
        type: result.success ? "ok" : "error",
        text: `${connection.label}: ${result.message}${latency}`,
      });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "연결 테스트에 실패했습니다.",
      });
    } finally {
      setTestingConnectionId(null);
    }
  }

  async function handleDeleteConnection(connection: AiOcrConnection) {
    if (!window.confirm(`「${connection.label}」 연동을 삭제할까요?`)) {
      return;
    }
    setConnectionBusy(true);
    setMessage(null);
    try {
      await apiClient.deleteAiOcrConnection(connection.id);
      const updated = await apiClient.getAiOcrSettings();
      setSettings(updated);
      setMessage({ type: "ok", text: "AI 연동이 삭제되었습니다." });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "연동 삭제에 실패했습니다.",
      });
    } finally {
      setConnectionBusy(false);
    }
  }

  const promptTemplates = settings?.prompt_templates ?? [];
  const defaultPromptId =
    settings?.active_prompt_id ?? promptTemplates[0]?.id ?? null;

  return (
    <section className="page ai-settings-page">
      <header className="page-top">
        <h2 className="page-title">
          <Bot size={24} aria-hidden="true" />
          AI 연동
        </h2>
        <p className="page-lead">
          이미지 OCR·아티클 변환에 사용할 AI 연동(API 키·모델)을 관리합니다. 테이블에서 모델·OCR
          프롬프트를 바로 바꿀 수 있으며, 프롬프트 본문은 「OCR 프롬프트」 메뉴에서 편집합니다.
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
        <div className="card ai-settings-card" style={{ maxWidth: "none" }}>
          <div className="ai-settings-card-header-row">
            <h3 className="title-with-icon">
              <KeyRound size={18} aria-hidden="true" />
              API 연동
            </h3>
            <button
              type="button"
              className="button-ghost"
              disabled={connectionBusy}
              onClick={() => {
                setEditingConnection(null);
                setConnectionModalOpen(true);
              }}
            >
              <Plus size={16} aria-hidden="true" />
              추가하기
            </button>
          </div>
          <p className="muted ai-settings-card-lead">
            Gemini·OpenAI·AWS Bedrock 등을 여러 개 등록할 수 있습니다. 「AI 모델」「프롬프트」
            열에서 바로 변경하고, 「사용」으로 OCR 분석에 쓸 연동을 지정합니다.
          </p>

          {settings?.connections.length === 0 ? (
            <p className="muted">등록된 AI 연동이 없습니다. 「추가하기」로 연동을 등록하세요.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 14,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left" }}>
                    <th style={{ padding: "10px 8px" }}>연동</th>
                    <th style={{ padding: "10px 8px", minWidth: 200 }}>AI 모델</th>
                    <th style={{ padding: "10px 8px", minWidth: 200 }}>OCR 프롬프트</th>
                    <th style={{ padding: "10px 8px" }}>키</th>
                    <th style={{ padding: "10px 8px" }}>상태</th>
                    <th style={{ padding: "10px 8px" }}>작업</th>
                  </tr>
                </thead>
                <tbody>
                  {(settings?.connections ?? []).map((connection) => {
                    const keyReady = connection.has_api_key;
                    const isTesting = testingConnectionId === connection.id;
                    const isUpdatingPrompt = updatingPromptConnectionId === connection.id;
                    const isUpdatingModel = updatingModelConnectionId === connection.id;
                    const modelOptions = modelOptionsForProvider(connection.provider);
                    const resolvedPromptId =
                      connection.prompt_template_id ?? defaultPromptId;
                    const promptSelectValue =
                      resolvedPromptId != null ? String(resolvedPromptId) : "";

                    return (
                      <tr key={connection.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                        <td style={{ padding: "10px 8px" }}>
                          <strong>{connection.label}</strong>
                        </td>
                        <td style={{ padding: "10px 8px" }}>
                          <select
                            className="ai-settings-table-select"
                            value={connection.model}
                            disabled={connectionBusy || isUpdatingModel}
                            onChange={(event) => {
                              const nextModel = event.target.value;
                              if (nextModel && nextModel !== connection.model) {
                                void handleConnectionModelChange(connection.id, nextModel);
                              }
                            }}
                            aria-label={`${connection.label} AI 모델`}
                          >
                            {modelOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td style={{ padding: "10px 8px" }}>
                          <select
                            className="ai-settings-table-select"
                            value={promptSelectValue}
                            disabled={
                              connectionBusy ||
                              isUpdatingPrompt ||
                              promptTemplates.length === 0
                            }
                            onChange={(event) => {
                              const nextId = Number(event.target.value);
                              if (!Number.isNaN(nextId)) {
                                void handleConnectionPromptChange(connection.id, nextId);
                              }
                            }}
                            aria-label={`${connection.label} OCR 프롬프트`}
                          >
                            {promptTemplates.length === 0 ? (
                              <option value="">프롬프트 없음</option>
                            ) : null}
                            {promptTemplates.map((template) => (
                              <option key={template.id} value={String(template.id)}>
                                {formatAiOcrPromptLabel(template)}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td style={{ padding: "10px 8px" }}>{connection.api_key_masked ?? "—"}</td>
                        <td style={{ padding: "10px 8px" }}>
                          {connection.is_active ? (
                            <span>사용 중</span>
                          ) : keyReady ? (
                            <span className="muted">대기</span>
                          ) : (
                            <span className="ai-ocr-provider-status-warn">키 미설정</span>
                          )}
                        </td>
                        <td style={{ padding: "10px 8px" }}>
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <button
                              type="button"
                              className="icon-button"
                              title="연결 테스트"
                              disabled={connectionBusy || !keyReady || isTesting}
                              onClick={() => void handleTestConnection(connection)}
                            >
                              <Zap size={14} aria-hidden="true" />
                              {isTesting ? "…" : "테스트"}
                            </button>
                            {!connection.is_active ? (
                              <button
                                type="button"
                                className="icon-button"
                                disabled={connectionBusy || !keyReady}
                                onClick={() => void handleActivateConnection(connection.id)}
                              >
                                사용
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="icon-button"
                              disabled={connectionBusy}
                              onClick={() => {
                                setEditingConnection(connection);
                                setConnectionModalOpen(true);
                              }}
                            >
                              수정
                            </button>
                            <button
                              type="button"
                              className="icon-button"
                              disabled={connectionBusy}
                              onClick={() => void handleDeleteConnection(connection)}
                            >
                              <Trash2 size={14} aria-hidden="true" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <AiOcrConnectionModal
        open={connectionModalOpen}
        connection={editingConnection}
        promptTemplates={promptTemplates}
        defaultPromptTemplateId={defaultPromptId}
        onClose={() => {
          setConnectionModalOpen(false);
          setEditingConnection(null);
        }}
        onSaved={() => {
          void loadSettings();
          setMessage({
            type: "ok",
            text: editingConnection ? "AI 연동이 수정되었습니다." : "AI 연동이 추가되었습니다.",
          });
        }}
      />
    </section>
  );
}
