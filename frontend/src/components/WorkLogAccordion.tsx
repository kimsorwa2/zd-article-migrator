import { ChevronDown } from "lucide-react";

export interface WorkLogEntry {
  timestamp: string;
  level: "info" | "error" | "success";
  summary: string;
  body: string;
}

interface WorkLogAccordionProps {
  /** 패널 제목 */
  title?: string;
  /** 작업 로그 목록 */
  entries: WorkLogEntry[];
  /** 비었을 때 숨김 여부 */
  hideWhenEmpty?: boolean;
}

const LEVEL_LABEL: Record<WorkLogEntry["level"], string> = {
  info: "정보",
  error: "오류",
  success: "완료",
};

/**
 * 마이그레이션 작업 로그와 동일한 아코디언 UI로 API 요청·응답 로그를 표시한다.
 */
export default function WorkLogAccordion({
  title = "작업 로그",
  entries,
  hideWhenEmpty = true,
}: WorkLogAccordionProps) {
  if (hideWhenEmpty && entries.length === 0) {
    return null;
  }

  const latest = entries[entries.length - 1];
  const latestPreview = latest ? `[${latest.timestamp}] ${latest.summary}` : "";

  return (
    <details className="migrate-progress-log work-log-accordion" open={entries.some((e) => e.level === "error")}>
      <summary className="migrate-progress-log-summary">
        <span className="migrate-progress-log-summary-main">
          <ChevronDown className="migrate-progress-log-chevron" size={16} aria-hidden="true" />
          <span className="migrate-progress-log-title">{title}</span>
          <span className="migrate-progress-log-count muted">({entries.length})</span>
        </span>
        <span className="migrate-progress-log-latest" title={latestPreview}>
          {latestPreview}
        </span>
      </summary>
      <ol className="migrate-progress-log-list work-log-list">
        {entries.map((entry, index) => (
          <li
            key={`${entry.timestamp}-${index}-${entry.summary}`}
            className={`work-log-item work-log-item-${entry.level}`}
          >
            <div className="work-log-item-head">
              <span className="work-log-time">{entry.timestamp}</span>
              <span className={`work-log-badge work-log-badge-${entry.level}`}>{LEVEL_LABEL[entry.level]}</span>
              <span className="work-log-summary">{entry.summary}</span>
            </div>
            {entry.body ? <pre className="work-log-body">{entry.body}</pre> : null}
          </li>
        ))}
      </ol>
    </details>
  );
}
