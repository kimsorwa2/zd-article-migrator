import { Loader2 } from "lucide-react";
import type { FetchSyncProgress } from "../api/client";

interface SyncProgressPanelProps {
  /** 수집 진행 상태 */
  progress: FetchSyncProgress;
}

/**
 * Help Center 수집 진행률을 퍼센트 바와 상세 통계로 표시한다.
 * @param progress 백엔드 폴링으로 받은 진행 상태
 */
export default function SyncProgressPanel({ progress }: SyncProgressPanelProps) {
  const percent = Math.max(0, Math.min(100, progress.percent));

  return (
    <div className="sync-progress-panel" role="status" aria-live="polite" aria-busy={progress.status === "running"}>
      <div className="sync-progress-header">
        <Loader2 className="loading-panel-spinner" size={22} aria-hidden="true" />
        <p className="sync-progress-message">{progress.message || "Help Center 수집 중..."}</p>
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
            · 첨부 확인 {progress.attachments_checked.toLocaleString("ko-KR")}/{progress.attachments_total.toLocaleString("ko-KR")}
          </>
        ) : null}
      </p>
    </div>
  );
}
