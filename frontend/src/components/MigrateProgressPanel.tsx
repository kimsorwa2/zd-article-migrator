import { Loader2 } from "lucide-react";
import type { MigrateProgress } from "../api/client";
import MigrateProgressLogAccordion from "./MigrateProgressLogAccordion";

interface MigrateProgressPanelProps {
  /** 마이그레이션 진행 상태 */
  progress: MigrateProgress;
}

/**
 * 마이그레이션 진행률을 퍼센트 바와 단계 정보로 표시한다.
 * @param progress 백엔드 폴링으로 받은 진행 상태
 */
export default function MigrateProgressPanel({ progress }: MigrateProgressPanelProps) {
  const percent = Math.max(0, Math.min(100, progress.percent));

  return (
    <div className="sync-progress-panel migrate-progress-panel" role="status" aria-live="polite" aria-busy={progress.status === "running"}>
      <div className="sync-progress-header">
        {progress.status === "running" ? (
          <Loader2 className="loading-panel-spinner" size={22} aria-hidden="true" />
        ) : null}
        <p
          className={
            progress.status === "failed"
              ? "sync-progress-message migrate-progress-message-failed"
              : "sync-progress-message"
          }
        >
          {progress.message || "마이그레이션 진행 중..."}
        </p>
      </div>
      <div className="sync-progress-track" aria-hidden="true">
        <div className="sync-progress-bar" style={{ width: `${percent}%` }} />
      </div>
      <p className="sync-progress-meta muted">
        <strong>{percent}%</strong>
        {progress.total_steps > 0 ? (
          <>
            {" "}
            · 단계 {progress.current_step}/{progress.total_steps}
          </>
        ) : null}
        {progress.phase ? <> · {progress.phase}</> : null}
      </p>
      <MigrateProgressLogAccordion logs={progress.logs ?? []} />
    </div>
  );
}
