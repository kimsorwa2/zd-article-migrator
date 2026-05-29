import { parseApiErrorDetail } from "./parseApiError";

export type DuplicatePolicy = "skip" | "update" | "force";

export interface SourceBrand {
  a_brand_id: number;
  name: string;
  subdomain: string;
}

export interface Instance {
  id: number;
  name: string;
  subdomain: string;
  email: string;
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

export interface MigrateExecuteResponse {
  source_instance_id: number;
  target_instance_id: number;
  summary: {
    brands: number;
    categories: number;
    sections: number;
    articles: number;
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

const API_BASE = "/api";

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
    try {
      const payload: unknown = await response.json();
      detailMessage = parseApiErrorDetail(payload, fallback);
    } catch {
      detailMessage = fallback;
    }
    throw new Error(detailMessage);
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
  updateInstance: (instanceId: number, payload: { name: string; email: string; api_token?: string }) =>
    request<Instance>(`/instances/${instanceId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteInstance: (instanceId: number) =>
    request<void>(`/instances/${instanceId}`, {
      method: "DELETE",
    }),
  previewBrands: (payload: { subdomain: string; email: string; api_token: string }) =>
    request<SourceBrand[]>("/instances/brands/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createInstance: (payload: {
    name: string;
    subdomain: string;
    email: string;
    api_token: string;
    selected_brand_ids: number[];
  }) =>
    request<InstanceDetail>("/instances", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  /** @deprecated createInstance 사용 */
  createSourceInstance: (payload: {
    name: string;
    subdomain: string;
    email: string;
    api_token: string;
    selected_brand_ids: number[];
  }) =>
    request<InstanceDetail>("/instances/source", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  /** @deprecated createInstance 사용 */
  createTargetInstance: (payload: {
    name: string;
    subdomain: string;
    email: string;
    api_token: string;
  }) =>
    request<Instance>("/instances/target", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  syncInstance: (instanceId: number) =>
    request<FetchSyncStartResponse>(`/fetch/${instanceId}/sync`, {
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
};
