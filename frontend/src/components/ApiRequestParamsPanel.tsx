import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

export type ApiRequestParamTab = "params" | "query" | "headers" | "body";
export type ApiRequestBodyTab = "json" | "raw" | "files";

export interface ApiRequestHeaderRow {
  id: string;
  key: string;
  value: string;
  description: string;
  enabled: boolean;
}

export interface ApiRequestQueryRow {
  id: string;
  key: string;
  value: string;
  description: string;
  enabled: boolean;
}

export interface ApiRequestPathParamRow {
  id: string;
  key: string;
  value: string;
  description: string;
  enabled: boolean;
}

interface ApiRequestParamsPanelProps {
  disabled?: boolean;
  bodyRequired: boolean;
  pathParamRows: ApiRequestPathParamRow[];
  onPathParamRowsChange: (rows: ApiRequestPathParamRow[]) => void;
  queryRows: ApiRequestQueryRow[];
  onQueryRowsChange: (rows: ApiRequestQueryRow[]) => void;
  headerRows: ApiRequestHeaderRow[];
  onHeaderRowsChange: (rows: ApiRequestHeaderRow[]) => void;
  bodyTab: ApiRequestBodyTab;
  onBodyTabChange: (tab: ApiRequestBodyTab) => void;
  jsonBodyText: string;
  onJsonBodyTextChange: (value: string) => void;
  rawBodyText: string;
  onRawBodyTextChange: (value: string) => void;
  jsonBodyError: string | null;
}

let headerRowSeed = 0;
let queryRowSeed = 0;
let pathParamRowSeed = 0;

/**
 * path parameter 행 목록을 path 치환용 map으로 변환한다.
 */
export function pathParamRowsToValues(rows: ApiRequestPathParamRow[]): Record<string, string> {
  const values: Record<string, string> = {};
  for (const row of rows) {
    if (!row.enabled) {
      values[row.key] = "";
      continue;
    }
    values[row.key] = row.value;
  }
  return values;
}

/**
 * path parameter 이름 목록으로 테이블 행을 생성한다.
 */
export function buildPathParamRows(
  names: string[],
  values: Record<string, string>,
  previousRows: ApiRequestPathParamRow[] = [],
): ApiRequestPathParamRow[] {
  const previousByKey = new Map(previousRows.map((row) => [row.key, row]));
  return names.map((name) => {
    const previous = previousByKey.get(name);
    return createPathParamRow({
      key: name,
      value: values[name] ?? previous?.value ?? "",
      description: previous?.description ?? "",
      enabled: previous?.enabled ?? true,
    });
  });
}

/**
 * path parameter 행 id를 생성한다.
 */
export function createPathParamRow(
  partial?: Partial<Pick<ApiRequestPathParamRow, "key" | "value" | "description" | "enabled">>,
): ApiRequestPathParamRow {
  pathParamRowSeed += 1;
  return {
    id: `path-param-${pathParamRowSeed}`,
    key: "",
    value: "",
    description: "",
    enabled: true,
    ...partial,
  };
}

/**
 * 활성화된 query 행을 key=value& 문자열로 변환한다.
 */
export function queryRowsToText(rows: ApiRequestQueryRow[]): string {
  return rows
    .filter((row) => row.enabled && row.key.trim())
    .map((row) => `${row.key.trim()}=${row.value}`)
    .join("&");
}

/**
 * key=value& 문자열을 query 테이블 행으로 파싱한다.
 */
export function parseQueryTextToRows(text: string): ApiRequestQueryRow[] {
  const trimmed = text.trim();
  if (!trimmed) {
    return [createQueryRow()];
  }

  const rows = trimmed.split("&").map((part) => {
    const segment = part.trim();
    if (!segment) {
      return createQueryRow();
    }
    const eqIndex = segment.indexOf("=");
    if (eqIndex === -1) {
      return createQueryRow({ key: segment, enabled: true });
    }
    return createQueryRow({
      key: segment.slice(0, eqIndex).trim(),
      value: segment.slice(eqIndex + 1).trim(),
      enabled: true,
    });
  });

  return ensureTrailingEmptyQueryRow(rows.filter((row) => row.key || row.value));
}

/**
 * 빈 query 행 id를 생성한다.
 */
export function createQueryRow(
  partial?: Partial<Pick<ApiRequestQueryRow, "key" | "value" | "description" | "enabled">>,
): ApiRequestQueryRow {
  queryRowSeed += 1;
  return {
    id: `query-${queryRowSeed}`,
    key: "",
    value: "",
    description: "",
    enabled: true,
    ...partial,
  };
}

/**
 * 마지막에 빈 입력 행이 하나 있도록 보장한다.
 */
