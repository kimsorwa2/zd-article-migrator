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
