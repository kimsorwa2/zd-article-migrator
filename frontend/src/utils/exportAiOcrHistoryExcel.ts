import * as XLSX from "xlsx";
import type { AiOcrAnalysisHistoryItem } from "../api/client";

/** Excel 셀 최대 길이(초과 시 잘림 안내를 붙인다) */
const EXCEL_CELL_CHAR_LIMIT = 32_000;

/**
 * ISO 시각 문자열을 로컬 표시용 문자열로 변환한다.
 * @param iso ISO 8601 시각
 */
function formatLocalDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("ko-KR");
}

/**
 * 파싱 성공 여부를 Excel용 문자열로 변환한다.
 * @param value DB parse_success
 */
function formatParseSuccess(value: boolean | null | undefined): string {
  if (value === true) {
    return "성공";
  }
  if (value === false) {
    return "실패";
  }
  return "";
}

/**
 * Excel 셀 길이 제한에 맞게 긴 텍스트를 자른다.
 * @param text 원문
 */
function clipCellText(text: string | null | undefined): string {
  if (text == null || text === "") {
    return "";
  }
  if (text.length <= EXCEL_CELL_CHAR_LIMIT) {
    return text;
  }
  return `${text.slice(0, EXCEL_CELL_CHAR_LIMIT)}\n…(길이 제한으로 잘림, 원문 ${text.length}자)`;
}

/**
 * API 이력 한 건을 Excel 행 객체로 변환한다(테이블 + 상세 모달 필드 포함).
 * @param item OCR 호출 이력
 */
export function aiOcrHistoryItemToExportRow(
  item: AiOcrAnalysisHistoryItem,
): Record<string, string | number> {
  return {
    ID: item.id,
    일시: formatLocalDateTime(item.created_at),
    라벨: item.display_label ?? item.label,
    모델: item.ai_model ?? "",
    "프롬프트 ID": item.prompt_template_id ?? "",
    "소스 파일명": item.source_filename,
    "이미지 크기(KB)": item.image_size_kb ?? "",
    "입력 토큰": item.input_tokens ?? "",
    "출력 토큰": item.output_tokens ?? "",
    "추론 토큰": item.thinking_tokens ?? 0,
    "총 토큰": item.total_tokens ?? "",
    "지연(ms)": item.latency_ms ?? "",
    "종료 이유": item.finish_reason ?? "",
    "파싱 성공": formatParseSuccess(item.parse_success),
    "실험 태그": item.experiment_tag ?? "",
    제목: item.title,
    "감지 제품": item.detected_product,
    "유지보수 주기": item.maintenance_cycle ?? "",
    라벨명: (item.label_names ?? []).join(", "),
    "본문 미리보기": clipCellText(item.body_preview_text),
    "파싱 오류": clipCellText(item.parse_error_message),
    "System prompt": clipCellText(item.used_system_prompt),
    "User prompt": clipCellText(item.used_user_prompt),
    "AI 원문 응답": clipCellText(item.raw_response_text),
    "HTML 본문": clipCellText(item.html_body),
  };
}

/**
 * AI OCR 호출 이력을 .xlsx 파일로 다운로드한다.
 * @param items 보낼 이력 목록
 * @param fileName 저장 파일명(확장자 제외 가능)
 */
export function downloadAiOcrHistoryExcel(
  items: AiOcrAnalysisHistoryItem[],
  fileName?: string,
): void {
  if (items.length === 0) {
    return;
  }

  const rows = items.map(aiOcrHistoryItemToExportRow);
  const worksheet = XLSX.utils.json_to_sheet(rows);
  worksheet["!cols"] = [
    { wch: 8 },
    { wch: 20 },
    { wch: 36 },
    { wch: 18 },
    { wch: 12 },
    { wch: 24 },
    { wch: 12 },
    { wch: 10 },
    { wch: 10 },
    { wch: 10 },
    { wch: 10 },
    { wch: 10 },
    { wch: 14 },
    { wch: 10 },
    { wch: 12 },
    { wch: 28 },
    { wch: 16 },
    { wch: 14 },
    { wch: 24 },
    { wch: 40 },
    { wch: 40 },
    { wch: 48 },
    { wch: 48 },
    { wch: 56 },
    { wch: 48 },
  ];

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "AI 호출 이력");

  const stamp = new Date().toISOString().slice(0, 10);
  const baseName = fileName?.replace(/\.xlsx$/i, "") ?? `ai-ocr-history-${stamp}`;
  XLSX.writeFile(workbook, `${baseName}.xlsx`);
}
