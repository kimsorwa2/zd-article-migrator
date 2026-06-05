import { useCallback, useEffect, useState } from "react";
import { CirclePlus, Database, FolderSync, Pencil, Trash2, X } from "lucide-react";
import { apiClient, type FetchDetailResponse, type FetchSyncProgress, type Instance } from "../api/client";
import FetchDataTree from "../components/FetchDataTree";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import SyncProgressPanel from "../components/SyncProgressPanel";
import InstanceForm, { type InstanceOAuthFormValues } from "../components/InstanceForm";
import StatusBadge from "../components/StatusBadge";
import { useTimedNotice } from "../hooks/useTimedNotice";

function parseSubdomain(input: string): string {
  return input.replace(".zendesk.com", "").trim();
}

/**
 * ISO 날짜 문자열을 로컬 표시 형식으로 변환한다.
 * @param value ISO 날짜 문자열 또는 null
 */
function formatFetchedAt(value: string | null): string {
  if (!value) {
    return "아직 수집 이력 없음";
  }
  return new Date(value).toLocaleString("ko-KR");
}

export default function InstancesPage() {
  const [instances, setInstances] = useState<Instance[]>([]);
  const [selectedInstanceId, setSelectedInstanceId] = useState<number>(0);
  const [detail, setDetail] = useState<FetchDetailResponse | null>(null);
  const { message, noticeVariant, setMessage, clearMessage } = useTimedNotice();
  const [formError, setFormError] = useState("");
  const [editFormError, setEditFormError] = useState("");
  const [editingInstance, setEditingInstance] = useState<Instance | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  /** 단건 브랜드 수집 시 대상 brand.id (전체 수집이면 null) */
  const [syncingBrandId, setSyncingBrandId] = useState<number | null>(null);
  const [syncProgress, setSyncProgress] = useState<FetchSyncProgress | null>(null);

  const SYNC_POLL_INTERVAL_MS = 800;
  const SYNC_POLL_MAX_IDLE_ROUNDS = 15;
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [deletingInstanceId, setDeletingInstanceId] = useState<number | null>(null);

  const selectedInstance = instances.find((instance) => instance.id === selectedInstanceId) ?? null;

  async function loadInstances() {
    setIsLoading(true);
    try {
      const data = await apiClient.listInstances();
      setInstances(data);
      // 미선택·삭제된 선택 상태면 목록 첫 항목을 자동 선택한다.
      setSelectedInstanceId((current) => {
        if (data.length === 0) {
          return 0;
        }
        const stillExists = data.some((instance) => instance.id === current);
        if (current === 0 || !stillExists) {
          return data[0].id;
        }
        return current;
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "인스턴스 조회 실패", { variant: "error" });
    } finally {
      setIsLoading(false);
    }
  }

  const loadDetail = useCallback(
    async (instanceId: number) => {
      if (!instanceId) {
        setDetail(null);
        return;
      }

      setIsDetailLoading(true);
      try {
        const payload = await apiClient.getFetchDetail(instanceId);
        setDetail(payload);
      } catch (error) {
        setDetail(null);
        setMessage(error instanceof Error ? error.message : "Help Center 구조 조회 실패", { variant: "error" });
      } finally {
        setIsDetailLoading(false);
      }
    },
    [setMessage],
  );

  useEffect(() => {
    void loadInstances();
  }, []);

  useEffect(() => {
    function handleInstancesRefresh() {
      void loadInstances();
    }
    window.addEventListener("zd:instances-refresh", handleInstancesRefresh);
    return () => window.removeEventListener("zd:instances-refresh", handleInstancesRefresh);
  }, []);

  useEffect(() => {
    void loadDetail(selectedInstanceId);
  }, [selectedInstanceId, loadDetail]);

  /** 다른 인스턴스를 선택하면 이전 인스턴스의 수집 진행·실패 패널을 숨긴다. */
  useEffect(() => {
    setSyncProgress((current) => {
      if (!current || current.instance_id === selectedInstanceId) {
        return current;
      }
      return null;
    });
  }, [selectedInstanceId]);

  /**
   * Client Credentials로 Zendesk OAuth 토큰을 발급하고 인스턴스를 생성·갱신한다.
   */
  async function handleConnectOAuth(payload: InstanceOAuthFormValues, options?: { instanceId?: number }) {
    const normalized = parseSubdomain(payload.subdomain);
    if (!normalized) {
      throw new Error("서브도메인을 입력하세요.");
    }
    await apiClient.connectOAuth({
      subdomain: normalized,
      name: payload.name,
      oauth_client_id: payload.oauth_client_id,
      oauth_client_secret: payload.oauth_client_secret,
      oauth_scopes: payload.oauth_scopes || undefined,
      instance_id: options?.instanceId,
    });
  }

  async function handleConnectOAuthForCreate(payload: InstanceOAuthFormValues) {
    try {
      await handleConnectOAuth(payload);
      setFormError("");
      setShowCreateForm(false);
      await loadInstances();
      setMessage("Zendesk OAuth 연결이 완료되었습니다.", { variant: "success" });
      window.dispatchEvent(new CustomEvent("zd:instances-refresh"));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "OAuth 연결 실패";
      setFormError(errorMessage);
      setMessage(errorMessage, { variant: "error" });
      throw error;
    }
  }

  /**
   * 인스턴스 메타·연결 계정·OAuth 클라이언트 설정을 저장한다(OAuth 재연결 없음).
   */
  /**
   * 수정 폼 값을 저장한 뒤 Client Credentials로 OAuth 토큰을 재발급한다.
   */
  async function handleSaveAndReconnect(instance: Instance, payload: InstanceOAuthFormValues) {
    try {
      await apiClient.updateInstance(instance.id, {
        name: payload.name,
        email: payload.email,
        oauth_client_id: payload.oauth_client_id,
        oauth_client_secret: payload.oauth_client_secret || undefined,
        oauth_scopes: payload.oauth_scopes,
      });
      await handleConnectOAuth(payload, { instanceId: instance.id });
      closeEditModal();
      await loadInstances();
      setMessage("인스턴스 저장 및 Zendesk OAuth 연결이 완료되었습니다.", { variant: "success" });
      setEditFormError("");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "저장·Zendesk 연결 실패";
      setEditFormError(errorMessage);
      setMessage(errorMessage, { variant: "error" });
      throw error;
    }
  }

  /**
   * 수집 완료까지 진행률 API를 폴링한다.
   * @param instanceId 수집 대상 인스턴스 ID
   */
  async function waitForSyncCompletion(instanceId: number): Promise<FetchSyncProgress> {
    let idleRounds = 0;

    while (true) {
      const progress = await apiClient.getSyncProgress(instanceId);
      setSyncProgress(progress);

      if (progress.status === "completed") {
        return progress;
      }
      if (progress.status === "failed") {
        throw new Error(progress.error ?? "Help Center 수집 실패");
      }
      if (progress.status === "running") {
        idleRounds = 0;
      } else if (progress.status === "idle") {
        idleRounds += 1;
        if (idleRounds > SYNC_POLL_MAX_IDLE_ROUNDS) {
          throw new Error("수집 작업 상태를 확인할 수 없습니다. 잠시 후 다시 시도하세요.");
        }
      }

      await new Promise((resolve) => setTimeout(resolve, SYNC_POLL_INTERVAL_MS));
    }
  }

  /**
   * Help Center 수집을 시작하고 완료까지 폴링한다.
   * @param brandId 지정 시 해당 브랜드만 수집, 생략 시 선택된 전체 브랜드 수집
   */
  async function runInstanceSync(brandId?: number) {
    const syncingInstanceId = selectedInstanceId;
    if (!syncingInstanceId) {
      setMessage("인스턴스를 먼저 선택하세요.", { variant: "error" });
      return;
    }

    const brandLabel =
      brandId !== undefined ? (detail?.brands.find((brand) => brand.id === brandId)?.name ?? "브랜드") : null;

    setSyncingBrandId(brandId ?? null);
    setSyncProgress({
      instance_id: syncingInstanceId,
      status: "running",
      percent: 0,
      message: brandLabel ? `「${brandLabel}」 수집을 시작합니다...` : "전체 브랜드 수집을 시작합니다...",
      phase: "preparing",
      brand_index: 0,
      brand_total: 0,
      brand_name: brandLabel,
      article_page: 0,
      articles_collected: 0,
      attachments_checked: 0,
      attachments_total: 0,
      error: null,
      result: null,
      warnings: [],
    });
    setIsSyncing(true);
    try {
      if (brandId !== undefined) {
        await apiClient.syncInstanceBrand(syncingInstanceId, brandId);
      } else {
        await apiClient.syncInstance(syncingInstanceId);
      }
      const finalProgress = await waitForSyncCompletion(syncingInstanceId);
      setSyncProgress(finalProgress);
      const processedBrands = finalProgress.result?.processed_brands ?? 0;
      const warningCount = finalProgress.warnings?.length ?? 0;
      if (brandLabel) {
        setMessage(
          warningCount > 0
            ? `「${brandLabel}」 수집 완료 (경고 ${warningCount}건)`
            : `「${brandLabel}」 수집 완료`,
        );
      } else {
        setMessage(
          warningCount > 0
            ? `전체 브랜드 수집 완료 (${processedBrands}개, 경고 ${warningCount}건)`
            : `전체 브랜드 수집 완료 (브랜드 ${processedBrands}개 처리)`,
        );
      }
      await loadInstances();
      if (selectedInstanceId === syncingInstanceId) {
        await loadDetail(syncingInstanceId);
      }
    } catch (error) {
      try {
        const failedProgress = await apiClient.getSyncProgress(syncingInstanceId);
        setSyncProgress(failedProgress);
      } catch {
        // 폴링 실패 시 기존 진행 상태 유지
      }
    } finally {
      setIsSyncing(false);
      setSyncingBrandId(null);
    }
  }

  async function handleSync() {
    await runInstanceSync();
  }

  async function handleSyncBrand(brandId: number) {
    await runInstanceSync(brandId);
  }

  async function handleToggleActive(instance: Instance) {
    try {
      await apiClient.setActive(instance.id, !instance.is_active);
      await loadInstances();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "상태 변경 실패", { variant: "error" });
    }
  }

  function closeEditModal() {
    setEditFormError("");
    setEditingInstance(null);
  }

  async function handleTestConnection(instanceId: number) {
    try {
      const result = await apiClient.testConnection(instanceId);
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "연결 테스트 실패", { variant: "error" });
    }
  }

  /**
   * 인스턴스와 DB에 저장된 수집·매핑 데이터를 삭제한다.
   * @param instance 삭제 대상 인스턴스
   */
  async function handleDeleteInstance(instance: Instance) {
    const confirmed = window.confirm(
      `「${instance.name}」 인스턴스를 삭제할까요?\n\n` +
        "브랜드·카테고리·섹션·아티클·마이그레이션 매핑 등 연관 데이터가 DB에서 모두 삭제됩니다.\n" +
        "Zendesk 계정 자체는 삭제되지 않습니다.",
    );
    if (!confirmed) {
      return;
    }

    setDeletingInstanceId(instance.id);
    try {
      await apiClient.deleteInstance(instance.id);
      setMessage(`인스턴스 「${instance.name}」 삭제 완료`);
      if (selectedInstanceId === instance.id) {
        setSyncError("");
        setSyncProgress(null);
        setIsSyncing(false);
      }
      if (editingInstance?.id === instance.id) {
        setEditingInstance(null);
      }
      await loadInstances();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "인스턴스 삭제 실패", { variant: "error" });
    } finally {
      setDeletingInstanceId(null);
    }
  }

  return (
    <section className="page page-instances">
      <header className="page-top">
        <h2 className="page-title">
          <Database size={22} aria-hidden="true" />
          인스턴스 관리
        </h2>
        <p className="page-lead">
          Zendesk OAuth(Client Credentials)로 계정을 연결하고 Help Center 데이터를 수집합니다. 마이그레이션 시 등록된 인스턴스 중에서 소스와 타겟을 선택합니다.
        </p>
      </header>
      {message ? <NoticeBanner message={message} variant={noticeVariant} onDismiss={clearMessage} /> : null}

      <div className="instances-split">
        <div className="instances-panel instances-panel-list">
          <div className="card-header-row">
            <h3 className="migrate-panel-title">인스턴스 리스트</h3>
            <button
              type="button"
              className="icon-button"
              onClick={() => {
                setFormError("");
                setShowCreateForm(true);
              }}
            >
              <CirclePlus size={16} aria-hidden="true" />
              추가
            </button>
          </div>
          <div className="instances-list-body">
            {isLoading ? <LoadingPanel message="인스턴스 리스트를 불러오는 중..." /> : null}
            {!isLoading && instances.length === 0 ? <p className="muted">등록된 인스턴스가 없습니다.</p> : null}
            <div className="instance-list">
              {instances.map((instance) => {
                const isSelected = selectedInstanceId === instance.id;
                return (
                <div
                  key={instance.id}
                  className={`instance-list-row${isSelected ? " is-selected" : ""}`}
                >
                  <div
                    className="instance-list-row-main instance-list-row-select"
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    aria-label={`${instance.name} 선택`}
                    onClick={() => setSelectedInstanceId(instance.id)}
                    onKeyDown={(event) => {
                      if (event.key !== "Enter" && event.key !== " ") {
                        return;
                      }
                      event.preventDefault();
                      setSelectedInstanceId(instance.id);
                    }}
                  >
                    <div className="instance-list-row-title">
                      <strong>{instance.name}</strong>
                      <StatusBadge active={instance.is_active} />
                    </div>
                    <p className="muted">{instance.subdomain}</p>
                    <p className="muted instance-list-meta">
                      마지막 수집: {formatFetchedAt(instance.last_fetched_at)}
                    </p>
                  </div>
                  <div className="instance-list-row-actions">
                    <div className="instance-list-row-actions-group">
                      <button
                        type="button"
                        onClick={() => {
                          setEditFormError("");
                          setEditingInstance(instance);
                        }}
                      >
                        <Pencil size={14} aria-hidden="true" /> 편집
                      </button>
                      <button type="button" onClick={() => void handleTestConnection(instance.id)}>
                        연결 테스트
                      </button>
                      <button type="button" onClick={() => void handleToggleActive(instance)}>
                        {instance.is_active ? "비활성화" : "활성화"}
                      </button>
                    </div>
                    <button
                      type="button"
                      className="instance-list-delete-btn"
                      title="인스턴스 삭제"
                      aria-label={`${instance.name} 삭제`}
                      disabled={
                        deletingInstanceId === instance.id ||
                        (isSyncing && selectedInstanceId === instance.id)
                      }
                      onClick={() => void handleDeleteInstance(instance)}
                    >
                      <Trash2 size={16} aria-hidden="true" />
                    </button>
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="instances-panel instances-panel-detail">
          {selectedInstance ? (
            <div className="instance-detail-card">
              <div className="instance-detail-header">
                <div>
                  <h3 className="migrate-panel-title">{selectedInstance.name}</h3>
                  <p className="muted">{selectedInstance.subdomain}</p>
                  <p className="muted">마지막 수집: {formatFetchedAt(selectedInstance.last_fetched_at)}</p>
                </div>
                <button
                  type="button"
                  className="migrate-primary-action"
                  disabled={isSyncing}
                  title="선택된 모든 브랜드를 순차 수집합니다"
                  onClick={() => void handleSync()}
                >
                  <FolderSync size={16} aria-hidden="true" />
                  {isSyncing && syncingBrandId === null ? "수집 중..." : "전체 브랜드 수집"}
                </button>
              </div>

              {syncProgress && syncProgress.instance_id === selectedInstanceId ? (
                <SyncProgressPanel
                  progress={syncProgress}
                  onDismiss={() => setSyncProgress(null)}
                />
              ) : null}

              {isDetailLoading && !isSyncing ? <LoadingPanel message="Help Center 구조를 불러오는 중..." /> : null}
              {!isDetailLoading && detail ? (
                <>
                  <p className="muted">
                    브랜드 {detail.summary.total_brands} · 카테고리 {detail.summary.total_categories} · 섹션 {detail.summary.total_sections} · 아티클{" "}
                    {detail.summary.total_articles}
                  </p>
                  <FetchDataTree
                    title="Help Center 구조"
                    brands={detail.brands}
                    onSyncBrand={(brandId) => void handleSyncBrand(brandId)}
                    syncingBrandId={syncingBrandId}
                    syncDisabled={isSyncing}
                  />
                </>
              ) : null}
              {!isDetailLoading && !detail?.brands.length ? (
                <p className="muted migrate-panel-placeholder">수집된 데이터가 없습니다. Help Center 수집을 실행하세요.</p>
              ) : null}
            </div>
          ) : (
            <p className="muted migrate-panel-placeholder">왼쪽에서 인스턴스를 선택하면 Help Center 구조가 표시됩니다.</p>
          )}
        </div>
      </div>

      {showCreateForm ? (
        <div
          className="modal-overlay"
          onClick={() => {
            setFormError("");
            setShowCreateForm(false);
          }}
        >
          <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3 className="title-with-icon">
                <CirclePlus size={18} aria-hidden="true" />
                인스턴스 추가
              </h3>
              <button
                type="button"
                className="icon-button"
                onClick={() => {
                  setFormError("");
                  setShowCreateForm(false);
                }}
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
            <div className="modal-body">
              <InstanceForm
                submitError={formError}
                oauthLabel="Zendesk 연결하고 인스턴스 추가"
                onOAuthConnect={handleConnectOAuthForCreate}
              />
            </div>
          </div>
        </div>
      ) : null}

      {editingInstance ? (
        <div className="modal-overlay" onClick={closeEditModal}>
          <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3 className="title-with-icon">
                <Pencil size={18} aria-hidden="true" />
                인스턴스 정보 수정
              </h3>
              <button type="button" className="icon-button" onClick={closeEditModal}>
                <X size={16} aria-hidden="true" />
              </button>
            </div>
            <div className="modal-body">
              <InstanceForm
                submitError={editFormError}
                oauthLabel="저장하고 Zendesk 연결"
                subdomainDisabled
                secretOptional
                emailEditable
                initialValues={{
                  name: editingInstance.name,
                  subdomain: editingInstance.subdomain,
                  email: editingInstance.email,
                  oauth_client_id: editingInstance.oauth_client_id,
                  oauth_scopes: editingInstance.oauth_scopes || "read write",
                }}
                onOAuthConnect={async (payload) => {
                  await handleSaveAndReconnect(editingInstance, payload);
                }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
