import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Rocket } from "lucide-react";
import {
  apiClient,
  type DeleteExecuteResponse,
  type DuplicatePolicy,
  type FetchDetailBrand,
  type FetchSyncProgress,
  type Instance,
  type MigrateOverlayResponse,
  type MigrateProgress,
} from "../api/client";
import LoadingPanel from "../components/LoadingPanel";
import MigrateProgressPanel from "../components/MigrateProgressPanel";
import SyncProgressPanel from "../components/SyncProgressPanel";
import SelectableSourceTree from "../components/SelectableSourceTree";
import TargetMigratedTree from "../components/TargetMigratedTree";
import NoticeBanner from "../components/NoticeBanner";
import { useTimedNotice } from "../hooks/useTimedNotice";
import { buildFetchTreeChildMaps, collectAllFetchTreeIds } from "../utils/fetchTreeSelection";
import { isMigrateEligibleInstance, isTargetHelpCenterBrand } from "../utils/instanceUtils";
import { waitForSyncCompletion } from "../utils/syncProgressPoll";

/**
 * 삭제 API 응답을 사용자 메시지로 변환한다.
 */
function formatDeleteResultMessage(response: DeleteExecuteResponse): string {
  const base = `삭제 완료 - 카테고리 ${response.summary.categories}, 섹션 ${response.summary.sections}, 아티클 ${response.summary.articles}`;
  if (response.failed_items.length === 0) {
    return base;
  }
  return `${base} (실패 ${response.failed_items.length}건 — 재시도 가능)`;
}

interface MigratePageProps {
  instances: Instance[];
}

/**
 * 중복 처리 정책 옵션과 사용자용 설명을 정의한다.
 */
const DUPLICATE_POLICY_OPTIONS: Array<{
  value: DuplicatePolicy;
  label: string;
  summary: string;
  description: string;
}> = [
  {
    value: "skip",
    label: "skip — 건너뛰기",
    summary: "이미 옮긴 아티클은 그대로 두고, 없는 아티클만 새로 만듭니다.",
    description:
      "타겟에 같은 아티클이 이전에 마이그레이션된 기록(매핑)이 있으면 해당 아티클은 수정하지 않고 건너뜁니다. 처음 옮기거나, 실수로 같은 항목을 다시 실행해 중복·덮어쓰기를 막고 싶을 때 선택하세요.",
  },
  {
    value: "update",
    label: "update — 내용 갱신",
    summary: "이미 옮긴 아티클은 소스 내용으로 다시 맞춥니다.",
    description:
      "매핑이 있는 아티클은 제목·본문·첨부파일을 소스 기준으로 타겟에 반영합니다. 아직 없는 아티클은 새로 생성합니다. 소스를 수정한 뒤 타겟만 최신화할 때 사용합니다.",
  },
  {
    value: "force",
    label: "force — 강제 갱신",
    summary: "update와 같이 기존 아티클을 소스 내용으로 갱신합니다.",
    description:
      "현재 구현에서는 update와 동일하게, 매핑된 아티클을 소스 내용으로 덮어씁니다. 향후 더 강한 덮어쓰기 규칙이 필요할 때를 대비한 옵션입니다. 일반적으로는 update를 사용하면 됩니다.",
  },
];

function toggleSet(values: number[], id: number, checked: boolean): number[] {
  if (checked) {
    return values.includes(id) ? values : [...values, id];
  }
  return values.filter((value) => value !== id);
}

/**
 * 타겟 Help Center 브랜드 로컬 ID를 결정한다(훅 밖 유틸).
 */
function resolveTargetBrandIdFromState(
  targetHelpCenterBrands: FetchDetailBrand[],
  targetBrandId: number,
): number | null {
  if (targetHelpCenterBrands.length === 0) {
    return null;
  }
  if (targetHelpCenterBrands.length === 1) {
    return targetHelpCenterBrands[0].id;
  }
  if (!targetBrandId) {
    return null;
  }
  return targetBrandId;
}

