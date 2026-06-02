import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  FileImage,
  FolderOpen,
  Loader2,
  RefreshCw,
  Settings,
  Sparkles,
} from "lucide-react";
import {
  apiClient,
  type AiOcrProvider,
  type AiOcrSectionSelection,
  type AiOcrSettings,
  type FetchDetailResponse,
  type ImageConvertAnalyzeResult,
  type ImageConvertArticleDetail,
  type ImageConvertArticleItem,
  type Instance,
} from "../api/client";
import AiOcrHtmlPreview from "../components/AiOcrHtmlPreview";
import AiOcrSettingsModal, { AI_PROVIDER_OPTIONS } from "../components/AiOcrSettingsModal";
import CategorySectionPickerModal from "../components/CategorySectionPickerModal";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import WorkLogAccordion, { type WorkLogEntry } from "../components/WorkLogAccordion";
import { buildAiProviderStatusDisplay } from "../utils/aiProviderStatus";

interface ConvertImagePageProps {
  instances: Instance[];
}

type EditMode = "none" | "title" | "labels";

/**
 * 소스 인스턴스 아티클 본문 이미지를 AI-OCR하여 타겟 인스턴스에 아티클을 생성하는 페이지.
 */
export default function ConvertImagePage({ instances }: ConvertImagePageProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [workLogs, setWorkLogs] = useState<WorkLogEntry[]>([]);

  const [sourceInstanceId, setSourceInstanceId] = useState<number | "">("");
  const [targetInstanceId, setTargetInstanceId] = useState<number | "">("");
  const [articleSearch, setArticleSearch] = useState("");
  const [articlesLoading, setArticlesLoading] = useState(false);
  const [articles, setArticles] = useState<ImageConvertArticleItem[]>([]);
  const [selectedArticleId, setSelectedArticleId] = useState<number | "">("");
  const [articleDetail, setArticleDetail] = useState<ImageConvertArticleDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [imagePreviewError, setImagePreviewError] = useState<string | null>(null);
  const [localImageFiles, setLocalImageFiles] = useState<Record<number, File>>({});
  const [localPreviewUrls, setLocalPreviewUrls] = useState<Record<number, string>>({});

  const [fetchDetail, setFetchDetail] = useState<FetchDetailResponse | null>(null);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [sectionSelection, setSectionSelection] = useState<AiOcrSectionSelection | null>(null);

  const [aiSettings, setAiSettings] = useState<AiOcrSettings | null>(null);
  const [aiSettingsLoading, setAiSettingsLoading] = useState(true);
  const [providerSaving, setProviderSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<ImageConvertAnalyzeResult | null>(null);
  const [editMode, setEditMode] = useState<EditMode>("none");
  const [editTitle, setEditTitle] = useState("");
  const [editLabels, setEditLabels] = useState("");
  const [createdUrl, setCreatedUrl] = useState<string | null>(null);

  const activeInstances = useMemo(
    () => instances.filter((instance) => instance.is_active),
    [instances],
  );

  const providerStatus = useMemo(
    () => buildAiProviderStatusDisplay(aiSettings, aiSettingsLoading),
    [aiSettings, aiSettingsLoading],
  );

  const selectedBodyImage = articleDetail?.images[selectedImageIndex] ?? null;

  const currentImagePreviewUrl = useMemo(() => {
    if (draft?.image_previews.length) {
      const preview = draft.image_previews.find((item) => item.index === selectedImageIndex);
      return preview?.preview_data_url ?? draft.image_previews[0]?.preview_data_url ?? null;
    }
    const localUrl = localPreviewUrls[selectedImageIndex];
    if (localUrl) {
      return localUrl;
    }
    if (articleDetail && sourceInstanceId !== "" && selectedArticleId !== "") {
      const image = articleDetail.images[selectedImageIndex];
      if (!image || image.availability === "external_paste") {
        return null;
      }
      return apiClient.getImageConvertPreviewUrl(sourceInstanceId, selectedArticleId, image.index);
    }
    return null;
  }, [
    articleDetail,
    draft,
    localPreviewUrls,
    selectedImageIndex,
    selectedArticleId,
    sourceInstanceId,
  ]);

  const imageCount = draft?.image_previews.length ?? articleDetail?.images.length ?? 0;

  const appendWorkLogs = useCallback((entries: WorkLogEntry[]) => {
    if (entries.length === 0) {
      return;
    }
    setWorkLogs((previous) => [...previous, ...entries]);
  }, []);

  const extractErrorLogs = useCallback((error: unknown): WorkLogEntry[] => {
    if (error && typeof error === "object" && "logs" in error) {
      const logs = (error as { logs?: WorkLogEntry[] }).logs;
      return Array.isArray(logs) ? logs : [];
    }
    return [];
  }, []);

  const buildOcrStartLog = useCallback((): WorkLogEntry => {
    const timestamp = new Date().toLocaleTimeString("ko-KR", { hour12: false });
    return {
      timestamp,
      level: "info",
      summary: "OCR 변환 시작",
      body: [
        sourceInstanceId !== "" ? `소스 인스턴스 ID: ${sourceInstanceId}` : null,
        selectedArticleId !== "" ? `아티클 ID: ${selectedArticleId}` : null,
        articleDetail?.title ? `제목: ${articleDetail.title}` : null,
      ]
        .filter(Boolean)
        .join("\n"),
    };
  }, [articleDetail?.title, selectedArticleId, sourceInstanceId]);

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

  const loadArticles = useCallback(async () => {
    if (sourceInstanceId === "") {
      setArticles([]);
      return;
    }
    setArticlesLoading(true);
    try {
      const response = await apiClient.listImageConvertArticles(sourceInstanceId, articleSearch);
      setArticles(response.items);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "이미지 아티클 목록을 불러오지 못했습니다.",
      });
    } finally {
      setArticlesLoading(false);
    }
  }, [articleSearch, sourceInstanceId]);

  const loadArticleDetail = useCallback(async (articleId: number) => {
    if (sourceInstanceId === "") {
      return;
    }
    setDetailLoading(true);
    setArticleDetail(null);
    try {
      const detail = await apiClient.getImageConvertArticleDetail(sourceInstanceId, articleId);
      setArticleDetail(detail);
      setSelectedImageIndex(0);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "아티클 상세를 불러오지 못했습니다.",
      });
    } finally {
      setDetailLoading(false);
    }
  }, [sourceInstanceId]);

  const loadFetchDetail = useCallback(async (instanceId: number) => {
    setFetchLoading(true);
    setFetchDetail(null);
    setSectionSelection(null);
    try {
      const detail = await apiClient.getFetchDetail(instanceId);
      setFetchDetail(detail);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "타겟 Help Center 데이터를 불러오지 못했습니다.",
      });
    } finally {
      setFetchLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAiSettings();
  }, [loadAiSettings]);

  useEffect(() => {
    if (sourceInstanceId === "") {
      setArticles([]);
      setSelectedArticleId("");
      setArticleDetail(null);
      return;
    }
    void loadArticles();
  }, [loadArticles, sourceInstanceId]);

  useEffect(() => {
    if (targetInstanceId === "") {
      setFetchDetail(null);
      setSectionSelection(null);
      return;
    }
    void loadFetchDetail(targetInstanceId);
  }, [loadFetchDetail, targetInstanceId]);

  useEffect(() => {
    if (selectedArticleId === "") {
      setArticleDetail(null);
      setDraft(null);
      setSelectedImageIndex(0);
      return;
    }
    void loadArticleDetail(selectedArticleId);
    setDraft(null);
    setCreatedUrl(null);
    setEditMode("none");
    setLocalImageFiles({});
  }, [loadArticleDetail, selectedArticleId]);

  useEffect(() => {
    const urls: Record<number, string> = {};
    for (const [indexText, file] of Object.entries(localImageFiles)) {
      urls[Number(indexText)] = URL.createObjectURL(file);
    }
    setLocalPreviewUrls(urls);
    return () => {
      for (const url of Object.values(urls)) {
        URL.revokeObjectURL(url);
      }
    };
  }, [localImageFiles]);

  useEffect(() => {
    if (localPreviewUrls[selectedImageIndex]) {
      setImagePreviewError(null);
      return;
    }
    if (selectedBodyImage?.availability === "external_paste" && selectedBodyImage.availability_reason) {
      setImagePreviewError(selectedBodyImage.availability_reason);
      return;
    }
    setImagePreviewError(null);
  }, [localPreviewUrls, selectedBodyImage, selectedImageIndex]);

  useEffect(() => {
    if (!currentImagePreviewUrl || currentImagePreviewUrl.startsWith("data:") || currentImagePreviewUrl.startsWith("blob:")) {
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch(currentImagePreviewUrl);
        if (cancelled || response.ok) {
          return;
        }
        const payload = (await response.json().catch(() => null)) as {
          detail?: { message?: string };
        } | null;
        const apiMessage = payload?.detail?.message?.trim();
        setImagePreviewError(
          apiMessage || `이미지 미리보기를 불러오지 못했습니다. (HTTP ${response.status})`,
        );
      } catch {
        if (!cancelled) {
          setImagePreviewError("이미지 미리보기를 불러오지 못했습니다.");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [currentImagePreviewUrl]);

  async function handleProviderChange(provider: AiOcrProvider) {
    if (!aiSettings || aiSettings.active_provider === provider) {
      return;
    }
    setProviderSaving(true);
    setMessage(null);
    try {
      const updated = await apiClient.updateAiOcrSettings({ active_provider: provider });
      setAiSettings(updated);
      setMessage({
        type: "ok",
        text: `분석 AI가 ${AI_PROVIDER_OPTIONS.find((option) => option.value === provider)?.label}로 변경되었습니다.`,
      });
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "AI 제공자 변경에 실패했습니다.",
      });
    } finally {
      setProviderSaving(false);
    }
  }

  function handleLocalImageFile(index: number, file: File | null) {
    setLocalImageFiles((previous) => {
      const next = { ...previous };
      if (file) {
        next[index] = file;
      } else {
        delete next[index];
      }
      return next;
    });
  }

  async function handleAnalyze() {
    if (sourceInstanceId === "" || selectedArticleId === "") {
      setMessage({ type: "error", text: "소스 인스턴스와 아티클을 선택하세요." });
      return;
    }
    if (!providerStatus.ready) {
      setMessage({ type: "error", text: "AI API 키를 먼저 설정하세요." });
      return;
    }

    const missingExternalPaste = (articleDetail?.images ?? []).filter(
      (image) => image.availability === "external_paste" && !localImageFiles[image.index],
    );
    if (missingExternalPaste.length > 0) {
      setMessage({
        type: "error",
        text: "다른 Zendesk에서 붙여넣은 이미지는 API로 받을 수 없습니다. 로컬 이미지 파일을 지정한 뒤 OCR을 실행하세요.",
      });
      return;
    }

    const overrideIndices = Object.keys(localImageFiles).map((key) => Number(key));

    setAnalyzing(true);
    setMessage(null);
    setCreatedUrl(null);
    setDraft(null);
    setEditMode("none");
    setWorkLogs([buildOcrStartLog()]);

    try {
      const result =
        overrideIndices.length > 0
          ? await apiClient.analyzeImageConvertArticleWithFiles({
              source_instance_id: sourceInstanceId,
              article_id: selectedArticleId,
              image_indices: overrideIndices,
              files: overrideIndices.map((index) => localImageFiles[index]),
            })
          : await apiClient.analyzeImageConvertArticle({
              source_instance_id: sourceInstanceId,
              article_id: selectedArticleId,
            });
      appendWorkLogs(result.logs ?? []);
      setDraft(result);
      setEditTitle(result.title);
      setEditLabels(result.label_names.join(", "));
      setSelectedImageIndex(0);
      setMessage({
        type: "ok",
        text: `OCR 변환이 완료되었습니다. (${result.ocr_image_count}/${result.image_count}개 이미지)`,
      });
    } catch (error) {
      appendWorkLogs(extractErrorLogs(error));
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "OCR 변환에 실패했습니다.",
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
      setMessage({ type: "error", text: "먼저 OCR 변환을 실행하세요." });
      return;
    }
    if (targetInstanceId === "") {
      setMessage({ type: "error", text: "타겟 인스턴스를 선택하세요." });
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
        instance_id: targetInstanceId,
        brand_id: sectionSelection.brandId,
        section_a_id: sectionSelection.sectionAId,
        title: draft.title,
        html_body: draft.html_body,
        label_names: draft.label_names,
      });
      appendWorkLogs(result.logs ?? []);
      setCreatedUrl(result.html_url);
      setMessage({
        type: "ok",
        text: `타겟 인스턴스에 아티클이 생성되었습니다. (ID: ${result.article_id}, 섹션: ${result.section_name})`,
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
    <section className="page ai-ocr-page convert-image-page">
      <header className="page-top">
        <div className="ai-ocr-title-row">
          <h2 className="page-title">이미지 아티클 변환</h2>
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
          소스 인스턴스(A)의 이미지가 포함된 아티클을 선택하면 본문 이미지를 AI-OCR 분석하고, 타겟
          인스턴스(B)에 새 아티클을 생성합니다.
        </p>
      </header>

      {message ? (
        <NoticeBanner
          variant={message.type === "error" ? "error" : "info"}
          message={message.text}
          onDismiss={() => setMessage(null)}
        />
      ) : null}

      <div className="card ai-ocr-config-card convert-image-config-card">
        <div className="ai-ocr-provider-row convert-image-ai-row">
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

        <div className="convert-image-instance-columns">
          <div className="convert-image-instance-panel convert-image-instance-panel-source">
            <h3 className="convert-image-instance-panel-title">소스 인스턴스 (A)</h3>
            <label>
              인스턴스
              <select
                value={sourceInstanceId}
                onChange={(event) => {
                  const value = event.target.value;
                  setSourceInstanceId(value ? Number(value) : "");
                  setSelectedArticleId("");
                  setArticleDetail(null);
                  setDraft(null);
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

            <label className="convert-image-search-label">
              이미지 포함 아티클 검색
              <div className="convert-image-search-row">
                <input
                  type="search"
                  value={articleSearch}
                  placeholder="제목 검색"
                  disabled={sourceInstanceId === ""}
                  onChange={(event) => setArticleSearch(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      void loadArticles();
                    }
                  }}
                />
                <button
                  type="button"
                  className="button-ghost"
                  disabled={sourceInstanceId === "" || articlesLoading}
                  onClick={() => void loadArticles()}
                >
                  <RefreshCw
                    size={16}
                    className={articlesLoading ? "spin-icon" : undefined}
                    aria-hidden="true"
                  />
                  검색
                </button>
              </div>
            </label>

            <label>
              아티클 선택
              <select
                value={selectedArticleId}
                disabled={sourceInstanceId === "" || articlesLoading}
                onChange={(event) => {
                  const value = event.target.value;
                  setSelectedArticleId(value ? Number(value) : "");
                }}
              >
                <option value="">
                  {sourceInstanceId === ""
                    ? "소스 인스턴스를 먼저 선택하세요"
                    : articlesLoading
                      ? "불러오는 중..."
                      : articles.length === 0
                        ? "이미지 포함 아티클 없음"
                        : "아티클 선택"}
                </option>
                {articles.map((article) => (
                  <option key={article.id} value={article.id}>
                    {article.title} ({article.image_count}개 이미지 · {article.section_name})
                  </option>
                ))}
              </select>
            </label>

            {articleDetail ? (
              <p className="convert-image-source-summary">
                <strong>{articleDetail.title}</strong>
                {" · "}
                {articleDetail.section_name}
                {" · "}
                이미지 {articleDetail.images.length}개
                {articleDetail.html_url ? (
                  <>
                    {" · "}
                    <a href={articleDetail.html_url} target="_blank" rel="noopener noreferrer">
                      원본 보기
                    </a>
                  </>
                ) : null}
              </p>
            ) : (
              <p className="muted convert-image-source-summary">변환할 이미지 포함 아티클을 선택하세요.</p>
            )}
          </div>

          <div className="convert-image-instance-panel convert-image-instance-panel-target">
            <h3 className="convert-image-instance-panel-title">타겟 인스턴스 (B)</h3>
            <label>
              인스턴스
              <select
                value={targetInstanceId}
                onChange={(event) => {
                  const value = event.target.value;
                  setTargetInstanceId(value ? Number(value) : "");
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

            <div className="ai-ocr-section-picker-row convert-image-target-section-row">
              <button
                type="button"
                className="button-ghost ai-ocr-picker-button"
                disabled={targetInstanceId === "" || fetchLoading}
                onClick={() => setPickerOpen(true)}
              >
                <FolderOpen size={16} aria-hidden="true" />
                카테고리 · 섹션 선택
              </button>
              {fetchLoading && targetInstanceId !== "" ? (
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
                <p className="muted ai-ocr-section-summary">
                  타겟 인스턴스에 생성할 카테고리·섹션을 선택하세요.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="ai-ocr-workspace">
        <div className="card ai-ocr-upload-card">
          <h3 className="title-with-icon">
            <FileImage size={18} aria-hidden="true" />
            이미지 미리보기
          </h3>

          {imageCount > 1 ? (
            <div className="convert-image-thumb-row">
              {Array.from({ length: imageCount }).map((_, index) => (
                <button
                  key={index}
                  type="button"
                  className={`convert-image-thumb${selectedImageIndex === index ? " is-active" : ""}`}
                  onClick={() => setSelectedImageIndex(index)}
                >
                  이미지 {index + 1}
                </button>
              ))}
            </div>
          ) : null}

          <div className="ai-ocr-upload-media">
            {detailLoading ? (
              <div className="ai-ocr-upload-media-placeholder">
                <Loader2 size={32} className="spin-icon" aria-hidden="true" />
                <p>아티클 이미지를 불러오는 중...</p>
              </div>
            ) : imagePreviewError && !localPreviewUrls[selectedImageIndex] ? (
              <div className="ai-ocr-upload-media-placeholder">
                <FileImage size={40} strokeWidth={1.25} aria-hidden="true" />
                <p>{imagePreviewError}</p>
              </div>
            ) : currentImagePreviewUrl ? (
              <img
                src={currentImagePreviewUrl}
                alt={`아티클 이미지 ${selectedImageIndex + 1}`}
                className="ai-ocr-image-preview"
                onError={() =>
                  setImagePreviewError(
                    "이미지를 표시할 수 없습니다. Zendesk에서 파일이 삭제되었거나 본문 URL이 유효하지 않을 수 있습니다.",
                  )
                }
              />
            ) : (
              <div className="ai-ocr-upload-media-placeholder">
                <FileImage size={40} strokeWidth={1.25} aria-hidden="true" />
                <p>소스 아티클을 선택하면 본문 이미지가 표시됩니다</p>
              </div>
            )}
          </div>

          {selectedBodyImage?.availability === "external_paste" || imagePreviewError ? (
            <label className="convert-image-local-upload">
              로컬 이미지 파일
              <span className="muted convert-image-local-upload-hint">
                다른 Zendesk에서 붙여넣은 이미지는 원본 파일을 직접 지정해야 OCR할 수 있습니다.
              </span>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                onChange={(event) =>
                  handleLocalImageFile(selectedImageIndex, event.target.files?.[0] ?? null)
                }
              />
              {localImageFiles[selectedImageIndex] ? (
                <span className="convert-image-local-upload-name">
                  {localImageFiles[selectedImageIndex].name}
                </span>
              ) : null}
            </label>
          ) : null}

          <button
            type="button"
            className="button-primary"
            disabled={
              sourceInstanceId === "" ||
              selectedArticleId === "" ||
              analyzing ||
              !providerStatus.ready ||
              detailLoading
            }
            onClick={() => void handleAnalyze()}
          >
            {analyzing ? (
              <>
                <Loader2 size={16} className="spin-icon" aria-hidden="true" />
                OCR 변환 중...
              </>
            ) : (
              <>
                <Sparkles size={16} aria-hidden="true" />
                OCR 변환 실행
              </>
            )}
          </button>
        </div>

        <div className="card ai-ocr-preview-card">
          <h3>아티클 미리보기</h3>

          <div className="ai-ocr-preview-pane">
            {!draft ? (
              <div className="ai-ocr-preview-pane-empty">
                <p className="muted">OCR 변환 결과가 여기에 표시됩니다.</p>
              </div>
            ) : (
              <>
                <dl className="ai-ocr-preview-meta">
                  <div>
                    <dt>소스 아티클</dt>
                    <dd>{draft.source_article_title}</dd>
                  </div>
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
                  <div>
                    <dt>OCR 이미지</dt>
                    <dd>
                      {draft.ocr_image_count}/{draft.image_count}개
                    </dd>
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
                disabled={creating || targetInstanceId === "" || !sectionSelection}
                onClick={() => void handleCreateArticle()}
              >
                {creating ? (
                  <>
                    <Loader2 size={16} className="spin-icon" aria-hidden="true" />
                    타겟 Zendesk에 생성 중...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={16} aria-hidden="true" />
                    타겟 아티클 생성
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

      <WorkLogAccordion title="API 작업 로그" entries={workLogs} hideWhenEmpty={!analyzing} />

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