function ensureTrailingEmptyQueryRow(rows: ApiRequestQueryRow[]): ApiRequestQueryRow[] {
  if (rows.length === 0) {
    return [createQueryRow()];
  }
  const last = rows[rows.length - 1];
  if (last.key.trim() || last.value.trim() || last.description.trim()) {
    return [...rows, createQueryRow()];
  }
  return rows;
}

/**
 * 활성화된 헤더 행을 API 요청용 객체로 변환한다.
 */
export function headerRowsToObject(rows: ApiRequestHeaderRow[]): Record<string, string> | null {
  const headers: Record<string, string> = {};
  for (const row of rows) {
    if (!row.enabled) {
      continue;
    }
    const key = row.key.trim();
    if (!key) {
      continue;
    }
    headers[key] = row.value;
  }
  return Object.keys(headers).length > 0 ? headers : null;
}

/**
 * 마지막에 빈 헤더 행이 하나 있도록 보장한다.
 */
function ensureTrailingEmptyHeaderRow(rows: ApiRequestHeaderRow[]): ApiRequestHeaderRow[] {
  if (rows.length === 0) {
    return [createHeaderRow()];
  }
  const last = rows[rows.length - 1];
  if (last.key.trim() || last.value.trim() || last.description.trim()) {
    return [...rows, createHeaderRow()];
  }
  return rows;
}

/**
 * 빈 헤더 행 id를 생성한다.
 */
export function createHeaderRow(
  partial?: Partial<Pick<ApiRequestHeaderRow, "key" | "value" | "description" | "enabled">>,
): ApiRequestHeaderRow {
  headerRowSeed += 1;
  return {
    id: `header-${headerRowSeed}`,
    key: "",
    value: "",
    description: "",
    enabled: true,
    ...partial,
  };
}

/**
 * Query·Headers·Body(JSON/Raw/Files) 탭형 요청 파라미터 패널.
 */
