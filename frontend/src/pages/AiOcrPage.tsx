import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CheckCircle2,
  FileImage,
  FolderOpen,
  Loader2,
  Settings,
  Sparkles,
  Upload,
} from "lucide-react";
import {
  apiClient,
  type AiOcrAnalysisHistoryItem,
  type AiOcrAnalyzeResult,
  type AiOcrProvider,
  type AiOcrSectionSelection,
  type AiOcrSettings,
  type FetchDetailResponse,
  type Instance,
} from "../api/client";
import AiOcrCuteSpinner from "../components/AiOcrCuteSpinner";
import AiOcrHtmlPreview from "../components/AiOcrHtmlPreview";
import AiOcrSettingsModal, { AI_PROVIDER_OPTIONS } from "../components/AiOcrSettingsModal";
import CategorySectionPickerModal from "../components/CategorySectionPickerModal";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import WorkLogAccordion, { type WorkLogEntry } from "../components/WorkLogAccordion";
import { buildAiProviderStatusDisplay } from "../utils/aiProviderStatus";

interface AiOcrPageProps {
  instances: Instance[];
}

type EditMode = "none" | "title" | "labels";

/**
 * 이미지 OCR로 Zendesk 아티클을 생성하는 페이지.
 */
export default function AiOcrPage({ instances }: AiOcrPageProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [instanceId, setInstanceId] = useState<number | "">("");
  const [fetchDetail, setFetchDetail] = useState<FetchDetailResponse | null>(null);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [sectionSelection, setSectionSelection] = useState<AiOcrSectionSelection | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<AiOcrAnalyzeResult | null>(null);
  const [editMode, setEditMode] = useState<EditMode>("none");
  const [editTitle, setEditTitle] = useState("");
  const [editLabels, setEditLabels] = useState("");
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [createdUrl, setCreatedUrl] = useState<string | null>(null);
  const [workLogs, setWorkLogs] = useState<WorkLogEntry[]>([]);
  const [historyItems, setHistoryItems] = useState<AiOcrAnalysisHistoryItem[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | "">("");
  const [aiSettings, setAiSettings] = useState<AiOcrSettings | null>(null);
  const [aiSettingsLoading, setAiSettingsLoading] = useState(true);
  const [providerSaving, setProviderSaving] = useState(false);

  const providerStatus = useMemo(
    () => buildAiProviderStatusDisplay(aiSettings, aiSettingsLoading),
    [aiSettings, aiSettingsLoading],
  );

  const activeInstances = useMemo(
    () => instances.filter((instance) => instance.is_active),
    [instances],
  );

  const loadFetchDetail = useCallback(async (targetInstanceId: number) => {
    setFetchLoading(true);
    setFetchDetail(null);
    setSectionSelection(null);
    try {
      const detail = await apiClient.getFetchDetail(targetInstanceId);
      setFetchDetail(detail);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Help Center 데이터를 불러오지 못했습니다.",
      });
    } finally {
      setFetchLoading(false);
    }
  }, []);

  const loadAiSettings = useCallback(async () => {
    setAiSettingsLoading(true);
    try {
      const settings = await apiClient.getAiOcrSettings();
      setAiSettings(settings);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "AI 설정을 불러오지 못했습니다.",
      });
    } finally {
      setAiSettingsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAiSettings();
  }, [loadAiSettings]);

  async function handleProviderChange(provider: AiOcrProvider) {
    if (!aiSettings || aiSettings.active_provider === provider) {
      return;
    }
    setProviderSaving(true);
    setMessage(null);
    try {
      const updated = await apiClient.updateAiOcrSettings({ active_provider: provider });
      setAiSettings(updated);
      setMessage({ type: "ok", text: `분석 AI가 ${AI_PROVIDER_OPTIONS.find((o) => o.value === provider)?.label}로 변경되었습니다.` });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "AI 제공자 변경에 실패했습니다.",
      });
    } finally {
      setProviderSaving(false);
    }
  }

  const loadHistory = useCallback(async () => {
    try {
      const response = await apiClient.getAiOcrHistory();
      setHistoryItems(response.items);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "이전 분석 이력을 불러오지 못했습니다.",
      });
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  function historyItemToDraft(item: AiOcrAnalysisHistoryItem): AiOcrAnalyzeResult {
    return {
      history_id: item.id,
      title: item.title,
      html_body: item.html_body,
      label_names: item.label_names,
      detected_product: item.detected_product,
      maintenance_cycle: item.maintenance_cycle,
      body_preview_text: item.body_preview_text,
      logs: [],
    };
  }

  function applyHistorySelection(historyId: number | "") {
    setSelectedHistoryId(historyId);
    if (historyId === "") {
      return;
    }
    const item = historyItems.find((entry) => entry.id === historyId);
    if (!item) {
      return;
    }
    const nextDraft = historyItemToDraft(item);
    setDraft(nextDraft);
    setEditTitle(nextDraft.title);
    setEditLabels(nextDraft.label_names.join(", "));
    setEditMode("none");
    setCreatedUrl(null);
  }

  useEffect(() => {
    if (instanceId === "") {
      setFetchDetail(null);
      setSectionSelection(null);
      return;
    }
    void loadFetchDetail(instanceId);
  }, [instanceId, loadFetchDetail]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  function handleFileChange(file: File | null) {
    setSelectedFile(file);
    setCreatedUrl(null);
    setEditMode("none");
  }

  function appendWorkLogs(entries: WorkLogEntry[]) {
    if (entries.length === 0) {
      return;
    }
    setWorkLogs((previous) => [...previous, ...entries]);
  }

  function extractErrorLogs(error: unknown): WorkLogEntry[] {
    if (error && typeof error === "object" && "logs" in error) {
      const logs = (error as { logs?: WorkLogEntry[] }).logs;
      return Array.isArray(logs) ? logs : [];
    }
    return [];
  }

  async function handleAnalyze() {
    if (!selectedFile) {
      setMessage({ type: "error", text: "분석할 이미지를 선택하세요." });
      return;
    }
    setAnalyzing(true);
    setMessage(null);
    setCreatedUrl(null);
    setDraft(null);
    setSelectedHistoryId("");
    setEditMode("none");
    setWorkLogs([]);
    try {
      const result = await apiClient.analyzeAiOcrImage(selectedFile);
      appendWorkLogs(result.logs ?? []);
      setDraft(result);
      setSelectedHistoryId(result.history_id);
      setEditTitle(result.title);
      setEditLabels(result.label_names.join(", "));
      setEditMode("none");
      void loadHistory();
      setMessage({ type: "ok", text: "이미지 분석이 완료되었습니다. 미리보기를 확인하세요." });
    } catch (error) {
      appendWorkLogs(extractErrorLogs(error));
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "이미지 분석에 실패했습니다.",
      });
    } finally {
      setAnalyzing(false);
    }
  }

  function applyEdits() {
    if (!draft) {
      return;
    }
    if (editMode === "title") {
      setDraft({ ...draft, title: editTitle.trim() || draft.title });
    }
    if (editMode === "labels") {
      const labels = editLabels
        .split(",")
        .map((label) => label.trim())
        .filter(Boolean);
      setDraft({ ...draft, label_names: labels });
      setEditLabels(labels.join(", "));
    }
    setEditMode("none");
  }

  async function handleCreateArticle() {
    if (!draft) {
      setMessage({ type: "error", text: "먼저 이미지 분석을 실행하세요." });
      return;
    }
    if (instanceId === "") {
      setMessage({ type: "error", text: "인스턴스를 선택하세요." });
      return;
    }
    if (!sectionSelection) {
      setMessage({ type: "error", text: "카테고리·섹션을 선택하세요." });
      return;
    }

    setCreating(true);
    setMessage(null);
    try {
      const result = await apiClient.createAiOcrArticle({
        instance_id: instanceId,
        brand_id: sectionSelection.brandId,
        section_a_id: sectionSelection.sectionAId,
        title: draft.title,
        html_body: draft.html_body,
        label_names: draft.label_names,
        locale: "ko",
        draft: false,
      });
      appendWorkLogs(result.logs ?? []);
      setCreatedUrl(result.html_url);
      setMessage({
        type: "ok",
        text: `아티클이 생성되었습니다. (ID: ${result.article_id}, 섹션: ${result.section_name})`,
      });
    } catch (error) {
      appendWorkLogs(extractErrorLogs(error));
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "아티클 생성에 실패했습니다.",
      });
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="page ai-ocr-page">
      <header className="page-top">
        <div className="ai-ocr-title-row">
          <h2 className="page-title">이미지로 아티클 생성</h2>
          <button
            type="button"
            className="icon-button ai-ocr-settings-button"
            title="AI 설정"
            onClick={() => setSettingsOpen(true)}
          >
            <Settings size={20} aria-hidden="true" />
            <span className="sr-only">AI 설정</span>
          </button>
        </div>
        <p className="page-lead">
          매뉴얼 이미지를 업로드하면 선택한 AI가 Zendesk 아티클 초안을 만들고, 확인 후 게시합니다.
        </p>
      </header>

      {message ? (
        <NoticeBanner
          variant={message.type === "error" ? "error" : "info"}
          message={message.text}
          onDismiss={() => setMessage(null)}
        />
      ) : null}

      <div className="card ai-ocr-config-card">
        <div className="ai-ocr-provider-row">
          <label className="ai-ocr-provider-select-label">
            분석 AI
            <select
              value={aiSettings?.active_provider ?? "gemini"}
              disabled={providerSaving || !aiSettings}
              onChange={(event) => void handleProviderChange(event.target.value as AiOcrProvider)}
            >
              {AI_PROVIDER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <p
            className={`ai-ocr-provider-status${providerStatus.warn ? " ai-ocr-provider-status-warn" : ""}`}
            aria-live="polite"
          >
            {providerStatus.text}
            {providerStatus.modelId ? ` · 모델: ${providerStatus.modelId}` : ""}
            {providerStatus.promptName ? ` · 프롬프트: ${providerStatus.promptName}` : ""}
          </p>
        </div>

        <label>
          Zendesk 인스턴스
          <select
            value={instanceId}
            onChange={(event) => {
              const value = event.target.value;
              setInstanceId(value ? Number(value) : "");
              setSectionSelection(null);
            }}
          >
            <option value="">인스턴스 선택</option>
            {activeInstances.map((instance) => (
              <option key={instance.id} value={instance.id}>
                {instance.name} ({instance.subdomain})
              </option>
            ))}
          </select>
        </label>

        <div className="ai-ocr-section-picker-row">
          <button
            type="button"
            className="button-ghost ai-ocr-picker-button"
            disabled={instanceId === "" || fetchLoading}
            onClick={() => setPickerOpen(true)}
          >
            <FolderOpen size={16} aria-hidden="true" />
            카테고리 · 섹션 선택
          </button>
          {fetchLoading && instanceId !== "" ? (
            <div className="ai-ocr-fetch-loading">
              <LoadingPanel
                variant="inline"
                showSpinner={false}
                message="카테고리 · 섹션 데이터를 불러오는 중..."
              />
            </div>
          ) : sectionSelection ? (
            <p className="ai-ocr-section-summary">
              <strong>{sectionSelection.brandName}</strong>
              {" · "}
              {sectionSelection.categoryName}
              {" / "}
              {sectionSelection.sectionName}
            </p>
          ) : (
            <p className="muted ai-ocr-section-summary">아티클을 넣을 섹션을 선택하세요.</p>
          )}
        </div>
      </div>

      <div className="ai-ocr-workspace">
        <div className="card ai-ocr-upload-card">
          <h3 className="title-with-icon">
            <Upload size={18} aria-hidden="true" />
            이미지 업로드
          </h3>
          <input
            ref={fileInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            className="ai-ocr-file-input"
            onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            className="button-ghost ai-ocr-file-trigger"
            onClick={() => fileInputRef.current?.click()}
          >
            <FileImage size={18} aria-hidden="true" />
            {selectedFile ? selectedFile.name : "이미지 파일 선택 (jpg, png, webp)"}
          </button>
          <div className="ai-ocr-upload-media">
            {previewUrl ? (
              <img src={previewUrl} alt="업로드 미리보기" className="ai-ocr-image-preview" />
            ) : (
              <div className="ai-ocr-upload-media-placeholder">
                <FileImage size={40} strokeWidth={1.25} aria-hidden="true" />
                <p>선택한 이미지가 여기에 표시됩니다</p>
              </div>
            )}
          </div>
          <button
            type="button"
            className="button-primary"
            disabled={!selectedFile || analyzing || !providerStatus.ready}
            onClick={() => void handleAnalyze()}
          >
            {analyzing ? (
              <>
                <Loader2 size={16} className="spin-icon" aria-hidden="true" />
                분석 중...
              </>
            ) : (
              <>
                <Sparkles size={16} aria-hidden="true" />
                OCR 분석 실행
              </>
            )}
          </button>
        </div>

        <div className="card ai-ocr-preview-card">
          <h3>아티클 미리보기</h3>
          <label
            className={`ai-ocr-history-select-label${analyzing ? " is-disabled" : ""}`}
          >
            이전 분석 결과
            <select
              value={selectedHistoryId}
              disabled={historyItems.length === 0 || analyzing}
              onChange={(event) => {
                const value = event.target.value;
                applyHistorySelection(value ? Number(value) : "");
              }}
            >
              <option value="">
                {historyItems.length === 0 ? "저장된 분석 결과 없음" : "선택하세요"}
              </option>
              {historyItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <div className="ai-ocr-preview-pane">
            {analyzing ? (
              <div className="ai-ocr-preview-pane-empty ai-ocr-preview-pane-loading">
                <AiOcrCuteSpinner />
              </div>
            ) : !draft ? (
              <div className="ai-ocr-preview-pane-empty">
                <p className="muted">분석 결과가 여기에 표시됩니다.</p>
              </div>
            ) : (
              <>
                <dl className="ai-ocr-preview-meta">
                  <div>
                    <dt>제목</dt>
                    <dd>{draft.title}</dd>
                  </div>
                  <div>
                    <dt>감지된 제품</dt>
                    <dd>{draft.detected_product}</dd>
                  </div>
                  <div>
                    <dt>관리 주기</dt>
                    <dd>{draft.maintenance_cycle ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>라벨</dt>
                    <dd>{draft.label_names.join(", ") || "—"}</dd>
                  </div>
                </dl>
                <div className="ai-ocr-preview-body">
                  <p className="ai-ocr-preview-body-title">본문 미리보기</p>
                  <AiOcrHtmlPreview htmlBody={draft.html_body} />
                </div>
              </>
            )}
          </div>
          {draft ? (
            <>
              <div className="ai-ocr-edit-actions">
                <button type="button" className="button-ghost" onClick={() => setEditMode("title")}>
                  제목 수정
                </button>
                <button type="button" className="button-ghost" onClick={() => setEditMode("labels")}>
                  라벨 수정
                </button>
              </div>
              {editMode === "title" ? (
                <label>
                  새 제목
                  <input type="text" value={editTitle} onChange={(event) => setEditTitle(event.target.value)} />
                  <button type="button" className="button-ghost" onClick={applyEdits}>
                    적용
                  </button>
                </label>
              ) : null}
              {editMode === "labels" ? (
                <label>
                  라벨 (쉼표 구분)
                  <input type="text" value={editLabels} onChange={(event) => setEditLabels(event.target.value)} />
                  <button type="button" className="button-ghost" onClick={applyEdits}>
                    적용
                  </button>
                </label>
              ) : null}
              <button
                type="button"
                className="button-primary ai-ocr-create-button"
                disabled={creating || instanceId === "" || !sectionSelection}
                onClick={() => void handleCreateArticle()}
              >
                {creating ? (
                  <>
                    <Loader2 size={16} className="spin-icon" aria-hidden="true" />
                    Zendesk에 생성 중...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={16} aria-hidden="true" />
                    아티클 생성
                  </>
                )}
              </button>
              {createdUrl ? (
                <p className="ai-ocr-created-link">
                  <a href={createdUrl} target="_blank" rel="noopener noreferrer">
                    생성된 아티클 열기
                  </a>
                </p>
              ) : null}
            </>
          ) : null}
        </div>
      </div>

      <WorkLogAccordion title="API 작업 로그" entries={workLogs} />

      <AiOcrSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={(settings) => setAiSettings(settings)}
      />
      <CategorySectionPickerModal
        open={pickerOpen}
        fetchDetail={fetchDetail}
        loading={fetchLoading}
        onClose={() => setPickerOpen(false)}
        onSelect={setSectionSelection}
      />
    </section>
  );
}