export default function MigratePage({ instances }: MigratePageProps) {
  const [sourceInstanceId, setSourceInstanceId] = useState(0);
  const [targetInstanceId, setTargetInstanceId] = useState(0);
  const [targetBrandId, setTargetBrandId] = useState(0);
  const [duplicatePolicy, setDuplicatePolicy] = useState<DuplicatePolicy>("skip");
  const [selectedBrandIds, setSelectedBrandIds] = useState<number[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedSectionIds, setSelectedSectionIds] = useState<number[]>([]);
  const [selectedArticleIds, setSelectedArticleIds] = useState<number[]>([]);
  const [sourceBrands, setSourceBrands] = useState<FetchDetailBrand[]>([]);
  const [targetBrands, setTargetBrands] = useState<FetchDetailBrand[]>([]);
  const [migrateOverlay, setMigrateOverlay] = useState<MigrateOverlayResponse | null>(null);
  const [selectedTargetCategoryAIds, setSelectedTargetCategoryAIds] = useState<number[]>([]);
  const [selectedTargetSectionAIds, setSelectedTargetSectionAIds] = useState<number[]>([]);
  const [migrateProgress, setMigrateProgress] = useState<MigrateProgress | null>(null);
  const { message, noticeVariant, setMessage, clearMessage } = useTimedNotice();
  const [isMigrateStarting, setIsMigrateStarting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [autoResyncTarget, setAutoResyncTarget] = useState(false);
  const [targetSyncProgress, setTargetSyncProgress] = useState<FetchSyncProgress | null>(null);
  const [isSourceLoading, setIsSourceLoading] = useState(false);
  const [isTargetLoading, setIsTargetLoading] = useState(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoResyncTargetRef = useRef(autoResyncTarget);

  const migrateEligibleInstances = useMemo(() => instances.filter(isMigrateEligibleInstance), [instances]);

  const targetHelpCenterBrands = useMemo(() => targetBrands.filter(isTargetHelpCenterBrand), [targetBrands]);

  const childMap = useMemo(() => buildFetchTreeChildMaps(sourceBrands), [sourceBrands]);

  const displayTargetBrands = useMemo(() => {
    const resolved = resolveTargetBrandIdFromState(targetHelpCenterBrands, targetBrandId);
    if (!resolved) {
      if (targetHelpCenterBrands.length > 1) {
        return [];
      }
      return targetBrands;
    }
    return targetBrands.filter((brand) => brand.id === resolved);
  }, [targetBrands, targetHelpCenterBrands, targetBrandId]);

  const isMigrateRunning = migrateProgress?.status === "running";
  const isTargetResyncing = targetSyncProgress?.status === "running";

  useEffect(() => {
    autoResyncTargetRef.current = autoResyncTarget;
  }, [autoResyncTarget]);

  useEffect(() => {
    async function loadSourceTree() {
      if (!sourceInstanceId) {
        setSourceBrands([]);
        setSelectedBrandIds([]);
        setSelectedCategoryIds([]);
        setSelectedSectionIds([]);
        setSelectedArticleIds([]);
        return;
      }

      setIsSourceLoading(true);
      setSelectedBrandIds([]);
      setSelectedCategoryIds([]);
      setSelectedSectionIds([]);
      setSelectedArticleIds([]);
      try {
        const response = await apiClient.getFetchDetail(sourceInstanceId);
        setSourceBrands(response.brands);
      } catch (error) {
        setSourceBrands([]);
        setMessage(error instanceof Error ? error.message : "소스 데이터 조회 실패", { variant: "error" });
      } finally {
        setIsSourceLoading(false);
      }
    }

    void loadSourceTree();
  }, [sourceInstanceId]);

  useEffect(() => {
    async function loadTargetTree() {
      if (!targetInstanceId) {
        setTargetBrands([]);
        return;
      }

      setIsTargetLoading(true);
      try {
        const response = await apiClient.getFetchDetail(targetInstanceId);
        setTargetBrands(response.brands);
      } catch (error) {
        setTargetBrands([]);
        setMessage(error instanceof Error ? error.message : "타겟 Help Center 구조 조회 실패", { variant: "error" });
      } finally {
        setIsTargetLoading(false);
      }
    }

    void loadTargetTree();
  }, [targetInstanceId, setMessage]);

  const reloadTargetTree = useCallback(async () => {
    if (!targetInstanceId) {
      return;
    }
    const targetDetail = await apiClient.getFetchDetail(targetInstanceId);
    setTargetBrands(targetDetail.brands);
  }, [targetInstanceId]);

  const reloadOverlay = useCallback(async () => {
    if (!sourceInstanceId || !targetInstanceId) {
      setMigrateOverlay(null);
      return;
    }
    try {
      const overlay = await apiClient.getMigrateOverlay(sourceInstanceId, targetInstanceId);
      setMigrateOverlay(overlay);
    } catch {
      setMigrateOverlay(null);
    }
  }, [sourceInstanceId, targetInstanceId]);

  const runTargetResync = useCallback(
    async (previousMessage: string) => {
      if (!targetInstanceId) {
        return;
      }
      setTargetSyncProgress({
        instance_id: targetInstanceId,
        status: "running",
        percent: 0,
        message: "타겟 Help Center 재수집을 시작합니다...",
        phase: "preparing",
        brand_index: 0,
        brand_total: 0,
        brand_name: null,
        article_page: 0,
        articles_collected: 0,
        attachments_checked: 0,
        attachments_total: 0,
        error: null,
        result: null,
      });
      try {
        await apiClient.syncInstance(targetInstanceId);
        const finalProgress = await waitForSyncCompletion(targetInstanceId, setTargetSyncProgress);
        const processedBrands = finalProgress.result?.processed_brands ?? 0;
        await reloadTargetTree();
        await reloadOverlay();
        setMessage(`${previousMessage} · 타겟 재수집 완료 (브랜드 ${processedBrands}개)`);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "타겟 재수집 실패", { variant: "error" });
      } finally {
        setTargetSyncProgress(null);
      }
    },
    [targetInstanceId, reloadTargetTree, reloadOverlay, setMessage],
  );

  useEffect(() => {
    setSelectedTargetCategoryAIds([]);
    setSelectedTargetSectionAIds([]);
    void reloadOverlay();
  }, [reloadOverlay]);

  useEffect(() => {
    if (!targetInstanceId) {
      setTargetBrandId(0);
      return;
    }
    if (targetHelpCenterBrands.length === 1) {
      setTargetBrandId(targetHelpCenterBrands[0].id);
      return;
    }
    setTargetBrandId(0);
  }, [targetInstanceId, targetHelpCenterBrands]);

  /**
   * 마이그레이션 API에 전달할 타겟 브랜드 ID를 결정한다.
   */
  function resolveTargetBrandId(): number | null {
    return resolveTargetBrandIdFromState(targetHelpCenterBrands, targetBrandId);
  }

  const stopMigratePolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const startMigratePolling = useCallback(() => {
    stopMigratePolling();
    if (!sourceInstanceId || !targetInstanceId) {
      return;
    }

    pollTimerRef.current = setInterval(() => {
      void (async () => {
        try {
          const progress = await apiClient.getMigrateProgress(sourceInstanceId, targetInstanceId);
          setMigrateProgress(progress);
          if (progress.status === "completed") {
            stopMigratePolling();
            const summary = progress.result?.summary;
            const completionMessage = summary
              ? `마이그레이션 완료 - 브랜드 ${summary.brands}, 카테고리 ${summary.categories}, 섹션 ${summary.sections}, 아티클 ${summary.articles}`
              : "마이그레이션이 완료되었습니다.";
            setMessage(completionMessage);
            await reloadOverlay();
            if (autoResyncTargetRef.current) {
              await runTargetResync(completionMessage);
            }
          }
          if (progress.status === "failed") {
            stopMigratePolling();
            setMessage(progress.error ?? "마이그레이션 실패", { variant: "error" });
          }
        } catch (error) {
          stopMigratePolling();
          setMessage(error instanceof Error ? error.message : "진행 상태 조회 실패", { variant: "error" });
        }
      })();
    }, 1500);
  }, [sourceInstanceId, targetInstanceId, reloadOverlay, runTargetResync, setMessage, stopMigratePolling]);

  useEffect(() => {
    if (!sourceInstanceId || !targetInstanceId) {
      setMigrateProgress(null);
      stopMigratePolling();
      return;
    }

    void (async () => {
      try {
        const progress = await apiClient.getMigrateProgress(sourceInstanceId, targetInstanceId);
        setMigrateProgress(progress.status === "idle" ? null : progress);
        if (progress.status === "running") {
          startMigratePolling();
        }
      } catch {
        setMigrateProgress(null);
      }
    })();

    return () => stopMigratePolling();
  }, [sourceInstanceId, targetInstanceId, startMigratePolling, stopMigratePolling]);

  /**
   * 소스 트리의 모든 항목을 선택한다.
   */
  function handleSelectAll() {
    const allIds = collectAllFetchTreeIds(sourceBrands);
    setSelectedBrandIds(allIds.brandIds);
    setSelectedCategoryIds(allIds.categoryIds);
    setSelectedSectionIds(allIds.sectionIds);
    setSelectedArticleIds(allIds.articleIds);
  }

  /**
   * 소스 트리의 모든 선택을 해제한다.
   */
  function handleDeselectAll() {
    setSelectedBrandIds([]);
    setSelectedCategoryIds([]);
    setSelectedSectionIds([]);
    setSelectedArticleIds([]);
  }

  async function handleMigrate() {
    if (!sourceInstanceId || !targetInstanceId) {
      setMessage("소스/타겟 인스턴스를 모두 선택하세요.", { variant: "error" });
      return;
    }
    if (sourceInstanceId === targetInstanceId) {
      setMessage("소스와 타겟은 서로 다른 인스턴스를 선택하세요.", { variant: "error" });
      return;
    }

    const resolvedTargetBrandId = resolveTargetBrandId();
    if (resolvedTargetBrandId === null) {
      setMessage(
        targetHelpCenterBrands.length > 1
          ? "마이그레이션할 타겟 브랜드를 선택하세요."
          : "타겟 Help Center 브랜드가 없습니다. 인스턴스 메뉴에서 Help Center 수집을 실행하세요.",
        { variant: "error" },
      );
      return;
    }

    setIsMigrateStarting(true);
    setMessage("");
    try {
      await apiClient.migrateExecute({
        source_instance_id: sourceInstanceId,
        target_instance_id: targetInstanceId,
        target_brand_id: resolvedTargetBrandId,
        duplicate_policy: duplicatePolicy,
        brand_ids: selectedBrandIds,
        category_ids: selectedCategoryIds,
        section_ids: selectedSectionIds,
        article_ids: selectedArticleIds,
      });
      setMigrateProgress({
        source_instance_id: sourceInstanceId,
        target_instance_id: targetInstanceId,
        status: "running",
        percent: 0,
        message: "마이그레이션을 시작합니다.",
        phase: "preparing",
        current_step: 0,
        total_steps: 1,
        error: null,
        result: null,
      });
      startMigratePolling();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "마이그레이션 실패", { variant: "error" });
    } finally {
      setIsMigrateStarting(false);
    }
  }

  async function runTargetDelete(payload: {
    target_category_a_ids?: number[];
    target_section_a_ids?: number[];
    target_article_a_ids?: number[];
  }) {
    if (!sourceInstanceId || !targetInstanceId) {
      setMessage("소스/타겟 인스턴스를 모두 선택하세요.", { variant: "error" });
      return;
    }

    const resolvedTargetBrandId = resolveTargetBrandId();
    if (resolvedTargetBrandId === null) {
      setMessage("타겟 브랜드를 선택하세요.", { variant: "error" });
      return;
    }

    setIsDeleting(true);
    setMessage("");
    try {
      const response = await apiClient.deleteExecute({
        source_instance_id: sourceInstanceId,
        target_instance_id: targetInstanceId,
        target_brand_id: resolvedTargetBrandId,
        target_category_a_ids: payload.target_category_a_ids ?? [],
        target_section_a_ids: payload.target_section_a_ids ?? [],
        target_article_a_ids: payload.target_article_a_ids ?? [],
      });
      setMessage(formatDeleteResultMessage(response));
      setSelectedTargetCategoryAIds([]);
      setSelectedTargetSectionAIds([]);
      await reloadOverlay();
      await reloadTargetTree();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "삭제 처리 실패", { variant: "error" });
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleDeleteRetry(mappingIds?: number[]) {
    if (!sourceInstanceId || !targetInstanceId) {
      setMessage("소스/타겟 인스턴스를 모두 선택하세요.", { variant: "error" });
      return;
    }

    const resolvedTargetBrandId = resolveTargetBrandId();
    if (resolvedTargetBrandId === null) {
      setMessage("타겟 브랜드를 선택하세요.", { variant: "error" });
      return;
    }

    setIsDeleting(true);
    setMessage("");
    try {
      const response = await apiClient.deleteRetry({
        source_instance_id: sourceInstanceId,
        target_instance_id: targetInstanceId,
        target_brand_id: resolvedTargetBrandId,
        mapping_ids: mappingIds,
      });
      setMessage(formatDeleteResultMessage(response));
      await reloadOverlay();
      await reloadTargetTree();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "삭제 재시도 실패", { variant: "error" });
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleBulkDeleteSelected() {
    if (selectedTargetCategoryAIds.length === 0 && selectedTargetSectionAIds.length === 0) {
      setMessage("삭제할 카테고리 또는 섹션을 선택하세요.", { variant: "error" });
      return;
    }
    await runTargetDelete({
      target_category_a_ids: selectedTargetCategoryAIds,
      target_section_a_ids: selectedTargetSectionAIds,
    });
  }

  const selectedTarget = migrateEligibleInstances.find((instance) => instance.id === targetInstanceId);
  const needsTargetBrandSelection = targetHelpCenterBrands.length > 1;
  const selectedDuplicatePolicy =
    DUPLICATE_POLICY_OPTIONS.find((option) => option.value === duplicatePolicy) ?? DUPLICATE_POLICY_OPTIONS[0];

  return (
    <section className="page">
      <h2 className="title-with-icon">
        <Rocket size={20} aria-hidden="true" />
        마이그레이션
      </h2>

      {message ? <NoticeBanner message={message} variant={noticeVariant} onDismiss={clearMessage} /> : null}

      {migrateProgress && (migrateProgress.status === "running" || migrateProgress.status === "failed") ? (
        <MigrateProgressPanel progress={migrateProgress} />
      ) : null}

      {migrateEligibleInstances.length === 0 ? (
        <p className="muted migrate-panel-placeholder">
          마이그레이션할 수 있는 인스턴스가 없습니다. 인스턴스 메뉴에서 Help Center 수집을 완료한 뒤 다시 시도하세요.
        </p>
      ) : null}

      <div className="migrate-split">
        <div className="migrate-panel">
          <h3 className="migrate-panel-title">소스 인스턴스</h3>
          <label className="migrate-panel-field">
            인스턴스
            <select
              value={sourceInstanceId}
              onChange={(event) => {
                setSourceInstanceId(Number(event.target.value));
                setMessage("");
              }}
            >
              <option value={0}>선택하세요 (수집 완료된 인스턴스만)</option>
              {migrateEligibleInstances
                .filter((instance) => instance.id !== targetInstanceId)
                .map((instance) => (
                  <option key={instance.id} value={instance.id}>
                    {instance.name} ({instance.subdomain})
                  </option>
                ))}
            </select>
          </label>

          {sourceInstanceId ? (
            <>
              <div className="migrate-source-controls">
                <div className="migrate-policy-block">
                  <label className="migrate-panel-field" htmlFor="duplicate-policy-select">
                    중복 처리 정책
                    <select
                      id="duplicate-policy-select"
                      value={duplicatePolicy}
                      onChange={(event) => setDuplicatePolicy(event.target.value as DuplicatePolicy)}
                    >
                      {DUPLICATE_POLICY_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p className="migrate-policy-summary">{selectedDuplicatePolicy.summary}</p>
                  <p className="migrate-policy-description">{selectedDuplicatePolicy.description}</p>
                </div>
              </div>
              <p className="muted migrate-selection-summary">
                선택됨 - 브랜드 {selectedBrandIds.length} / 카테고리 {selectedCategoryIds.length} / 섹션 {selectedSectionIds.length} / 아티클{" "}
                {selectedArticleIds.length}
              </p>
              <div className="migrate-selection-toolbar">
                <button type="button" className="button-ghost" onClick={handleSelectAll} disabled={sourceBrands.length === 0}>
                  전체 선택
                </button>
                <button type="button" className="button-ghost" onClick={handleDeselectAll} disabled={sourceBrands.length === 0}>
                  전체 해제
                </button>
              </div>
              {isSourceLoading ? <LoadingPanel message="소스 Help Center 구조를 불러오는 중..." /> : null}
              {!isSourceLoading ? (
                <SelectableSourceTree
                  brands={sourceBrands}
                  selectedBrandIds={selectedBrandIds}
                  selectedCategoryIds={selectedCategoryIds}
                  selectedSectionIds={selectedSectionIds}
                  selectedArticleIds={selectedArticleIds}
                  onToggleBrand={(id, checked) => {
                    setSelectedBrandIds((prev) => toggleSet(prev, id, checked));
                    const categoryIds = childMap.brandToCategories.get(id) ?? [];
                    setSelectedCategoryIds((prev) =>
                      checked ? Array.from(new Set([...prev, ...categoryIds])) : prev.filter((value) => !categoryIds.includes(value)),
                    );

                    const sectionIds = categoryIds.flatMap((categoryId) => childMap.categoryToSections.get(categoryId) ?? []);
                    setSelectedSectionIds((prev) =>
                      checked ? Array.from(new Set([...prev, ...sectionIds])) : prev.filter((value) => !sectionIds.includes(value)),
                    );

                    const articleIds = sectionIds.flatMap((sectionId) => childMap.sectionToArticles.get(sectionId) ?? []);
                    setSelectedArticleIds((prev) =>
                      checked ? Array.from(new Set([...prev, ...articleIds])) : prev.filter((value) => !articleIds.includes(value)),
                    );
                  }}
                  onToggleCategory={(id, checked) => {
                    setSelectedCategoryIds((prev) => toggleSet(prev, id, checked));
                    const sectionIds = childMap.categoryToSections.get(id) ?? [];
                    setSelectedSectionIds((prev) =>
                      checked ? Array.from(new Set([...prev, ...sectionIds])) : prev.filter((value) => !sectionIds.includes(value)),
                    );

                    const articleIds = sectionIds.flatMap((sectionId) => childMap.sectionToArticles.get(sectionId) ?? []);
                    setSelectedArticleIds((prev) =>
                      checked ? Array.from(new Set([...prev, ...articleIds])) : prev.filter((value) => !articleIds.includes(value)),
                    );
                  }}
                  onToggleSection={(id, checked) => {
                    setSelectedSectionIds((prev) => toggleSet(prev, id, checked));
                    const articleIds = childMap.sectionToArticles.get(id) ?? [];
                    setSelectedArticleIds((prev) =>
                      checked ? Array.from(new Set([...prev, ...articleIds])) : prev.filter((value) => !articleIds.includes(value)),
                    );
                  }}
                  onToggleArticle={(id, checked) => setSelectedArticleIds((prev) => toggleSet(prev, id, checked))}
                />
              ) : null}
            </>
          ) : (
            <p className="muted">소스 인스턴스를 선택하세요. 인스턴스 메뉴에서 Help Center 수집이 필요합니다.</p>
          )}
        </div>

        <div className="migrate-panel">
          <h3 className="migrate-panel-title">타겟 인스턴스</h3>
          <label className="migrate-panel-field">
            인스턴스
            <select
              value={targetInstanceId}
              onChange={(event) => {
                setTargetInstanceId(Number(event.target.value));
                setMessage("");
              }}
            >
              <option value={0}>선택하세요 (수집 완료된 인스턴스만)</option>
              {migrateEligibleInstances
                .filter((instance) => instance.id !== sourceInstanceId)
                .map((instance) => (
                  <option key={instance.id} value={instance.id}>
                    {instance.name} ({instance.subdomain})
                  </option>
                ))}
            </select>
          </label>

          {targetInstanceId && !isTargetLoading && targetHelpCenterBrands.length > 1 ? (
            <label className="migrate-panel-field">
              마이그레이션 대상 브랜드
              <select
                value={targetBrandId}
                onChange={(event) => {
                  setTargetBrandId(Number(event.target.value));
                  setMessage("");
                }}
              >
                <option value={0}>타겟 브랜드를 선택하세요</option>
                {targetHelpCenterBrands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name} ({brand.subdomain})
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {targetInstanceId && !isTargetLoading && sourceInstanceId ? (
            <div className="migrate-target-run-block">
              <label className="migrate-auto-resync-label">
                <input
                  type="checkbox"
                  checked={autoResyncTarget}
                  disabled={isMigrateRunning || isTargetResyncing}
                  onChange={(event) => setAutoResyncTarget(event.target.checked)}
                />
                마이그레이션 완료 후 타겟 Help Center 자동 재수집
              </label>
              <div className="migrate-target-run-row">
                <button
                  type="button"
                  className="migrate-primary-action"
                  disabled={
                    isMigrateStarting ||
                    isMigrateRunning ||
                    isDeleting ||
                    isTargetResyncing ||
                    (needsTargetBrandSelection && !targetBrandId) ||
                    targetHelpCenterBrands.length === 0
                  }
                  onClick={() => void handleMigrate()}
                >
                  {isMigrateRunning || isMigrateStarting ? "마이그레이션 진행 중..." : "마이그레이션 실행"}
                </button>
              </div>
            </div>
          ) : null}

          {targetSyncProgress ? <SyncProgressPanel progress={targetSyncProgress} /> : null}

          {targetInstanceId ? (
            <>
              {isTargetLoading ? <LoadingPanel message="타겟 Help Center 구조를 불러오는 중..." /> : null}
              {!isTargetLoading && displayTargetBrands.length > 0 ? (
                <TargetMigratedTree
                  title="타겟 Help Center 구조 (마이그레이션 생성 항목)"
                  brands={displayTargetBrands}
                  overlay={migrateOverlay}
                  selectedCategoryAIds={selectedTargetCategoryAIds}
                  selectedSectionAIds={selectedTargetSectionAIds}
                  isDeleting={isDeleting}
                  isMigrateRunning={isMigrateRunning}
                  onBulkDeleteSelected={() => void handleBulkDeleteSelected()}
                  onToggleCategory={(aId, checked) => setSelectedTargetCategoryAIds((prev) => toggleSet(prev, aId, checked))}
                  onToggleSection={(aId, checked) => setSelectedTargetSectionAIds((prev) => toggleSet(prev, aId, checked))}
                  onDeleteCategory={(aId) => void runTargetDelete({ target_category_a_ids: [aId] })}
                  onDeleteSection={(aId) => void runTargetDelete({ target_section_a_ids: [aId] })}
                  onDeleteArticle={(aId) => void runTargetDelete({ target_article_a_ids: [aId] })}
                  onRetryDeleteAll={() => void handleDeleteRetry()}
                  onRetryDeleteMapping={(mappingId) => void handleDeleteRetry([mappingId])}
                />
              ) : null}
              {!isTargetLoading && targetBrands.length === 0 ? (
                <p className="muted migrate-panel-placeholder">
                  수집된 데이터가 없습니다. 인스턴스 메뉴에서 {selectedTarget?.name ?? "타겟"} 인스턴스의 Help Center 수집을 실행하세요.
                </p>
              ) : null}
            </>
          ) : (
            <p className="muted migrate-panel-placeholder">타겟 인스턴스를 선택하세요.</p>
          )}
        </div>
      </div>
    </section>
  );
}
