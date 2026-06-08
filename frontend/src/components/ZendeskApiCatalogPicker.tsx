import { useEffect, useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";
import type { ZendeskApiCatalog, ZendeskApiOperation, ZendeskApiProduct } from "../api/client";

export interface CatalogSelectionState {
  method: ZendeskApiOperation["method"];
  pathTemplate: string;
  pathParamNames: string[];
  jsonBodyText: string;
  queryText: string;
  docUrl: string | null;
}

interface ZendeskApiCatalogPickerProps {
  catalog: ZendeskApiCatalog | null;
  disabled?: boolean;
  defaultOperationId?: string;
  onSelectionChange: (state: CatalogSelectionState) => void;
}

/** 초기 화면 기본 API operation id */
export const DEFAULT_CATALOG_OPERATION_ID = "tickets.show";

/** Show Ticket path template (초기 endpoint 기준) */
export const DEFAULT_SHOW_TICKET_PATH_TEMPLATE = "/api/v2/tickets/{ticket_id}.json";

/**
 * path template의 placeholder를 사용자 입력값으로 치환한다.
 * 값이 비어 있으면 `{param}` 형태를 유지한다.
 */
export function resolvePathTemplate(template: string, values: Record<string, string>): string {
  return template.replace(/\{([^}]+)\}/g, (_, key: string) => {
    const value = values[key];
    if (value === undefined || value.trim() === "") {
      return `{${key}}`;
    }
    return value;
  });
}

/**
 * path 문자열에서 template placeholder에 해당하는 값을 추출한다.
 * @param template /api/v2/tickets/{ticket_id}.json 형태
 * @param path 실제 path 입력값
 * @returns 추출된 path parameter map (매칭 실패 시 빈 객체)
 */
export function parsePathTemplateValues(template: string, path: string): Record<string, string> {
  const values: Record<string, string> = {};
  const parts: Array<{ type: "literal" | "param"; value: string }> = [];
  const placeholderPattern = /\{([^}]+)\}/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null = placeholderPattern.exec(template);

  while (match) {
    if (match.index > lastIndex) {
      parts.push({ type: "literal", value: template.slice(lastIndex, match.index) });
    }
    parts.push({ type: "param", value: match[1] });
    lastIndex = placeholderPattern.lastIndex;
    match = placeholderPattern.exec(template);
  }

  if (lastIndex < template.length) {
    parts.push({ type: "literal", value: template.slice(lastIndex) });
  }

  let regexSource = "^";
  const paramNames: string[] = [];
  for (const part of parts) {
    if (part.type === "literal") {
      regexSource += part.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      continue;
    }
    regexSource += "([^/]+)";
    paramNames.push(part.value);
  }
  regexSource += "$";

  const matched = new RegExp(regexSource).exec(path.trim());
  if (!matched) {
    return values;
  }

  for (const [index, name] of paramNames.entries()) {
    const captured = matched[index + 1] ?? "";
    values[name] = captured === `{${name}}` ? "" : captured;
  }
  return values;
}

/**
 * default_query 객체를 key=value& 형태 문자열로 변환한다.
 */
function queryObjectToText(query: Record<string, string> | null | undefined): string {
  if (!query) {
    return "";
  }
  return Object.entries(query)
    .map(([key, value]) => `${key}=${value}`)
    .join("&");
}

/**
 * operation id로 소속 product를 찾는다.
 */
function findProductForOperation(
  catalog: ZendeskApiCatalog,
  operationId: string,
): ZendeskApiProduct | null {
  for (const product of catalog.products) {
    for (const category of product.categories) {
      for (const group of category.groups) {
        if (group.operations.some((operation) => operation.id === operationId)) {
          return product;
        }
      }
    }
  }
  return null;
}

/**
 * operation id로 카탈로그 계층·operation을 찾는다.
 */
function findOperationContext(
  catalog: ZendeskApiCatalog,
  operationId: string,
): {
  operation: ZendeskApiOperation;
  productId: string;
  categoryId: string;
  groupId: string;
} | null {
  for (const product of catalog.products) {
    for (const category of product.categories) {
      for (const group of category.groups) {
        const operation = group.operations.find((item) => item.id === operationId);
        if (operation) {
          return {
            operation,
            productId: product.id,
            categoryId: category.id,
            groupId: group.id,
          };
        }
      }
    }
  }
  return null;
}

