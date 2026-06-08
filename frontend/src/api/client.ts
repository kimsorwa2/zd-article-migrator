import { parseApiErrorDetail, parseApiErrorLogs } from "./parseApiError";
import type { WorkLogEntry } from "../components/WorkLogAccordion";

export type DuplicatePolicy = "skip" | "update" | "force";

export interface SourceBrand {
  id: number;
  a_brand_id: number;
  name: string;
  subdomain: string;
  has_help_center: boolean;
}

export interface Instance {
  id: number;
  name: string;
  subdomain: string;
  email: string;
  oauth_connected: boolean;
  oauth_client_configured: boolean;
  oauth_client_id: string;
  oauth_redirect_uri: string;
  oauth_scopes: string;
  role: string;
  is_active: boolean;
  last_fetched_at: string | null;
  created_at: string;
}

export interface InstanceDetail extends Instance {
  brands: SourceBrand[];
}

/** @deprecated InstanceDetail 사용 */
export type SourceInstance = InstanceDetail;

export interface SyncCounts {
  created: number;
  updated: number;
  deleted: number;
}

export interface FetchSyncResponse {
  instance_id: number;
  processed_brands: number;
  brand_summaries: Array<{
    brand_id: number;
    brand_name: string;
    categories: SyncCounts;
    sections: SyncCounts;
    articles: SyncCounts;
  }>;
}

export interface FetchSyncStartResponse {
  instance_id: number;
  status: string;
}

export interface FetchSyncWarning {
  timestamp: string;
  phase: string;
  brand_name: string;
  message: string;
}

export interface FetchSyncProgress {
  instance_id: number;
  status: "idle" | "running" | "completed" | "failed";
  percent: number;
  message: string;
  phase: string;
  brand_index: number;
  brand_total: number;
  brand_name: string | null;
  article_page: number;
  articles_collected: number;
  attachments_checked: number;
  attachments_total: number;
  error: string | null;
  result: FetchSyncResponse | null;
  warnings: FetchSyncWarning[];
}

export interface FetchDetailArticle {
  id: number;
  a_id: number;
  title: string;
  draft: boolean;
  html_url: string;
  has_attachments: boolean;
}

export interface FetchDetailSection {
  id: number;
  a_id: number;
  name: string;
  articles: FetchDetailArticle[];
  /** parent_section_id로 연결된 하위 섹션 */
  children?: FetchDetailSection[];
}

export interface FetchDetailCategory {
  id: number;
  a_id: number;
  name: string;
  sections: FetchDetailSection[];
}

export interface FetchDetailBrand {
  id: number;
  a_brand_id: number;
  name: string;
  subdomain: string;
  has_help_center: boolean;
  categories: FetchDetailCategory[];
}

export interface FetchDetailResponse {
  instance_id: number;
  instance_name: string;
  last_fetched_at: string | null;
  summary: {
    total_brands: number;
    total_categories: number;
    total_sections: number;
    total_articles: number;
  };
  brands: FetchDetailBrand[];
}

/** 마이그레이션으로 생성·DB에 저장된 타겟 트리(재수집 없이 조회) */
export interface MigrateTargetTreeResponse extends FetchDetailResponse {
  source_instance_id: number;
  target_instance_id: number;
  mapping_record_count: number;
}

export interface MigrateClearMappingsResponse {
  source_instance_id: number;
  target_instance_id: number;
  deleted_count: number;
}

export interface MigrateExecuteResponse {
  source_instance_id: number;
  target_instance_id: number;
  summary: {
    brands: number;
    categories: number;
    sections: number;
    articles: number;
    scope_categories?: number;
    scope_sections?: number;
    scope_articles?: number;
  };
}

export interface MigrateExecuteStartResponse {
  source_instance_id: number;
  target_instance_id: number;
  status: string;
}

export interface MigrateProgress {
  source_instance_id: number;
  target_instance_id: number;
  status: "idle" | "running" | "completed" | "failed";
  percent: number;
  message: string;
  phase: string;
  current_step: number;
  total_steps: number;
  error: string | null;
  result: MigrateExecuteResponse | null;
  logs: string[];
}

