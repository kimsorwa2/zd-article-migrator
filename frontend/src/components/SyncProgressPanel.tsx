import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import type { FetchSyncProgress } from "../api/client";

interface SyncProgressPanelProps {
  /** 수집 진행 상태 */
  progress: FetchSyncProgress;
  /** 완료·실패 패널 닫기(선택) */
  onDismiss?: () => void;
}

/**
 * Help Center 수집 진행률을 퍼센트 바와 상세 통계·경고·오류로 표시한다.
 */
export default function SyncProgressPanel({ progress, onDismiss }: SyncProgressPanelProps) {
  const percent = Math.max(0, Math.min(100, progress.percent));
  const isRunning = progress.status === "running";
  const isFailed = progress.status === "failed";
  const isCompleted = progress.status === "completed";
  const warnings = progress.warnings ?? [];

  return (
    <div
      className={`sync-progress-panel${isFailed ? " sync-progress-panel-failed" : ""}${isCompleted && warnings.length > 0 ? " sync-progress-panel-warn" : ""}`}
      role="status"
      aria-live="polite"
      aria-busy={isRunning}
    >
      <div className="sync-progress-header">
        {isRunning ? (
          <Loader2 className="loading-panel-spinner" size={22} aria-hidden="true" />
        ) : isFailed ? (
          <AlertCircle size={22} className="sync-progress-icon-failed" aria-hidden="true" />
        ) : (
          <CheckCircle2 size={22} className="sync-progress-icon-done" aria-hidden="true" />
        )}
        <p className="sync-progress-message">{progress.message || "Help Center 수집 중..."}</p>
        {onDismiss && !isRunning ? (
          <button type="button" className="button-ghost sync-progress-dismiss" onClick={onDismiss}>
            닫기
          </button>
        ) : null}
      </div>

      <div className="sync-progress-track" aria-hidden="true">
        <div className="sync-progress-bar" style={{ width: `${percent}%` }} />
      </div>

      <p className="sync-progress-meta muted">
        <strong>{percent}%</strong>
        {progress.brand_total > 0 ? (
          <>
            {" "}
            · 브랜드 {progress.brand_index}/{progress.brand_total}
            {progress.brand_name ? ` (${progress.brand_name})` : ""}
          </>
        ) : null}
        {progress.articles_collected > 0 ? <> · 아티클 {progress.articles_collected.toLocaleString("ko-KR")}건</> : null}
        {progress.article_page > 0 ? <> · API {progress.article_page}페이지</> : null}
        {progress.attachments_total > 0 ? (
          <>
            {" "}
            · 첨부 확인 {progress.attachments_checked.toLocaleString("ko-KR")}/
            {progress.attachments_total.toLocaleString("ko-KR")}
          </>
        ) : null}
      </p>

      {isFailed && progress.error ? (
        <p className="sync-progress-error-text">{progress.error}</p>
      ) : null}

      {warnings.length > 0 ? (
        <details className="sync-progress-warnings" open={isFailed || (isCompleted && warnings.length <= 20)}>
          <summary>
            수집 경고 {warnings.length}건
            {isCompleted ? " (수집은 완료됨)" : ""}
          </summary>
          <ol className="sync-progress-warnings-list">
            {warnings.map((item, index) => (
              <li key={`${item.timestamp}-${index}`}>
                <span className="sync-progress-warnings-time">[{item.timestamp}]</span>
                {item.brand_name ? <span className="sync-progress-warnings-brand">{item.brand_name}</span> : null}
                {item.phase ? <span className="sync-progress-warnings-phase">{item.phase}</span> : null}
                <span className="sync-progress-warnings-msg">{item.message}</span>
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </div>
  );
}
