/**
 * AI OCR 호출 이력의 토큰 수를 표시용 문자열로 변환한다.
 * @param value 토큰 수 (null이면 미기록)
 */
export function formatTokenCount(value: number | null | undefined): string {
  if (value == null) {
    return "-";
  }
  return value.toLocaleString("ko-KR");
}

/**
 * 추론(thinking) 토큰 — API에서 null이면 0으로 간주해 표시한다.
 * @param value 추론 토큰 수
 */
export function formatThinkingTokenCount(value: number | null | undefined): string {
  if (value == null) {
    return "0";
  }
  return value.toLocaleString("ko-KR");
}