export interface MigrateOverlayItem {
  mapping_id: number;
  mapping_entity_type: string;
  source_a_id: number;
  target_a_id: number;
  status: string;
  error_message?: string | null;
}

export interface MigrateOverlayResponse {
  source_instance_id: number;
  target_instance_id: number;
  items: MigrateOverlayItem[];
  migrated_target_category_a_ids: number[];
  migrated_target_section_a_ids: number[];
  migrated_target_article_a_ids: number[];
  delete_error_target_category_a_ids: number[];
  delete_error_target_section_a_ids: number[];
  delete_error_target_article_a_ids: number[];
  delete_error_items: MigrateOverlayItem[];
}

export interface MigrateTreeNodeArticle {
  id: number;
  a_id: number;
  title: string;
  status: string;
}

export interface MigrateTreeNodeSection {
  id: number;
  a_id: number;
  name: string;
  status: string;
  articles: MigrateTreeNodeArticle[];
}

export interface MigrateTreeNodeCategory {
  id: number;
  a_id: number;
  name: string;
  status: string;
  sections: MigrateTreeNodeSection[];
}

export interface MigrateTreeNodeBrand {
  id: number;
  a_brand_id: number;
  name: string;
  status: string;
  categories: MigrateTreeNodeCategory[];
}

export interface MigrateTreeResponse {
  source_instance_id: number;
  target_instance_id: number;
  brands: MigrateTreeNodeBrand[];
}

export interface DeleteFailedItem {
  mapping_id: number;
  entity_type: string;
  target_a_id: number;
  error_message: string;
}

export type AiOcrProvider = "gemini" | "openai" | "bedrock";

/** AI 연동 연결 테스트 API 응답 */
export interface AiOcrConnectionTestResult {
  success: boolean;
  message: string;
  provider: AiOcrProvider;
  model: string;
  latency_ms: number | null;
}

