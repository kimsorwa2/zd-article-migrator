import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy, PlugZap, Send } from "lucide-react";
import {
  apiClient,
  type Instance,
  type ZendeskProxyResponse,
  type ZendeskApiCatalog,
} from "../api/client";
import LoadingPanel from "../components/LoadingPanel";
import NoticeBanner from "../components/NoticeBanner";
import WorkLogAccordion, { type WorkLogEntry } from "../components/WorkLogAccordion";
import ZendeskApiCatalogPicker, {
  DEFAULT_SHOW_TICKET_PATH_TEMPLATE,
  parsePathTemplateValues,
  resolvePathTemplate,
  type CatalogSelectionState,
} from "../components/ZendeskApiCatalogPicker";
import ApiRequestParamsPanel, {
  buildPathParamRows,
  createHeaderRow,
  createQueryRow,
  headerRowsToObject,
  parseQueryTextToRows,
  pathParamRowsToValues,
  queryRowsToText,
  type ApiRequestBodyTab,
  type ApiRequestHeaderRow,
  type ApiRequestPathParamRow,
  type ApiRequestQueryRow,
} from "../components/ApiRequestParamsPanel";
import { ROUTE_TITLES } from "../components/AppSidebar";
import { useTimedNotice } from "../hooks/useTimedNotice";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

interface ApiRequestPageProps {
  instances: Instance[];
}

/**
 * key=value& 형태 쿼리 문자열을 객체로 파싱한다.
 */
function parseQueryText(raw: string): Record<string, string> | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const params: Record<string, string> = {};
  for (const part of trimmed.split("&")) {
    const segment = part.trim();
    if (!segment) {
      continue;
    }
    const eqIndex = segment.indexOf("=");
    if (eqIndex === -1) {
      params[segment] = "";
    } else {
      const key = segment.slice(0, eqIndex).trim();
      const value = segment.slice(eqIndex + 1).trim();
      if (key) {
        params[key] = value;
      }
    }
  }
  return Object.keys(params).length > 0 ? params : null;
}

/**
 * ISO 시각을 로그용 로컬 문자열로 변환한다.
 */
function formatLogTimestamp(date: Date): string {
  return date.toLocaleTimeString("ko-KR", { hour12: false });
}

/**
 * Zendesk OAuth 프록시 API Request 콘솔 페이지.
 */
