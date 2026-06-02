import type { WorkLogEntry } from "../components/WorkLogAccordion";

/**
 * FastAPI HTTPException 등 API 오류 응답의 detail 필드를 사용자용 문자열로 변환한다.
 * @param payload JSON 파싱된 응답 본문
 * @param fallback detail이 없을 때 사용할 기본 메시지
 */
export function parseApiErrorDetail(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const detail = (payload as { detail?: unknown }).detail;

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message.trim().length > 0) {
      return message.trim();
    }
  }

  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail.trim();
  }

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          const loc = "loc" in item && Array.isArray(item.loc)
            ? item.loc.filter((segment: unknown) => segment !== "body").join(".")
            : "";
          if (loc) {
            return `${loc}: ${item.msg}`;
          }
          return item.msg;
        }
        return "";
      })
      .filter((value) => value.trim().length > 0);
    if (parts.length > 0) {
      return parts.join(" ");
    }
  }

  return fallback;
}

/**
 * API 오류 응답에서 작업 로그 배열을 추출한다.
 * @param payload JSON 파싱된 응답 본문
 */
export function parseApiErrorLogs(payload: unknown): WorkLogEntry[] {
  if (!payload || typeof payload !== "object") {
    return [];
  }

  const root = payload as { detail?: unknown; logs?: unknown };
  if (Array.isArray(root.logs)) {
    return root.logs as WorkLogEntry[];
  }

  const detail = root.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const nestedLogs = (detail as { logs?: unknown }).logs;
    if (Array.isArray(nestedLogs)) {
      return nestedLogs as WorkLogEntry[];
    }
  }

  return [];
}
