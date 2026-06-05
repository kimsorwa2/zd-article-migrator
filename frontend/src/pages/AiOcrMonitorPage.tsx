import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BarChart2, FileDown, Trash2, X } from "lucide-react";
import { apiClient, type AiOcrAnalysisHistoryItem } from "../api/client";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import { downloadAiOcrHistoryExcel } from "../utils/exportAiOcrHistoryExcel";
import {
  formatThinkingTokenCount,
  formatTokenCount,
} from "../utils/formatAiOcrTokens";

const METRICS_FETCH_LIMIT = 100;

/**
 * 숫자 배열의 평균을 계산한다. 값이 없으면 null을 반환한다.
 */
function average(values: Array<number | null | undefined>): number | null {
  const numbers = values.filter((value): value is number => typeof value === "number");
  if (numbers.length === 0) {
    return null;
  }
  return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}

/**
 * ISO 시각 문자열을 로컬 표시용 문자열로 변환한다.
 */
function formatLocalDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("ko-KR");
}

/**
 * AI OCR 호출 이력·토큰·지연 시간 모니터링 페이지.
 */
export default function AiOcrMonitorPage() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<AiOcrAnalysisHistoryItem[]>([]);
  const [message, setMessage] = useState<{ type: "error"; text: string } | null>(null);
  const [selectedItem, setSelectedItem] = useState<AiOcrAnalysisHistoryItem | null>(null);
  const [exporting, setExporting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set());
  const [deleting, setDeleting] = useState(false);
  const headerCheckboxRef = useRef<HTMLInputElement>(null);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const response = await apiClient.listAiOcrHistoryMetrics(METRICS_FETCH_LIMIT);
      setItems(response.items);
    } catch (error) {
      setItems([]);
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "AI 호출 이력을 불러오지 못했습니다.",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  const visibleIds = useMemo(() => items.map((item) => item.id), [items]);

  const allSelected =
    items.length > 0 && visibleIds.every((id) => selectedIds.has(id));
  const someSelected =
    visibleIds.some((id) => selectedIds.has(id)) && !allSelected;

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = someSelected;
    }
  }, [someSelected]);

  /** 목록 갱신 후 화면에 없는 ID는 선택에서 제거한다. */
  useEffect(() => {
    setSelectedIds((prev) => {
      const visibleSet = new Set(visibleIds);
      const next = new Set([...prev].filter((id) => visibleSet.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [visibleIds]);

  const toggleSelectAll = useCallback(() => {
    if (allSelected) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(visibleIds));
  }, [allSelected, visibleIds]);

  const toggleSelectOne = useCallback((id: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }, []);

  const handleDeleteSelected = useCallback(async () => {
    const ids = [...selectedIds];
    if (ids.length === 0) {
      return;
    }
    if (!window.confirm(`${ids.length}건의 호출 이력을 DB에서 삭제할까요?`)) {
      return;
    }
    setDeleting(true);
    setMessage(null);
    try {
      const result = await apiClient.deleteAiOcrHistory(ids);
      if (result.deleted_count === 0) {
        setMessage({
          type: "error",
          text: "삭제된 이력이 없습니다. 이미 제거되었을 수 있습니다.",
        });
        return;
      }
      setSelectedIds(new Set());
      if (selectedItem && ids.includes(selectedItem.id)) {
        setSelectedItem(null);
      }
      await loadMetrics();
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "선택한 호출 이력을 삭제하지 못했습니다.",
      });
    } finally {
      setDeleting(false);
    }
  }, [loadMetrics, selectedIds, selectedItem]);

  const handleExportExcel = useCallback((rows: AiOcrAnalysisHistoryItem[], fileName?: string) => {
    if (rows.length === 0) {
      setMessage({ type: "error", text: "보낼 호출 이력이 없습니다." });
      return;
    }
    try {
      downloadAiOcrHistoryExcel(rows, fileName);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Excel 파일을 만들지 못했습니다.",
      });
    }
  }, []);

  const handleExportAll = useCallback(async () => {
    setExporting(true);
    setMessage(null);
    try {
      const response = await apiClient.listAiOcrHistoryMetrics(METRICS_FETCH_LIMIT);
      setItems(response.items);
      handleExportExcel(response.items);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "이력을 불러와 Excel로 보내지 못했습니다.",
      });
    } finally {
      setExporting(false);
    }
  }, [handleExportExcel]);

  const summary = useMemo(() => {
    const avgInput = average(items.map((item) => item.input_tokens));
    const avgTotal = average(items.map((item) => item.total_tokens));
    const avgLatency = average(items.map((item) => item.latency_ms));
    return {
      totalCalls: items.length,
      avgInputTokens: avgInput === null ? "-" : Math.round(avgInput).toLocaleString("ko-KR"),
      avgTotalTokens: avgTotal === null ? "-" : Math.round(avgTotal).toLocaleString("ko-KR"),
      avgLatencyMs: avgLatency === null ? "-" : `${Math.round(avgLatency).toLocaleString("ko-KR")} ms`,
    };
  }, [items]);

  const selectedCount = selectedIds.size;

  return (
    <section className="page ai-ocr-monitor-page">
      <header className="page-top">
        <h2 className="page-title">
          <BarChart2 size={24} aria-hidden="true" />
          AI 호출 이력
        </h2>
        <p className="page-lead">
          AI OCR Vision API 호출 결과(토큰 사용량, 지연 시간, 모델, 프롬프트 템플릿 등)를 확인합니다.
          입력·출력·추론·총 토큰은 제공자별 API usage를 공통 형식으로 정규화해 표시합니다(Gemini
          추론 토큰, Bedrock·OpenAI 미사용 시 0). 행을 클릭하면 프롬프트 스냅샷·AI 원문·파싱
          오류를 볼 수 있습니다.
        </p>
      </header>

      {message ? (
        <NoticeBanner variant="error" message={message.text} onDismiss={() => setMessage(null)} />
      ) : null}

      {loading ? (
        <LoadingPanel variant="panel" message="호출 이력을 불러오는 중..." showSpinner={false} />
      ) : (
        <>
          <div className="grid-2" style={{ marginBottom: 14 }}>
            <div className="card">
              <h3>총 호출 수</h3>
              <p style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>{summary.totalCalls}</p>
              <p className="muted" style={{ margin: "6px 0 0" }}>
                최근 {METRICS_FETCH_LIMIT}건 기준
              </p>
            </div>
            <div className="card">
              <h3>평균 입력 토큰</h3>
              <p style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>{summary.avgInputTokens}</p>
            </div>
            <div className="card">
              <h3>평균 총 토큰</h3>
              <p style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>{summary.avgTotalTokens}</p>
            </div>
            <div className="card">
              <h3>평균 지연 시간</h3>
              <p style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>{summary.avgLatencyMs}</p>
            </div>
          </div>

          <div className="card">
            <div className="card-header-row">
              <h3 style={{ margin: 0 }}>호출 상세</h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="icon-button icon-button--danger"
                  disabled={selectedCount === 0 || deleting}
                  onClick={() => void handleDeleteSelected()}
                >
                  <Trash2 size={16} aria-hidden="true" />
                  {deleting ? "삭제 중…" : `선택 삭제 (${selectedCount})`}
                </button>
                <button
                  type="button"
                  className="icon-button"
                  disabled={items.length === 0 || exporting}
                  onClick={() => handleExportExcel(items)}
                >
                  <FileDown size={16} aria-hidden="true" />
                  Excel 내보내기
                </button>
                <button
                  type="button"
                  className="icon-button"
                  disabled={exporting}
                  onClick={() => void handleExportAll()}
                >
                  {exporting ? "보내는 중…" : "전체 새로고침 후 내보내기"}
                </button>
                <button type="button" className="icon-button" onClick={() => void loadMetrics()}>
                  새로고침
                </button>
              </div>
            </div>

            {items.length === 0 ? (
              <p className="muted">저장된 AI OCR 호출 이력이 없습니다.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table
                  className="ai-ocr-monitor-table"
                  style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}
                >
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left" }}>
                      <th className="ai-ocr-monitor-check-col">
                        <label className="form-checkbox-label form-checkbox-label--table">
                          <input
                            ref={headerCheckboxRef}
                            type="checkbox"
                            checked={allSelected}
                            onChange={toggleSelectAll}
                            aria-label="전체 선택"
                          />
                        </label>
                      </th>
                      <th style={{ padding: "10px 8px" }}>일시</th>
                      <th style={{ padding: "10px 8px" }}>라벨</th>
                      <th style={{ padding: "10px 8px" }}>모델</th>
                      <th style={{ padding: "10px 8px" }}>프롬프트 ID</th>
                      <th style={{ padding: "10px 8px" }}>이미지 크기</th>
                      <th style={{ padding: "10px 8px" }}>전처리</th>
                      <th style={{ padding: "10px 8px" }}>전처리 후(KB)</th>
                      <th style={{ padding: "10px 8px" }}>입력 토큰</th>
                      <th style={{ padding: "10px 8px" }}>출력 토큰</th>
                      <th
                        style={{ padding: "10px 8px" }}
                        title="Gemini thoughts 등 내부 추론. Bedrock·OpenAI 일반 호출은 0"
                      >
                        추론 토큰
                      </th>
                      <th style={{ padding: "10px 8px" }}>총 토큰</th>
                      <th style={{ padding: "10px 8px" }}>지연 시간</th>
                      <th style={{ padding: "10px 8px" }}>종료 이유</th>
                      <th style={{ padding: "10px 8px" }}>파싱 성공</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => {
                      const isRowSelected = selectedIds.has(item.id);
                      return (
                        <tr
                          key={item.id}
                          role="button"
                          tabIndex={0}
                          onClick={() => setSelectedItem(item)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              setSelectedItem(item);
                            }
                          }}
                          style={{
                            borderBottom: "1px solid var(--color-border)",
                            cursor: "pointer",
                            background:
                              selectedItem?.id === item.id ? "rgba(99, 102, 241, 0.08)" : undefined,
                          }}
                        >
                          <td
                            className="ai-ocr-monitor-check-col"
                            onClick={(event) => event.stopPropagation()}
                            onKeyDown={(event) => event.stopPropagation()}
                          >
                            <label className="form-checkbox-label form-checkbox-label--table">
                              <input
                                type="checkbox"
                                checked={isRowSelected}
                                onChange={(event) =>
                                  toggleSelectOne(item.id, event.target.checked)
                                }
                                aria-label={`${item.display_label ?? item.label} 선택`}
                              />
                            </label>
                          </td>
                          <td style={{ padding: "10px 8px", whiteSpace: "nowrap" }}>
                            {formatLocalDateTime(item.created_at)}
                          </td>
                          <td style={{ padding: "10px 8px" }}>{item.display_label ?? item.label}</td>
                          <td style={{ padding: "10px 8px" }}>{item.ai_model ?? "-"}</td>
                          <td style={{ padding: "10px 8px" }}>{item.prompt_template_id ?? "-"}</td>
                          <td style={{ padding: "10px 8px" }}>
                            {item.image_size_kb != null ? `${item.image_size_kb} KB` : "-"}
                          </td>
                          <td style={{ padding: "10px 8px" }}>
                            {item.preprocessed === true
                              ? "✅"
                              : item.preprocessed === false
                                ? "❌"
                                : "-"}
                          </td>
                          <td style={{ padding: "10px 8px" }}>
                            {item.processed_image_size_kb != null
                              ? `${item.processed_image_size_kb} KB`
                              : "-"}
                          </td>
                          <td style={{ padding: "10px 8px" }}>{formatTokenCount(item.input_tokens)}</td>
                          <td style={{ padding: "10px 8px" }}>{formatTokenCount(item.output_tokens)}</td>
                          <td style={{ padding: "10px 8px" }}>
                            {formatThinkingTokenCount(item.thinking_tokens)}
                          </td>
                          <td style={{ padding: "10px 8px" }}>{formatTokenCount(item.total_tokens)}</td>
                          <td style={{ padding: "10px 8px" }}>
                            {item.latency_ms != null ? `${item.latency_ms} ms` : "-"}
                          </td>
                          <td style={{ padding: "10px 8px" }}>{item.finish_reason ?? "-"}</td>
                          <td style={{ padding: "10px 8px" }}>
                            {item.parse_success === true
                              ? "✅"
                              : item.parse_success === false
                                ? "❌"
                                : "-"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {selectedItem ? (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ai-ocr-monitor-detail-title"
          onClick={() => setSelectedItem(null)}
        >
          <div
            className="modal-panel"
            style={{ width: "min(920px, 100%)" }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="ai-ocr-monitor-detail-title" style={{ margin: 0 }}>
                호출 상세 — {selectedItem.display_label ?? selectedItem.label}
              </h3>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() =>
                    handleExportExcel(
                      [selectedItem],
                      `ai-ocr-history-${selectedItem.id}`,
                    )
                  }
                >
                  <FileDown size={16} aria-hidden="true" />
                  이 행 Excel
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="닫기"
                  onClick={() => setSelectedItem(null)}
                >
                  <X size={18} aria-hidden="true" />
                </button>
              </div>
            </div>

            <div className="modal-body">
            {selectedItem.parse_error_message ? (
              <div style={{ marginBottom: 14 }}>
                <h4 style={{ margin: "0 0 6px" }}>파싱 오류</h4>
                <pre
                  style={{
                    margin: 0,
                    padding: 12,
                    borderRadius: 8,
                    background: "#fef2f2",
                    border: "1px solid #fecaca",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontSize: 13,
                    maxHeight: 160,
                    overflow: "auto",
                  }}
                >
                  {selectedItem.parse_error_message}
                </pre>
              </div>
            ) : null}

            <div style={{ marginBottom: 14 }}>
              <h4 style={{ margin: "0 0 6px" }}>System prompt (호출 당시)</h4>
              <pre
                style={{
                  margin: 0,
                  padding: 12,
                  borderRadius: 8,
                  background: "#f8fafc",
                  border: "1px solid var(--color-border)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 13,
                  maxHeight: 200,
                  overflow: "auto",
                }}
              >
                {selectedItem.used_system_prompt ?? "(저장된 스냅샷 없음)"}
              </pre>
            </div>

            <div style={{ marginBottom: 14 }}>
              <h4 style={{ margin: "0 0 6px" }}>User prompt (호출 당시)</h4>
              <pre
                style={{
                  margin: 0,
                  padding: 12,
                  borderRadius: 8,
                  background: "#f8fafc",
                  border: "1px solid var(--color-border)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 13,
                  maxHeight: 200,
                  overflow: "auto",
                }}
              >
                {selectedItem.used_user_prompt ?? "(저장된 스냅샷 없음)"}
              </pre>
            </div>

            <div>
              <h4 style={{ margin: "0 0 6px" }}>AI 원문 응답</h4>
              <pre
                style={{
                  margin: 0,
                  padding: 12,
                  borderRadius: 8,
                  background: "#f8fafc",
                  border: "1px solid var(--color-border)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 12,
                  maxHeight: 360,
                  overflow: "auto",
                }}
              >
                {selectedItem.raw_response_text ?? "(저장된 원문 없음)"}
              </pre>
            </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