export interface AiOcrConnection {
  id: number;
  provider: AiOcrProvider;
  model: string;
  account: string | null;
  has_api_key: boolean;
  api_key_masked: string | null;
  has_api_secret: boolean;
  api_secret_masked: string | null;
  aws_region: string | null;
  label: string;
  is_active: boolean;
  prompt_template_id: number | null;
  prompt_template_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AiOcrProviderConfig {
  account: string | null;
  has_api_key: boolean;
  api_key_masked: string | null;
  model: string;
}

export interface AiOcrPromptTemplate {
  id: number;
  name: string;
  description: string | null;
  system_prompt: string;
  user_prompt: string;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface AiOcrSettings {
  active_provider: AiOcrProvider;
  active_connection_id: number | null;
  active_prompt_id: number | null;
  connections: AiOcrConnection[];
  gemini: AiOcrProviderConfig;
  openai: AiOcrProviderConfig;
  prompt_templates: AiOcrPromptTemplate[];
  default_system_prompt: string;
  default_user_prompt: string;
}

export interface AiOcrAnalyzeResult {
  history_id: number;
  title: string;
  html_body: string;
  label_names: string[];
  detected_product: string;
  maintenance_cycle: string | null;
  body_preview_text: string;
  logs: WorkLogEntry[];
}

export interface AiOcrAnalysisHistoryItem {
  id: number;
  label: string;
  display_label?: string | null;
  ai_model?: string | null;
  source_filename: string;
  title: string;
  html_body: string;
  label_names: string[];
  detected_product: string;
  maintenance_cycle: string | null;
  body_preview_text: string;
  prompt_template_id?: number | null;
  image_size_kb?: number | null;
  preprocessed?: boolean | null;
  processed_image_size_kb?: number | null;
  latency_ms?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  thinking_tokens?: number | null;
  total_tokens?: number | null;
  finish_reason?: string | null;
  parse_success?: boolean | null;
  experiment_tag?: string | null;
  raw_response_text?: string | null;
  parse_error_message?: string | null;
  used_system_prompt?: string | null;
  used_user_prompt?: string | null;
  created_at: string;
}

export interface AiOcrCreateArticleResult {
  article_id: number;
  html_url: string | null;
  section_a_id: number;
  section_name: string;
  logs: WorkLogEntry[];
}

export interface AiOcrSectionSelection {
  brandId: number;
  brandName: string;
  categoryAId: number;
  categoryName: string;
  sectionAId: number;
  sectionName: string;
}

export interface ImageConvertArticleItem {
  id: number;
  a_id: number;
  title: string;
  html_url: string | null;
  section_name: string;
  image_count: number;
  label_names: string[];
}

export interface ImageConvertArticleDetail {
  id: number;
  a_id: number;
  title: string;
  html_url: string | null;
  section_name: string;
  label_names: string[];
  body: string | null;
  images: Array<{
    index: number;
    source_url: string;
    filename: string;
    availability: "ok" | "external_paste" | "unknown";
    availability_reason: string | null;
  }>;
  brand_subdomain: string;
}

export interface ImageConvertAnalyzeResult {
  history_id: number;
  source_article_id: number;
  source_article_a_id: number;
  source_article_title: string;
  title: string;
  html_body: string;
  label_names: string[];
  detected_product: string;
  maintenance_cycle: string | null;
  body_preview_text: string;
  image_count: number;
  ocr_image_count: number;
  image_previews: Array<{
    index: number;
    filename: string;
    preview_data_url: string;
  }>;
  logs: WorkLogEntry[];
}

export interface DeleteExecuteResponse {
  source_instance_id: number;
  target_instance_id: number;
  summary: {
    categories: number;
    sections: number;
    articles: number;
  };
  failed_items: DeleteFailedItem[];
}

export interface ZendeskApiOperation {
  id: string;
  category: string;
  group: string;
  label: string;
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path_template: string;
  path_params: string[];
  doc_url: string;
  sample_body?: Record<string, unknown> | null;
  default_query?: Record<string, string> | null;
}

export interface ZendeskApiGroup {
  id: string;
  label: string;
  operations: ZendeskApiOperation[];
}

export interface ZendeskApiCategory {
  id: string;
  label: string;
  groups: ZendeskApiGroup[];
}

export interface ZendeskApiProduct {
  id: string;
  label: string;
  doc_url: string;
  categories: ZendeskApiCategory[];
}

export interface ZendeskApiCatalog {
  products: ZendeskApiProduct[];
}

/** @deprecated ZendeskApiOperation 사용 */
export type ZendeskTicketingApiOperation = ZendeskApiOperation;
/** @deprecated ZendeskApiGroup 사용 */
export type ZendeskTicketingApiGroup = ZendeskApiGroup;
/** @deprecated ZendeskApiCategory 사용 */
export type ZendeskTicketingApiCategory = ZendeskApiCategory;
/** @deprecated ZendeskApiCatalog 사용 */
export type ZendeskTicketingApiCatalog = ZendeskApiCatalog;

export interface ZendeskProxyRequest {
  instance_id: number;
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  json_body?: Record<string, unknown> | null;
  raw_body?: string | null;
  query_params?: Record<string, string> | null;
  request_headers?: Record<string, string> | null;
}

export interface ZendeskProxyResponse {
  success: boolean;
  http_status: number;
  latency_ms: number;
  request_url: string;
  response_body: unknown;
  response_headers: Record<string, string>;
  error_message: string | null;
}

const API_BASE =
  (import.meta as unknown as { env: { VITE_API_BASE_URL?: string } }).env
    ?.VITE_API_BASE_URL ?? "/api";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const fallback = `요청 실패: ${response.status}`;
    let detailMessage = fallback;
    let logs: WorkLogEntry[] = [];
    try {
      const payload: unknown = await response.json();
      detailMessage = parseApiErrorDetail(payload, fallback);
      logs = parseApiErrorLogs(payload);
    } catch {
      detailMessage = fallback;
    }
    const error = new Error(detailMessage) as Error & { logs?: WorkLogEntry[] };
    if (logs.length > 0) {
      error.logs = logs;
    }
    throw error;
  }

  if (response.status === 204) {
    return {} as T;
  }
  return (await response.json()) as T;
}

