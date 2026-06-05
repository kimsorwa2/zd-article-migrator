/**
 * Zendesk OAuth scope 정의.
 * @see https://developer.zendesk.com/api-reference/ticketing/oauth/oauth_tokens/#scopes
 */

/** Zendesk OAuth scope 문서 URL */
export const ZENDESK_OAUTH_SCOPES_DOC_URL =
  "https://developer.zendesk.com/api-reference/ticketing/oauth/oauth_tokens/#scopes";

/** 셀렉트 옵션 한 항목 */
export interface ZendeskOAuthScopeOption {
  /** scope 문자열 (예: read, hc:write) */
  value: string;
  /** UI 표시 라벨 */
  label: string;
  /** optgroup 제목 */
  group: string;
}

/** 인스턴스 연결 기본 scope */
export const DEFAULT_OAUTH_SCOPES = ["read", "write"];

/**
 * 공백으로 구분된 scope 문자열을 배열로 파싱한다.
 * @param raw DB·폼에 저장된 scope 문자열
 */
export function parseOAuthScopesString(raw: string): string[] {
  return raw
    .trim()
    .split(/\s+/)
    .filter((scope) => scope.length > 0);
}

/**
 * scope 배열을 Zendesk authorize 요청용 공백 구분 문자열로 직렬화한다.
 * @param scopes 선택된 scope 목록
 */
export function serializeOAuthScopes(scopes: string[]): string {
  return scopes.join(" ");
}

const GLOBAL_SCOPE_OPTIONS: ZendeskOAuthScopeOption[] = [
  {
    value: "read",
    group: "전역",
    label: "read — GET API(전체 리소스 읽기, sideload 포함)",
  },
  {
    value: "write",
    group: "전역",
    label: "write — POST·PUT·DELETE(전체 리소스 쓰기)",
  },
  {
    value: "impersonate",
    group: "전역",
    label: "impersonate — 관리자가 종료 사용자 대신 API 요청",
  },
];

/** 리소스별 scope 생성 규칙 */
const SCOPED_RESOURCES: Array<{
  key: string;
  label: string;
  read: boolean;
  write: boolean;
}> = [
  { key: "tickets", label: "티켓", read: true, write: true },
  { key: "users", label: "사용자", read: true, write: true },
  { key: "auditlogs", label: "감사 로그", read: true, write: false },
  { key: "organizations", label: "조직", read: true, write: true },
  { key: "hc", label: "Help Center", read: true, write: true },
  { key: "apps", label: "앱", read: true, write: true },
  { key: "triggers", label: "트리거", read: true, write: true },
  { key: "automations", label: "자동화", read: true, write: true },
  { key: "targets", label: "타겟", read: true, write: true },
  { key: "webhooks", label: "웹훅", read: true, write: true },
  { key: "macros", label: "매크로", read: true, write: true },
  { key: "requests", label: "요청", read: true, write: true },
  { key: "satisfaction_ratings", label: "만족도 평가", read: true, write: true },
  { key: "dynamic_content", label: "동적 콘텐츠", read: true, write: true },
  { key: "any_channel", label: "Any Channel", read: false, write: true },
  { key: "web_widget", label: "Web Widget", read: false, write: true },
  { key: "unrestricted", label: "unrestricted", read: true, write: true },
];

function buildResourceScopeOptions(): ZendeskOAuthScopeOption[] {
  const options: ZendeskOAuthScopeOption[] = [];
  for (const resource of SCOPED_RESOURCES) {
    if (resource.read) {
      options.push({
        value: `${resource.key}:read`,
        group: `리소스 — ${resource.label}`,
        label: `${resource.key}:read — ${resource.label} 읽기`,
      });
    }
    if (resource.write) {
      options.push({
        value: `${resource.key}:write`,
        group: `리소스 — ${resource.label}`,
        label: `${resource.key}:write — ${resource.label} 쓰기`,
      });
    }
  }
  return options;
}

/** 문서 기준 선택 가능한 전체 scope 옵션 */
export const ZENDESK_OAUTH_SCOPE_OPTIONS: ZendeskOAuthScopeOption[] = [
  ...GLOBAL_SCOPE_OPTIONS,
  ...buildResourceScopeOptions(),
];

/** value → 옵션 맵(라벨 표시용) */
export const ZENDESK_OAUTH_SCOPE_OPTION_BY_VALUE = new Map(
  ZENDESK_OAUTH_SCOPE_OPTIONS.map((option) => [option.value, option]),
);

/**
 * optgroup별로 묶은 scope 옵션 목록을 반환한다.
 */
export function groupZendeskOAuthScopeOptions(
  options: ZendeskOAuthScopeOption[],
): Array<{ group: string; options: ZendeskOAuthScopeOption[] }> {
  const order: string[] = [];
  const map = new Map<string, ZendeskOAuthScopeOption[]>();

  for (const option of options) {
    if (!map.has(option.group)) {
      map.set(option.group, []);
      order.push(option.group);
    }
    map.get(option.group)?.push(option);
  }

  return order.map((group) => ({
    group,
    options: map.get(group) ?? [],
  }));
}