export default function ApiRequestPage({ instances }: ApiRequestPageProps) {
  const connectedInstances = useMemo(
    () => instances.filter((instance) => instance.oauth_connected && instance.is_active),
    [instances],
  );

  const [catalog, setCatalog] = useState<ZendeskApiCatalog | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogNotice, setCatalogNotice] = useState<string | null>(null);

  const [instanceId, setInstanceId] = useState<number>(0);
  const [method, setMethod] = useState<(typeof HTTP_METHODS)[number]>("GET");
  const [path, setPath] = useState(DEFAULT_SHOW_TICKET_PATH_TEMPLATE);
  const [pathTemplate, setPathTemplate] = useState(DEFAULT_SHOW_TICKET_PATH_TEMPLATE);
  const [pathParamRows, setPathParamRows] = useState<ApiRequestPathParamRow[]>(() =>
    buildPathParamRows(["ticket_id"], { ticket_id: "" }),
  );
  const [queryRows, setQueryRows] = useState<ApiRequestQueryRow[]>(() => [createQueryRow()]);
  const [jsonBodyText, setJsonBodyText] = useState("");
  const [rawBodyText, setRawBodyText] = useState("");
  const [bodyTab, setBodyTab] = useState<ApiRequestBodyTab>("json");
  const [headerRows, setHeaderRows] = useState<ApiRequestHeaderRow[]>(() => [createHeaderRow()]);

  const [sending, setSending] = useState(false);
  const { message, noticeVariant, setMessage, clearMessage } = useTimedNotice();
  const [response, setResponse] = useState<ZendeskProxyResponse | null>(null);
  const [responseText, setResponseText] = useState("");
  const [logs, setLogs] = useState<WorkLogEntry[]>([]);

  const selectedInstance =
    connectedInstances.find((instance) => instance.id === instanceId) ?? null;

  const bodyRequired = method === "POST" || method === "PUT" || method === "PATCH";

  const jsonBodyError = useMemo(() => {
    if (!bodyRequired || bodyTab !== "json") {
      return null;
    }
    if (!jsonBodyText.trim()) {
      return null;
    }
    try {
      JSON.parse(jsonBodyText);
      return null;
    } catch {
      return "요청 본문 JSON 형식이 올바르지 않습니다.";
    }
  }, [bodyRequired, bodyTab, jsonBodyText]);

  const bodyTabBlocksSend = bodyRequired && bodyTab === "files";

  const pathParamsReady = !/\{[^}]+\}/.test(path);

  const canSend =
    selectedInstance !== null &&
    path.trim().startsWith("/api/v2/") &&
    pathParamsReady &&
    !jsonBodyError &&
    !bodyTabBlocksSend &&
    !sending;

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogNotice(null);
    try {
      const data = await apiClient.fetchZendeskApiCatalog();
      setCatalog(data);
    } catch (error) {
      setCatalog(null);
      setCatalogNotice(
        error instanceof Error ? error.message : "API 카탈로그를 불러오지 못했습니다.",
      );
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    if (connectedInstances.length === 0) {
      setInstanceId(0);
      return;
    }
    setInstanceId((current) => {
      if (current !== 0 && connectedInstances.some((instance) => instance.id === current)) {
        return current;
      }
      return connectedInstances[0]?.id ?? 0;
    });
  }, [connectedInstances]);

  function handleCatalogSelection(state: CatalogSelectionState) {
    setMethod(state.method);
    setPathTemplate(state.pathTemplate);
    setPathParamRows((current) => {
      const nextRows = buildPathParamRows(
        state.pathParamNames,
        pathParamRowsToValues(current),
        current,
      );
      setPath(resolvePathTemplate(state.pathTemplate, pathParamRowsToValues(nextRows)));
      return nextRows;
    });
    setQueryRows(parseQueryTextToRows(state.queryText));
    setJsonBodyText(state.jsonBodyText);
    if (state.jsonBodyText.trim()) {
      setBodyTab("json");
    }
  }

  function handlePathParamRowsChange(rows: ApiRequestPathParamRow[]) {
    setPathParamRows(rows);
    setPath(resolvePathTemplate(pathTemplate, pathParamRowsToValues(rows)));
  }

  /**
   * URL path 직접 수정 시 Params 입력값과 동기화한다.
   */
  function handlePathChange(nextPath: string) {
    if (!pathTemplate) {
      setPath(nextPath);
      return;
    }

    setPathParamRows((current) => {
      if (current.length === 0) {
        setPath(nextPath);
        return current;
      }

      const parsed = parsePathTemplateValues(pathTemplate, nextPath);
      const nextRows = current.map((row) => ({
        ...row,
        value: row.key in parsed ? parsed[row.key] : row.value,
      }));
      setPath(resolvePathTemplate(pathTemplate, pathParamRowsToValues(nextRows)));
      return nextRows;
    });
  }

  function appendLog(entry: WorkLogEntry) {
    setLogs((prev) => [...prev, entry].slice(-20));
  }

  async function handleSend() {
    if (!selectedInstance || !canSend) {
      return;
    }

    setSending(true);
    clearMessage();
    setResponse(null);
    setResponseText("");

    let jsonBody: Record<string, unknown> | null = null;
    let rawBody: string | null = null;

    if (bodyRequired) {
      if (bodyTab === "files") {
        setMessage("Files 본문은 아직 프록시에서 지원하지 않습니다.", { variant: "error" });
        setSending(false);
        return;
      }
      if (bodyTab === "json" && jsonBodyText.trim()) {
        try {
          jsonBody = JSON.parse(jsonBodyText) as Record<string, unknown>;
        } catch {
          setMessage("요청 본문 JSON 형식이 올바르지 않습니다.", { variant: "error" });
          setSending(false);
          return;
        }
      }
      if (bodyTab === "raw" && rawBodyText.trim()) {
        rawBody = rawBodyText;
      }
    }

    const payload = {
      instance_id: selectedInstance.id,
      method,
      path: path.trim(),
      json_body: jsonBody,
      raw_body: rawBody,
      query_params: parseQueryText(queryRowsToText(queryRows)),
      request_headers: headerRowsToObject(headerRows),
    };

    appendLog({
      timestamp: formatLogTimestamp(new Date()),
      level: "info",
      summary: `${method} ${path}`,
      body: JSON.stringify(payload, null, 2),
    });

    try {
      const result = await apiClient.zendeskProxyRequest(payload);
      setResponse(result);
      const formatted =
        result.response_body === null || result.response_body === undefined
          ? ""
          : typeof result.response_body === "string"
            ? result.response_body
            : JSON.stringify(result.response_body, null, 2);
      setResponseText(formatted);

      appendLog({
        timestamp: formatLogTimestamp(new Date()),
        level: result.success ? "success" : "error",
        summary: `HTTP ${result.http_status} · ${result.latency_ms}ms`,
        body: formatted || result.error_message || "(empty body)",
      });

      if (!result.success) {
        setMessage(result.error_message ?? `Zendesk API 오류 (HTTP ${result.http_status})`, {
          variant: "error",
        });
      }
    } catch (error) {
      const text = error instanceof Error ? error.message : "API 요청에 실패했습니다.";
      setMessage(text, { variant: "error" });
      appendLog({
        timestamp: formatLogTimestamp(new Date()),
        level: "error",
        summary: "프록시 요청 실패",
        body: text,
      });
    } finally {
      setSending(false);
    }
  }

  async function copyResponse() {
    if (!responseText) {
      return;
    }
    await navigator.clipboard.writeText(responseText);
    setMessage("응답 본문을 클립보드에 복사했습니다.");
  }

  async function copyCurl() {
    if (!selectedInstance) {
      return;
    }
    const host = selectedInstance.subdomain.replace(".zendesk.com", "");
    const query = queryRowsToText(queryRows);
    const querySuffix = query ? `?${query}` : "";
    const url = `https://${host}.zendesk.com${path.trim()}${querySuffix}`;
    const lines = [`curl "${url}"`, '  -H "Authorization: Bearer <ACCESS_TOKEN>"'];
    const headerObject = headerRowsToObject(headerRows);
    if (headerObject) {
      for (const [key, value] of Object.entries(headerObject)) {
        lines.push(`  -H "${key}: ${value}"`);
      }
    } else if (bodyRequired && (bodyTab === "json" || bodyTab === "raw")) {
      lines.push('  -H "Content-Type: application/json"');
    }
    if (bodyRequired && bodyTab === "json" && jsonBodyText.trim()) {
      lines.push(`  -d '${jsonBodyText.trim().replace(/'/g, "'\\''")}'`);
    } else if (bodyRequired && bodyTab === "raw" && rawBodyText.trim()) {
      lines.push(`  -d '${rawBodyText.trim().replace(/'/g, "'\\''")}'`);
    }
    lines.push(`  -X ${method}`);
    await navigator.clipboard.writeText(lines.join(" \\\n"));
    setMessage("cURL 예시를 클립보드에 복사했습니다.");
  }

  if (catalogLoading) {
    return <LoadingPanel message="Zendesk API 카탈로그를 불러오는 중…" />;
  }

  return (
    <section className="page page-api-request">
      <header className="page-top">
        <h2 className="page-title">
          <PlugZap size={24} aria-hidden="true" />
          {ROUTE_TITLES["api-request"]}
        </h2>
        <p className="page-lead">
          등록된 Zendesk 인스턴스 OAuth 토큰으로{" "}
          <a href="https://developer.zendesk.com/api-reference/" target="_blank" rel="noreferrer">
            Zendesk API
          </a>
          (Ticketing, Help Center, Voice TPE, Custom Data, Omnichannel)를 호출합니다. access token은
          서버에서만 사용됩니다.
        </p>
      </header>

      {message ? <NoticeBanner message={message} variant={noticeVariant} onDismiss={clearMessage} /> : null}
      {catalogNotice ? (
        <NoticeBanner
          message={catalogNotice}
          variant="error"
          onDismiss={() => setCatalogNotice(null)}
        />
      ) : null}

      {connectedInstances.length === 0 ? (
        <NoticeBanner
          variant="error"
          message="OAuth가 연결된 활성 인스턴스가 없습니다. 연결 · 설정 → Zendesk 인스턴스에서 OAuth를 연결하세요."
          onDismiss={() => undefined}
        />
      ) : null}

      <div className="api-request-layout">
        <div className="card api-request-panel">

          <div className="form-grid">
            <label>
              Zendesk 인스턴스
              <select
                value={instanceId || ""}
                disabled={connectedInstances.length === 0 || sending}
                onChange={(event) => setInstanceId(Number(event.target.value))}
              >
                {connectedInstances.map((instance) => (
                  <option key={instance.id} value={instance.id}>
                    {instance.name} ({instance.subdomain})
                  </option>
                ))}
              </select>
              {selectedInstance ? (
                <span className="form-hint">
                  OAuth 연결됨 · scope: <code>{selectedInstance.oauth_scopes || "read write"}</code>
                </span>
              ) : null}
            </label>
          </div>

          <div className="api-request-builder">
            <section className="api-request-builder-section api-request-builder-catalog">
              <ZendeskApiCatalogPicker
                catalog={catalog}
                disabled={sending}
                onSelectionChange={handleCatalogSelection}
              />
            </section>

            <section className="api-request-builder-section api-request-builder-urlbar">
              <div className="api-request-urlbar">
                <label className="api-request-urlbar-method">
                  <span className="sr-only">HTTP Method</span>
                  <select
                    value={method}
                    disabled={sending}
                    className={`api-request-method-select api-request-method-${method.toLowerCase()}`}
                    onChange={(event) => setMethod(event.target.value as typeof method)}
                  >
                    {HTTP_METHODS.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="api-request-urlbar-path">
                  <span className="sr-only">Request Path</span>
                  <input
                    value={path}
                    disabled={sending}
                    spellCheck={false}
                    placeholder={pathTemplate || DEFAULT_SHOW_TICKET_PATH_TEMPLATE}
                    onChange={(event) => handlePathChange(event.target.value)}
                  />
                </label>
                <button
                  type="button"
                  className="button-primary api-request-urlbar-send"
                  disabled={!canSend}
                  onClick={() => void handleSend()}
                >
                  <Send size={16} aria-hidden="true" />
                  {sending ? "전송 중…" : "보내기"}
                </button>
              </div>
            </section>

            <section className="api-request-builder-section api-request-builder-params">
              <ApiRequestParamsPanel
                disabled={sending}
                bodyRequired={bodyRequired}
                pathParamRows={pathParamRows}
                onPathParamRowsChange={handlePathParamRowsChange}
                queryRows={queryRows}
                onQueryRowsChange={setQueryRows}
                headerRows={headerRows}
                onHeaderRowsChange={setHeaderRows}
                bodyTab={bodyTab}
                onBodyTabChange={setBodyTab}
                jsonBodyText={jsonBodyText}
                onJsonBodyTextChange={setJsonBodyText}
                rawBodyText={rawBodyText}
                onRawBodyTextChange={setRawBodyText}
                jsonBodyError={jsonBodyError}
              />
            </section>
          </div>
        </div>

        <div className="card api-request-panel api-request-panel-response">
          <div className="card-header-row">
            <h3>응답</h3>
            <div className="api-request-response-actions">
              <button type="button" className="button-ghost" disabled={!responseText} onClick={() => void copyResponse()}>
                <Copy size={14} aria-hidden="true" />
                응답 복사
              </button>
              <button type="button" className="button-ghost" disabled={!selectedInstance} onClick={() => void copyCurl()}>
                <Copy size={14} aria-hidden="true" />
                cURL 복사
              </button>
            </div>
          </div>

          {response ? (
            <p className={`api-request-status ${response.success ? "ok" : "error"}`}>
              HTTP {response.http_status} · {response.latency_ms}ms
              {response.error_message ? ` · ${response.error_message}` : ""}
            </p>
          ) : (
            <p className="muted">요청을 보내면 응답이 여기에 표시됩니다.</p>
          )}

          <pre className="api-request-response-body">{responseText || " "}</pre>
        </div>
      </div>

      <WorkLogAccordion title="API 작업 로그" entries={logs} />
    </section>
  );
}