export default function ApiRequestParamsPanel({
  disabled = false,
  bodyRequired,
  pathParamRows,
  onPathParamRowsChange,
  queryRows,
  onQueryRowsChange,
  headerRows,
  onHeaderRowsChange,
  bodyTab,
  onBodyTabChange,
  jsonBodyText,
  onJsonBodyTextChange,
  rawBodyText,
  onRawBodyTextChange,
  jsonBodyError,
}: ApiRequestParamsPanelProps) {
  const [paramTab, setParamTab] = useState<ApiRequestParamTab>("query");

  const pathParamKey = pathParamRows.map((row) => row.key).join("\u0000");

  useEffect(() => {
    if (pathParamRows.length > 0) {
      setParamTab("params");
    }
  }, [pathParamKey, pathParamRows.length]);

  const paramTabs = useMemo(
    () =>
      [
        { id: "params" as const, label: "Params" },
        { id: "query" as const, label: "Query" },
        { id: "headers" as const, label: "Headers" },
        { id: "body" as const, label: "Body" },
      ] satisfies Array<{ id: ApiRequestParamTab; label: string }>,
    [],
  );

  const bodyTabs = useMemo(
    () =>
      [
        { id: "json" as const, label: "JSON" },
        { id: "raw" as const, label: "Raw" },
        { id: "files" as const, label: "Files" },
      ] satisfies Array<{ id: ApiRequestBodyTab; label: string }>,
    [],
  );

  function updateHeaderRows(nextRows: ApiRequestHeaderRow[]) {
    onHeaderRowsChange(ensureTrailingEmptyHeaderRow(nextRows));
  }

  function updateHeaderRow(
    rowId: string,
    patch: Partial<Pick<ApiRequestHeaderRow, "key" | "value" | "description" | "enabled">>,
  ) {
    updateHeaderRows(headerRows.map((row) => (row.id === rowId ? { ...row, ...patch } : row)));
  }

  function removeHeaderRow(rowId: string) {
    const next = headerRows.filter((row) => row.id !== rowId);
    updateHeaderRows(next.length > 0 ? next : [createHeaderRow()]);
  }

  /** HTTP 헤더 행을 추가한다. */
  function addHeaderRow() {
    updateHeaderRows([...headerRows, createHeaderRow()]);
  }

  function updateQueryRows(nextRows: ApiRequestQueryRow[]) {
    onQueryRowsChange(ensureTrailingEmptyQueryRow(nextRows));
  }

  function updateQueryRow(
    rowId: string,
    patch: Partial<Pick<ApiRequestQueryRow, "key" | "value" | "description" | "enabled">>,
  ) {
    updateQueryRows(queryRows.map((row) => (row.id === rowId ? { ...row, ...patch } : row)));
  }

  function removeQueryRow(rowId: string) {
    const next = queryRows.filter((row) => row.id !== rowId);
    updateQueryRows(next.length > 0 ? next : [createQueryRow()]);
  }

  /** Query 파라미터 행을 추가한다. */
  function addQueryRow() {
    updateQueryRows([...queryRows, createQueryRow()]);
  }

  function updatePathParamRow(
    rowId: string,
    patch: Partial<Pick<ApiRequestPathParamRow, "value" | "description" | "enabled">>,
  ) {
    onPathParamRowsChange(pathParamRows.map((row) => (row.id === rowId ? { ...row, ...patch } : row)));
  }

  return (
    <div className="api-request-params">
      <div className="api-request-segment-tabs" role="tablist" aria-label="요청 파라미터">
        {paramTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={paramTab === tab.id}
            className={`api-request-segment-tab${paramTab === tab.id ? " is-active" : ""}`}
            disabled={disabled}
            onClick={() => setParamTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="api-request-segment-panel" role="tabpanel">
        {paramTab === "params" ? (
          <div className="api-request-kv-table-wrap">
            {pathParamRows.length === 0 ? (
              <p className="muted api-request-param-panel-lead">
                선택한 API에 Path Parameter가 없습니다. URL 경로에 변수가 필요하면 Path 필드에 직접 입력하세요.
              </p>
            ) : (
              <>
                <p className="api-request-kv-table-title">Path Params</p>
                <div className="api-request-kv-table api-request-kv-table--path" role="table" aria-label="Path Params">
                  <div className="api-request-kv-table-head" role="row">
                    <span className="api-request-kv-table-check" role="columnheader" aria-hidden="true" />
                    <span role="columnheader">Key</span>
                    <span role="columnheader">Value</span>
                    <span role="columnheader">Description</span>
                  </div>
                  {pathParamRows.map((row) => (
                    <div key={row.id} className="api-request-kv-table-row" role="row">
                      <label className="api-request-kv-table-check">
                        <span className="sr-only">{row.key} path parameter 사용</span>
                        <input
                          type="checkbox"
                          checked={row.enabled}
                          disabled={disabled}
                          onChange={(event) => updatePathParamRow(row.id, { enabled: event.target.checked })}
                        />
                      </label>
                      <span className="api-request-kv-table-key" aria-label="Path parameter key">
                        {row.key}
                      </span>
                      <input
                        value={row.value}
                        disabled={disabled || !row.enabled}
                        placeholder={`{${row.key}}`}
                        spellCheck={false}
                        aria-label="Path parameter value"
                        onChange={(event) => updatePathParamRow(row.id, { value: event.target.value })}
                      />
                      <input
                        value={row.description}
                        disabled={disabled}
                        placeholder="Description"
                        spellCheck={false}
                        aria-label="Path parameter description"
                        onChange={(event) => updatePathParamRow(row.id, { description: event.target.value })}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : null}

        {paramTab === "query" ? (
          <div className="api-request-kv-table-wrap">
            <div className="api-request-kv-table-toolbar">
              <p className="api-request-kv-table-title">Query Params</p>
              <button
                type="button"
                className="button-ghost api-request-kv-table-add"
                disabled={disabled}
                onClick={addQueryRow}
              >
                <Plus size={14} aria-hidden="true" />
                파라미터 추가
              </button>
            </div>
            <div className="api-request-kv-table" role="table" aria-label="Query Params">
              <div className="api-request-kv-table-head" role="row">
                <span className="api-request-kv-table-check" role="columnheader" aria-hidden="true" />
                <span role="columnheader">Key</span>
                <span role="columnheader">Value</span>
                <span role="columnheader">Description</span>
                <span className="api-request-kv-table-actions" role="columnheader" aria-hidden="true" />
              </div>
              {queryRows.map((row) => (
                <div key={row.id} className="api-request-kv-table-row" role="row">
                  <label className="api-request-kv-table-check">
                    <span className="sr-only">{row.key || "query"} 파라미터 사용</span>
                    <input
                      type="checkbox"
                      checked={row.enabled}
                      disabled={disabled}
                      onChange={(event) => updateQueryRow(row.id, { enabled: event.target.checked })}
                    />
                  </label>
                  <input
                    value={row.key}
                    disabled={disabled}
                    placeholder="Key"
                    spellCheck={false}
                    aria-label="Query key"
                    onChange={(event) => updateQueryRow(row.id, { key: event.target.value })}
                  />
                  <input
                    value={row.value}
                    disabled={disabled}
                    placeholder="Value"
                    spellCheck={false}
                    aria-label="Query value"
                    onChange={(event) => updateQueryRow(row.id, { value: event.target.value })}
                  />
                  <input
                    value={row.description}
                    disabled={disabled}
                    placeholder="Description"
                    spellCheck={false}
                    aria-label="Query description"
                    onChange={(event) => updateQueryRow(row.id, { description: event.target.value })}
                  />
                  <button
                    type="button"
                    className="icon-button api-request-kv-table-remove"
                    disabled={disabled || queryRows.length <= 1}
                    aria-label="Query 파라미터 삭제"
                    onClick={() => removeQueryRow(row.id)}
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {paramTab === "headers" ? (
          <div className="api-request-kv-table-wrap">
            <div className="api-request-kv-table-toolbar">
              <div className="api-request-kv-table-toolbar-text">
                <p className="api-request-kv-table-title">Headers</p>
                <p className="api-request-kv-table-hint muted">
                  Authorization은 OAuth 토큰으로 자동 설정됩니다.
                </p>
              </div>
              <button
                type="button"
                className="button-ghost api-request-kv-table-add"
                disabled={disabled}
                onClick={addHeaderRow}
              >
                <Plus size={14} aria-hidden="true" />
                헤더 추가
              </button>
            </div>
            <div className="api-request-kv-table" role="table" aria-label="Headers">
              <div className="api-request-kv-table-head" role="row">
                <span className="api-request-kv-table-check" role="columnheader" aria-hidden="true" />
                <span role="columnheader">Key</span>
                <span role="columnheader">Value</span>
                <span role="columnheader">Description</span>
                <span className="api-request-kv-table-actions" role="columnheader" aria-hidden="true" />
              </div>
              {headerRows.map((row) => (
                <div key={row.id} className="api-request-kv-table-row" role="row">
                  <label className="api-request-kv-table-check">
                    <span className="sr-only">{row.key || "header"} 사용</span>
                    <input
                      type="checkbox"
                      checked={row.enabled}
                      disabled={disabled}
                      onChange={(event) => updateHeaderRow(row.id, { enabled: event.target.checked })}
                    />
                  </label>
                  <input
                    value={row.key}
                    disabled={disabled || !row.enabled}
                    placeholder="Key"
                    spellCheck={false}
                    aria-label="Header key"
                    onChange={(event) => updateHeaderRow(row.id, { key: event.target.value })}
                  />
                  <input
                    value={row.value}
                    disabled={disabled || !row.enabled}
                    placeholder="Value"
                    spellCheck={false}
                    aria-label="Header value"
                    onChange={(event) => updateHeaderRow(row.id, { value: event.target.value })}
                  />
                  <input
                    value={row.description}
                    disabled={disabled}
                    placeholder="Description"
                    spellCheck={false}
                    aria-label="Header description"
                    onChange={(event) => updateHeaderRow(row.id, { description: event.target.value })}
                  />
                  <button
                    type="button"
                    className="icon-button api-request-kv-table-remove"
                    disabled={disabled || headerRows.length <= 1}
                    aria-label="헤더 삭제"
                    onClick={() => removeHeaderRow(row.id)}
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {paramTab === "body" ? (
          <>
            <div className="api-request-subtabs" role="tablist" aria-label="요청 본문 형식">
              {bodyTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={bodyTab === tab.id}
                  className={`api-request-subtab${bodyTab === tab.id ? " is-active" : ""}`}
                  disabled={disabled}
                  onClick={() => onBodyTabChange(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="api-request-subpanel">
              {bodyTab === "json" ? (
                <label className="api-request-param-field">
                  <textarea
                    className="api-request-json-editor"
                    rows={10}
                    value={jsonBodyText}
                    disabled={disabled || !bodyRequired}
                    spellCheck={false}
                    placeholder={
                      bodyRequired ? '{"ticket": {"subject": "Sample"}}' : "본문이 필요한 메서드를 선택하세요."
                    }
                    onChange={(event) => onJsonBodyTextChange(event.target.value)}
                  />
                  {jsonBodyError ? (
                    <span className="form-hint api-request-field-error">{jsonBodyError}</span>
                  ) : null}
                </label>
              ) : null}

              {bodyTab === "raw" ? (
                <label className="api-request-param-field">
                  <textarea
                    className="api-request-json-editor"
                    rows={10}
                    value={rawBodyText}
                    disabled={disabled || !bodyRequired}
                    spellCheck={false}
                    placeholder={
                      bodyRequired ? "plain text 또는 JSON 문자열" : "본문이 필요한 메서드를 선택하세요."
                    }
                    onChange={(event) => onRawBodyTextChange(event.target.value)}
                  />
                  <span className="form-hint">Content-Type은 Headers 탭에서 지정할 수 있습니다.</span>
                </label>
              ) : null}

              {bodyTab === "files" ? (
                <div className="api-request-files-panel">
                  <p className="muted api-request-param-panel-lead">
                    multipart/form-data 업로드는 현재 프록시에서 지원하지 않습니다. cURL로 직접 호출하거나 후속
                    버전에서 지원 예정입니다.
                  </p>
                  <label className="api-request-param-field">
                    <span className="api-request-param-field-label">File (미리보기)</span>
                    <input type="file" disabled />
                  </label>
                  <label className="api-request-param-field">
                    <span className="api-request-param-field-label">Field name</span>
                    <input disabled placeholder="file" />
                  </label>
                </div>
              ) : null}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