/**
 * Zendesk API 문서 구조 기반 4단 카탈로그 선택기.
 */
export default function ZendeskApiCatalogPicker({
  catalog,
  disabled = false,
  defaultOperationId = DEFAULT_CATALOG_OPERATION_ID,
  onSelectionChange,
}: ZendeskApiCatalogPickerProps) {
  const [productId, setProductId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [operationId, setOperationId] = useState("");
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    if (!catalog || catalog.products.length === 0 || operationId) {
      return;
    }

    const context = findOperationContext(catalog, defaultOperationId);
    if (!context) {
      setProductId(catalog.products[0]?.id ?? "");
      return;
    }

    setProductId(context.productId);
    setCategoryId(context.categoryId);
    setGroupId(context.groupId);
    setOperationId(context.operation.id);
    onSelectionChange({
      method: context.operation.method,
      pathTemplate: context.operation.path_template,
      pathParamNames: [...context.operation.path_params],
      jsonBodyText: context.operation.sample_body
        ? JSON.stringify(context.operation.sample_body, null, 2)
        : "",
      queryText: queryObjectToText(context.operation.default_query),
      docUrl: context.operation.doc_url,
    });
  }, [catalog, defaultOperationId, operationId, onSelectionChange]);

  const selectedProduct = catalog?.products.find((item) => item.id === productId) ?? null;
  const selectedCategory = selectedProduct?.categories.find((item) => item.id === categoryId) ?? null;
  const selectedGroup = selectedCategory?.groups.find((item) => item.id === groupId) ?? null;

  const flatOperations = useMemo(() => {
    if (!catalog) {
      return [] as ZendeskApiOperation[];
    }
    const sourceProducts = selectedProduct ? [selectedProduct] : catalog.products;
    return sourceProducts.flatMap((product) =>
      product.categories.flatMap((category) => category.groups.flatMap((group) => group.operations)),
    );
  }, [catalog, selectedProduct]);

  const searchResults = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) {
      return [];
    }
    return flatOperations.filter((operation) => {
      const productLabel =
        catalog && selectedProduct
          ? selectedProduct.label
          : findProductForOperation(catalog!, operation.id)?.label ?? "";
      const haystack = [
        productLabel,
        operation.label,
        operation.path_template,
        operation.group,
        operation.category,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(keyword);
    });
  }, [flatOperations, searchText, catalog, selectedProduct]);

  function emitSelection(operation: ZendeskApiOperation) {
    onSelectionChange({
      method: operation.method,
      pathTemplate: operation.path_template,
      pathParamNames: [...operation.path_params],
      jsonBodyText: operation.sample_body ? JSON.stringify(operation.sample_body, null, 2) : "",
      queryText: queryObjectToText(operation.default_query),
      docUrl: operation.doc_url,
    });
  }

  function applyOperation(operation: ZendeskApiOperation) {
    if (!catalog) {
      return;
    }
    const context = findOperationContext(catalog, operation.id);
    const product =
      (context ? catalog.products.find((item) => item.id === context.productId) : null) ??
      selectedProduct ??
      findProductForOperation(catalog, operation.id) ??
      catalog.products[0] ??
      null;
    const category = product?.categories.find((item) => item.label === operation.category);
    const group = category?.groups.find((item) => item.label === operation.group);
    if (product) {
      setProductId(product.id);
    }
    if (category) {
      setCategoryId(category.id);
    }
    if (group) {
      setGroupId(group.id);
    }
    setOperationId(operation.id);
    emitSelection(operation);
    setSearchText("");
  }

  function handleProductChange(nextProductId: string) {
    setProductId(nextProductId);
    setCategoryId("");
    setGroupId("");
    setOperationId("");
  }

  function handleCategoryChange(nextCategoryId: string) {
    setCategoryId(nextCategoryId);
    setGroupId("");
    setOperationId("");
  }

  function handleGroupChange(nextGroupId: string) {
    setGroupId(nextGroupId);
    setOperationId("");
  }

  function handleOperationChange(nextOperationId: string) {
    const operation = selectedGroup?.operations.find((item) => item.id === nextOperationId);
    setOperationId(nextOperationId);
    if (!operation) {
      return;
    }
    emitSelection(operation);
  }

  if (!catalog) {
    return (
      <p className="muted api-request-catalog-fallback">
        API 카탈로그를 불러오지 못했습니다. 아래에서 method·path를 직접 입력할 수 있습니다.
      </p>
    );
  }

  return (
    <div className="api-request-catalog">
      <div className="api-request-catalog-product-row">
        <label className="api-request-catalog-field api-request-catalog-product-field">
          <span className="api-request-catalog-field-label">빠르게 찾기</span>
          <select
            value={productId}
            disabled={disabled}
            onChange={(event) => handleProductChange(event.target.value)}
          >
            <option value="">선택…</option>
            {catalog.products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.label}
              </option>
            ))}
          </select>
        </label>

        {selectedProduct?.doc_url ? (
          <a
            className="button-ghost api-request-doc-link"
            href={selectedProduct.doc_url}
            target="_blank"
            rel="noreferrer"
          >
            API 소개 문서
            <ExternalLink size={14} aria-hidden="true" />
          </a>
        ) : (
          <button type="button" className="button-ghost api-request-doc-link" disabled>
            API 소개 문서
            <ExternalLink size={14} aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="api-request-catalog-toolbar">
        <label className="api-request-catalog-field">
          <span className="api-request-catalog-field-label">대분류</span>
          <select
            value={categoryId}
            disabled={disabled || !selectedProduct}
            onChange={(event) => handleCategoryChange(event.target.value)}
          >
            <option value="">선택…</option>
            {(selectedProduct?.categories ?? []).map((category) => (
              <option key={category.id} value={category.id}>
                {category.label}
              </option>
            ))}
          </select>
        </label>

        <label className="api-request-catalog-field">
          <span className="api-request-catalog-field-label">중분류</span>
          <select
            value={groupId}
            disabled={disabled || !selectedCategory}
            onChange={(event) => handleGroupChange(event.target.value)}
          >
            <option value="">선택…</option>
            {(selectedCategory?.groups ?? []).map((group) => (
              <option key={group.id} value={group.id}>
                {group.label}
              </option>
            ))}
          </select>
        </label>

        <label className="api-request-catalog-field">
          <span className="api-request-catalog-field-label">API</span>
          <select
            value={operationId}
            disabled={disabled || !selectedGroup}
            onChange={(event) => handleOperationChange(event.target.value)}
          >
            <option value="">선택…</option>
            {(selectedGroup?.operations ?? []).map((operation) => (
              <option key={operation.id} value={operation.id}>
                {operation.method} · {operation.label}
              </option>
            ))}
          </select>
        </label>

        <label className="api-request-catalog-field api-request-catalog-search">
          <span className="api-request-catalog-field-label">API 검색</span>
          <input
            type="search"
            placeholder="label, path, 그룹…"
            value={searchText}
            disabled={disabled}
            onChange={(event) => setSearchText(event.target.value)}
          />
        </label>
      </div>

      {searchResults.length > 0 ? (
        <ul className="api-request-search-results">
          {searchResults.slice(0, 12).map((operation) => {
            const productLabel =
              selectedProduct?.label ??
              (catalog ? findProductForOperation(catalog, operation.id)?.label : "") ??
              "";
            return (
              <li key={operation.id}>
                <button
                  type="button"
                  className="api-request-search-item"
                  disabled={disabled}
                  onClick={() => applyOperation(operation)}
                >
                  <strong>{operation.label}</strong>
                  <span className="muted">
                    {productLabel} · {operation.category} · {operation.group} · {operation.method}{" "}
                    {operation.path_template}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

/** path placeholder가 모두 채워졌는지 검사한다. */
export function arePathParamsFilled(pathTemplate: string, values: Record<string, string>): boolean {
  const matches = pathTemplate.match(/\{([^}]+)\}/g) ?? [];
  return matches.every((token) => {
    const key = token.slice(1, -1);
    return (values[key] ?? "").trim().length > 0;
  });
}
