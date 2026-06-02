import { ChevronDown } from "lucide-react";

interface MigrateProgressLogAccordionProps {
  /** 마이그레이션 작업 로그(시간순) */
  logs: string[];
}

/**
 * 마이그레이션 진행 패널 하단 작업 로그 아코디언.
 * 접힌 상태에서는 최신 로그 한 줄만 요약으로 보여준다.
 */
export default function MigrateProgressLogAccordion({ logs }: MigrateProgressLogAccordionProps) {
  if (logs.length === 0) {
    return null;
  }

  const latestLog = logs[logs.length - 1];

  return (
    <details className="migrate-progress-log">
      <summary className="migrate-progress-log-summary">
        <span className="migrate-progress-log-summary-main">
          <ChevronDown className="migrate-progress-log-chevron" size={16} aria-hidden="true" />
          <span className="migrate-progress-log-title">작업 로그</span>
          <span className="migrate-progress-log-count muted">({logs.length})</span>
        </span>
        <span className="migrate-progress-log-latest" title={latestLog}>
          {latestLog}
        </span>
      </summary>
      <ol className="migrate-progress-log-list">
        {logs.map((line, index) => (
          <li key={`${index}-${line}`} className="migrate-progress-log-item">
            {line}
          </li>
        ))}
      </ol>
    </details>
  );
}