export const apiClient = {
  listInstances: () => request<Instance[]>("/instances"),
  getInstance: (instanceId: number) => request<InstanceDetail>(`/instances/${instanceId}`),
  testConnection: (instanceId: number) =>
    request<{ success: boolean; message: string }>(`/instances/${instanceId}/connection-test`, {
      method: "POST",
    }),
  setActive: (instanceId: number, isActive: boolean) =>
    request<Instance>(`/instances/${instanceId}/active`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),
  updateInstance: (instanceId: number, payload: {
    name?: string;
    email?: string;
    oauth_client_id?: string;
    oauth_client_secret?: string;
    oauth_scopes?: string;
  }) =>
    request<Instance>(`/instances/${instanceId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  connectOAuth: (payload: {
    subdomain: string;
    oauth_client_id: string;
    oauth_client_secret: string;
    oauth_scopes?: string;
    name?: string;
    instance_id?: number;
    selected_brand_ids?: number[];
  }) =>
    request<InstanceDetail>("/instances/oauth/connect", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteInstance: (instanceId: number) =>
    request<void>(`/instances/${instanceId}`, {
      method: "DELETE",
    }),
  previewBrands: (payload: { instance_id: number }) =>
    request<SourceBrand[]>("/instances/brands/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  syncInstance: (instanceId: number) =>
    request<FetchSyncStartResponse>(`/fetch/${instanceId}/sync`, {
      method: "POST",
    }),
  /** 선택한 브랜드 한 개만 Help Center 수집 */
  syncInstanceBrand: (instanceId: number, brandId: number) =>
    request<FetchSyncStartResponse>(`/fetch/${instanceId}/brands/${brandId}/sync`, {
      method: "POST",
    }),
  getSyncProgress: (instanceId: number) => request<FetchSyncProgress>(`/fetch/${instanceId}/sync/progress`),
  /** @deprecated syncInstance 사용 */
  syncSource: (instanceId: number) =>
    request<FetchSyncResponse>(`/fetch/${instanceId}/sync`, {
      method: "POST",
    }),
  getFetchDetail: (instanceId: number) => request<FetchDetailResponse>(`/fetch/${instanceId}/detail`),
  migrateExecute: (payload: {
    source_instance_id: number;
    target_instance_id: number;
    target_brand_id?: number | null;
    duplicate_policy: DuplicatePolicy;
    brand_ids: number[];
    category_ids: number[];
    section_ids: number[];
    article_ids: number[];
  }) =>
    request<MigrateExecuteStartResponse>("/migrate/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getMigrateProgress: (sourceInstanceId: number, targetInstanceId: number) =>
    request<MigrateProgress>(
      `/migrate/progress?source_instance_id=${sourceInstanceId}&target_instance_id=${targetInstanceId}`,
    ),
  getMigrateOverlay: (sourceInstanceId: number, targetInstanceId: number) =>
    request<MigrateOverlayResponse>(
      `/migrate/overlay?source_instance_id=${sourceInstanceId}&target_instance_id=${targetInstanceId}`,
    ),
  clearMigrateMappings: (sourceInstanceId: number, targetInstanceId: number) =>
    request<MigrateClearMappingsResponse>(
      `/migrate/mappings?source_instance_id=${sourceInstanceId}&target_instance_id=${targetInstanceId}`,
      { method: "DELETE" },
    ),
  getMigrateTargetTree: (
    sourceInstanceId: number,
    targetInstanceId: number,
    targetBrandId?: number | null,
  ) => {
    const brandQuery =
      targetBrandId !== undefined && targetBrandId !== null && targetBrandId > 0
        ? `&target_brand_id=${targetBrandId}`
        : "";
    return request<MigrateTargetTreeResponse>(
      `/migrate/target-tree?source_instance_id=${sourceInstanceId}&target_instance_id=${targetInstanceId}${brandQuery}`,
    );
  },
  getMigrateTree: (sourceInstanceId: number, targetInstanceId: number) =>
    request<MigrateTreeResponse>(`/migrate/tree?source_instance_id=${sourceInstanceId}&target_instance_id=${targetInstanceId}`),
  deletePreview: (payload: {
    source_instance_id: number;
    target_instance_id: number;
    target_brand_id?: number | null;
    brand_a_ids?: number[];
    category_a_ids?: number[];
    section_a_ids?: number[];
    article_a_ids?: number[];
    target_category_a_ids?: number[];
    target_section_a_ids?: number[];
    target_article_a_ids?: number[];
  }) =>
    request<DeleteExecuteResponse>("/delete/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteExecute: (payload: {
    source_instance_id: number;
    target_instance_id: number;
    target_brand_id?: number | null;
    brand_a_ids?: number[];
    category_a_ids?: number[];
    section_a_ids?: number[];
    article_a_ids?: number[];
    target_category_a_ids?: number[];
    target_section_a_ids?: number[];
    target_article_a_ids?: number[];
  }) =>
    request<DeleteExecuteResponse>("/delete/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAiOcrSettings: () => request<AiOcrSettings>("/ai-ocr/settings"),
  getAiOcrHistory: () =>
    request<{ items: AiOcrAnalysisHistoryItem[] }>("/ai-ocr/history"),
  listAiOcrHistoryMetrics: (limit = 100) =>
    request<{ items: AiOcrAnalysisHistoryItem[] }>(
      `/ai-ocr/history/metrics?limit=${encodeURIComponent(String(limit))}`,
    ),
  deleteAiOcrHistory: (ids: number[]) =>
    request<{ deleted_count: number }>("/ai-ocr/history", {
      method: "DELETE",
      body: JSON.stringify({ ids }),
    }),
  updateAiOcrSettings: (payload: {
    active_provider?: AiOcrProvider;
    active_connection_id?: number | null;
    active_prompt_id?: number | null;
    gemini_account?: string | null;
    gemini_api_key?: string | null;
    gemini_model?: string | null;
    openai_account?: string | null;
    openai_api_key?: string | null;
    openai_model?: string | null;
  }) =>
    request<AiOcrSettings>("/ai-ocr/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  createAiOcrConnection: (payload: {
    provider: AiOcrProvider;
    model: string;
    account?: string | null;
    api_key?: string | null;
    api_secret?: string | null;
    aws_region?: string | null;
    prompt_template_id?: number | null;
    set_active?: boolean;
  }) =>
    request<AiOcrConnection>("/ai-ocr/connections", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateAiOcrConnection: (
    connectionId: number,
    payload: {
      model?: string;
      account?: string | null;
      api_key?: string | null;
      api_secret?: string | null;
      aws_region?: string | null;
      prompt_template_id?: number | null;
    },
  ) =>
    request<AiOcrConnection>(`/ai-ocr/connections/${connectionId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteAiOcrConnection: (connectionId: number) =>
    request<void>(`/ai-ocr/connections/${connectionId}`, { method: "DELETE" }),
  activateAiOcrConnection: (connectionId: number) =>
    request<AiOcrSettings>(`/ai-ocr/connections/${connectionId}/activate`, {
      method: "PUT",
    }),
  testAiOcrConnection: (connectionId: number) =>
    request<AiOcrConnectionTestResult>(`/ai-ocr/connections/${connectionId}/test`, {
      method: "POST",
    }),
  createAiOcrPrompt: (payload: {
    name: string;
    description?: string | null;
    system_prompt: string;
    user_prompt: string;
    set_active?: boolean;
  }) =>
    request<AiOcrPromptTemplate>("/ai-ocr/prompts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateAiOcrPrompt: (
    templateId: number,
    payload: {
      name?: string;
      description?: string | null;
      system_prompt?: string;
      user_prompt?: string;
    },
  ) =>
    request<AiOcrPromptTemplate>(`/ai-ocr/prompts/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteAiOcrPrompt: (templateId: number) =>
    request<void>(`/ai-ocr/prompts/${templateId}`, { method: "DELETE" }),
  listImageConvertArticles: (sourceInstanceId: number, query?: string) => {
    const params = new URLSearchParams({ source_instance_id: String(sourceInstanceId) });
    if (query?.trim()) {
      params.set("q", query.trim());
    }
    return request<{ items: ImageConvertArticleItem[] }>(`/image-convert/articles?${params.toString()}`);
  },
  getImageConvertArticleDetail: (sourceInstanceId: number, articleId: number) => {
    const params = new URLSearchParams({ source_instance_id: String(sourceInstanceId) });
    return request<ImageConvertArticleDetail>(`/image-convert/articles/${articleId}?${params.toString()}`);
  },
  getImageConvertPreviewUrl: (sourceInstanceId: number, articleId: number, imageIndex: number) =>
    `${API_BASE}/image-convert/articles/${articleId}/images/${imageIndex}?source_instance_id=${sourceInstanceId}`,
  analyzeImageConvertArticle: (payload: {
    source_instance_id: number;
    article_id: number;
    preprocess?: boolean;
  }) => {
    const params = new URLSearchParams();
    if (payload.preprocess === false) {
      params.set("preprocess", "false");
    }
    const query = params.toString();
    return request<ImageConvertAnalyzeResult>(
      `/image-convert/analyze${query ? `?${query}` : ""}`,
      {
        method: "POST",
        body: JSON.stringify({
          source_instance_id: payload.source_instance_id,
          article_id: payload.article_id,
        }),
      },
    );
  },
  analyzeImageConvertArticleWithFiles: async (payload: {
    source_instance_id: number;
    article_id: number;
    image_indices: number[];
    files: File[];
    preprocess?: boolean;
  }): Promise<ImageConvertAnalyzeResult> => {
    const formData = new FormData();
    formData.append("source_instance_id", String(payload.source_instance_id));
    formData.append("article_id", String(payload.article_id));
    formData.append("image_indices", payload.image_indices.join(","));
    for (const file of payload.files) {
      formData.append("files", file);
    }
    const params = new URLSearchParams();
    if (payload.preprocess === false) {
      params.set("preprocess", "false");
    }
    const query = params.toString();
    const response = await fetch(
      `${API_BASE}/image-convert/analyze-with-files${query ? `?${query}` : ""}`,
      {
        method: "POST",
        body: formData,
      },
    );
    if (!response.ok) {
      const fallback = `요청 실패: ${response.status}`;
      let detailMessage = fallback;
      let logs: WorkLogEntry[] = [];
      try {
        const payload: unknown = await response.json();
        detailMessage = parseApiErrorDetail(payload, fallback);
        logs = parseApiErrorLogs(payload);
      } catch {
        detailMessage = fallback;
      }
      const error = new Error(detailMessage) as Error & { logs?: WorkLogEntry[] };
      if (logs.length > 0) {
        error.logs = logs;
      }
      throw error;
    }
    return (await response.json()) as ImageConvertAnalyzeResult;
  },
  analyzeAiOcrImage: async (file: File, preprocess = true): Promise<AiOcrAnalyzeResult> => {
    const formData = new FormData();
    formData.append("file", file);
    const params = new URLSearchParams();
    if (!preprocess) {
      params.set("preprocess", "false");
    }
    const query = params.toString();
    const response = await fetch(`${API_BASE}/ai-ocr/analyze${query ? `?${query}` : ""}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const fallback = `요청 실패: ${response.status}`;
      let detailMessage = fallback;
      let logs: WorkLogEntry[] = [];
      try {
        const payload: unknown = await response.json();
        detailMessage = parseApiErrorDetail(payload, fallback);
        logs = parseApiErrorLogs(payload);
      } catch {
        detailMessage = fallback;
      }
      const error = new Error(detailMessage) as Error & { logs?: WorkLogEntry[] };
      error.logs = logs;
      throw error;
    }
    return (await response.json()) as AiOcrAnalyzeResult;
  },
  createAiOcrArticle: (payload: {
    instance_id: number;
    brand_id: number;
    section_a_id: number;
    title: string;
    html_body: string;
    label_names: string[];
    locale?: string;
    draft?: boolean;
  }) =>
    request<AiOcrCreateArticleResult>("/ai-ocr/create-article", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteRetry: (payload: {
    source_instance_id: number;
    target_instance_id: number;
    target_brand_id?: number | null;
    mapping_ids?: number[];
  }) =>
    request<DeleteExecuteResponse>("/delete/retry", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  fetchZendeskApiCatalog: () => request<ZendeskApiCatalog>("/zendesk-proxy/catalog"),
  /** @deprecated fetchZendeskApiCatalog 사용 */
  fetchZendeskTicketingApiCatalog: () => request<ZendeskApiCatalog>("/zendesk-proxy/catalog"),
  zendeskProxyRequest: (payload: ZendeskProxyRequest) =>
    request<ZendeskProxyResponse>("/zendesk-proxy/request", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
