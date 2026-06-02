import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, ExternalLink, FileText, Folder, Layers, Paperclip, RotateCcw, Store, Trash2 } from "lucide-react";
import type { FetchDetailBrand, FetchDetailCategory, FetchDetailSection, MigrateOverlayResponse } from "../api/client";
import { countBrandArticles, countBrandSections, countCategoryArticles } from "../utils/fetchTreeUtils";
import { NestedSectionTreeNodes, countSectionsForCategory } from "./NestedSectionTreeNodes";

interface TargetMigratedTreeProps {
  title: string;
  brands: FetchDetailBrand[];
  overlay: MigrateOverlayResponse | null;
  selectedCategoryAIds: number[];
  selectedSectionAIds: number[];
  isDeleting: boolean;
  isMigrateRunning?: boolean;
  onBulkDeleteSelected: () => void;
  onToggleCategory: (targetAId: number, checked: boolean) => void;
  onToggleSection: (targetAId: number, checked: boolean) => void;
  onDeleteCategory: (targetAId: number) => void;
  onDeleteSection: (targetAId: number) => void;
  onDeleteArticle: (targetAId: number) => void;
  onRetryDeleteAll: () => void;
  onRetryDeleteMapping: (mappingId: number) => void;
}

type TreeNodeKey = string;
type OverlayNodeStatus = "migrated" | "delete_error";

/**
 * migrated·delete_error 오버레이 Set을 만든다.
 */
function buildOverlaySets(overlay: MigrateOverlayResponse | null) {
  return {
    migrated: {
      categories: new Set(overlay?.migrated_target_category_a_ids ?? []),
      sections: new Set(overlay?.migrated_target_section_a_ids ?? []),
      articles: new Set(overlay?.migrated_target_article_a_ids ?? []),
    },
    deleteError: {
      categories: new Set(overlay?.delete_error_target_category_a_ids ?? []),
      sections: new Set(overlay?.delete_error_target_section_a_ids ?? []),
      articles: new Set(overlay?.delete_error_target_article_a_ids ?? []),
    },
    errorByTargetAId: new Map(
      (overlay?.delete_error_items ?? []).map((item) => [item.target_a_id, item] as const),
    ),
  };
}

/**
 * 카테고리·섹션·아티클의 오버레이 상태를 반환한다.
 */
function resolveNodeStatus(
  sets: ReturnType<typeof buildOverlaySets>,
  kind: "categories" | "sections" | "articles",
  targetAId: number,
): OverlayNodeStatus | undefined {
  if (sets.deleteError[kind].has(targetAId)) {
    return "delete_error";
  }
  if (sets.migrated[kind].has(targetAId)) {
    return "migrated";
  }
  return undefined;
}

interface MigratedTreeRowProps {
  checked?: boolean;
  showCheckbox: boolean;
  showDelete: boolean;
  showRetry: boolean;
  nodeStatus?: OverlayNodeStatus;
  errorHint?: string;
  label: string;
  level: number;
  nodeKey: TreeNodeKey;
  hasChildren: boolean;
  isExpanded: boolean;
  icon: ReactNode;
  countLabel?: string;
  meta?: ReactNode;
  isDeleting: boolean;
  onExpandToggle: (nodeKey: TreeNodeKey) => void;
  onCheckChange?: (checked: boolean) => void;
  onDelete?: () => void;
  onRetry?: () => void;
}

/**
 * 타겟 트리 행(체크박스·삭제·migrated 강조).
 */
function MigratedTreeRow({
  checked = false,
  showCheckbox,
  showDelete,
  showRetry,
  nodeStatus,
  errorHint,
  label,
  level,
  nodeKey,
  hasChildren,
  isExpanded,
  icon,
  countLabel,
  meta,
  isDeleting,
  onExpandToggle,
  onCheckChange,
  onDelete,
  onRetry,
}: MigratedTreeRowProps) {
  const rowClass =
    nodeStatus === "delete_error" ? " tree-row-delete-error" : nodeStatus === "migrated" ? " tree-row-migrated" : "";

  return (
    <div className={`tree-select-row tree-level-${level}${rowClass}`} title={errorHint}>
      {showCheckbox ? (
        <input
          type="checkbox"
          className="tree-select-checkbox"
          checked={checked}
          disabled={nodeStatus !== "migrated" || isDeleting}
          onChange={(event) => onCheckChange?.(event.target.checked)}
          aria-label={`${label} 선택`}
        />
      ) : (
        <span className="tree-select-checkbox-placeholder" aria-hidden="true" />
      )}
      <button
        type="button"
        className="tree-expand-button"
        onClick={() => {
          if (hasChildren) {
            onExpandToggle(nodeKey);
          }
        }}
        aria-expanded={hasChildren ? isExpanded : undefined}
        disabled={!hasChildren}
      >
        <span className="tree-node-chevron" aria-hidden="true">
          {!hasChildren ? (
            <span className="tree-node-chevron-placeholder" />
          ) : isExpanded ? (
            <ChevronDown size={16} />
          ) : (
            <ChevronRight size={16} />
          )}
        </span>
        <span className="tree-node-icon" aria-hidden="true">
          {icon}
        </span>
        <span className="tree-label">{label}</span>
        {countLabel ? <span className="tree-node-count">{countLabel}</span> : null}
        {meta}
      </button>
      {nodeStatus === "migrated" && showDelete ? (
        <button
          type="button"
          className="tree-delete-button"
          title="마이그레이션으로 생성된 항목 삭제"
          disabled={isDeleting}
          onClick={() => onDelete?.()}
          aria-label={`${label} 삭제`}
        >
          <Trash2 size={14} aria-hidden="true" />
        </button>
      ) : null}
      {nodeStatus === "delete_error" && showRetry ? (
        <button
          type="button"
          className="tree-retry-button"
          title={errorHint ?? "삭제 재시도"}
          disabled={isDeleting}
          onClick={() => onRetry?.()}
          aria-label={`${label} 삭제 재시도`}
        >
          <RotateCcw size={14} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}

/**
 * 타겟 Help Center 트리에서 마이그레이션으로 생성된 항목을 강조하고 삭제할 수 있게 한다.
 */
export default function TargetMigratedTree({
  title,
  brands,
  overlay,
  selectedCategoryAIds,
  selectedSectionAIds,
  isDeleting,
  isMigrateRunning = false,
  onBulkDeleteSelected,
  onToggleCategory,
  onToggleSection,
  onDeleteCategory,
  onDeleteSection,
  onDeleteArticle,
  onRetryDeleteAll,
  onRetryDeleteMapping,
}: TargetMigratedTreeProps) {
  const overlaySets = useMemo(() => buildOverlaySets(overlay), [overlay]);
  const deleteErrorCount = overlay?.delete_error_items.length ?? 0;
  const [expandedKeys, setExpandedKeys] = useState<Set<TreeNodeKey>>(() => new Set());

  useEffect(() => {
    setExpandedKeys(new Set());
  }, [brands, overlay]);

  function toggleNode(nodeKey: TreeNodeKey) {
    setExpandedKeys((previous) => {
      const next = new Set(previous);
      if (next.has(nodeKey)) {
        next.delete(nodeKey);
      } else {
        next.add(nodeKey);
      }
      return next;
    });
  }

  function isExpanded(nodeKey: TreeNodeKey): boolean {
    return expandedKeys.has(nodeKey);
  }

  function renderArticles(section: FetchDetailSection) {
    if (!isExpanded(`section:${section.id}`)) {
      return null;
    }

    if (section.articles.length === 0) {
      return <p className="tree-empty-child muted">아티클 없음</p>;
    }

    return (
      <ul className="fetch-tree-children">
        {section.articles.map((article) => {
          const nodeStatus = resolveNodeStatus(overlaySets, "articles", article.a_id);
          const errorItem = overlaySets.errorByTargetAId.get(article.a_id);
          const rowClass =
            nodeStatus === "delete_error" ? " tree-row-delete-error" : nodeStatus === "migrated" ? " tree-row-migrated" : "";
          return (
            <li
              key={article.id}
              className={`tree-article-row${rowClass}`}
              title={errorItem?.error_message ?? undefined}
            >
              <FileText size={14} aria-hidden="true" className="tree-node-icon-muted" />
              <a
                href={article.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="tree-article-link"
                title="Zendesk Help Center에서 열기"
              >
                <span className="tree-label">{article.title}</span>
                <ExternalLink size={13} aria-hidden="true" className="tree-article-link-icon" />
              </a>
              {article.has_attachments ? (
                <span className="badge badge-gray tree-attachment-badge" title="첨부파일 있음">
                  <Paperclip size={12} aria-hidden="true" />
                  첨부
                </span>
              ) : null}
              {article.draft ? <span className="badge badge-yellow">초안</span> : null}
              {nodeStatus === "migrated" ? (
                <button
                  type="button"
                  className="tree-delete-button"
                  title="마이그레이션으로 생성된 아티클 삭제"
                  disabled={isDeleting}
                  onClick={() => onDeleteArticle(article.a_id)}
                  aria-label={`${article.title} 삭제`}
                >
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              ) : null}
              {nodeStatus === "delete_error" && errorItem ? (
                <button
                  type="button"
                  className="tree-retry-button"
                  title={errorItem.error_message ?? "삭제 재시도"}
                  disabled={isDeleting}
                  onClick={() => onRetryDeleteMapping(errorItem.mapping_id)}
                  aria-label={`${article.title} 삭제 재시도`}
                >
                  <RotateCcw size={14} aria-hidden="true" />
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
    );
  }

  function renderSections(category: FetchDetailCategory) {
    if (!isExpanded(`category:${category.id}`)) {
      return null;
    }

    if (category.sections.length === 0) {
      return <p className="tree-empty-child muted">섹션 없음</p>;
    }

    return (
      <ul className="fetch-tree-children">
        <NestedSectionTreeNodes
          sections={category.sections}
          level={2}
          isExpanded={isExpanded}
          renderSectionNode={(section, level, hasChildren) => {
            const childCount = section.children?.length ?? 0;
            const articleCount = section.articles.length;
            const nodeStatus = resolveNodeStatus(overlaySets, "sections", section.a_id);
            const errorItem = overlaySets.errorByTargetAId.get(section.a_id);
            const countParts: string[] = [];
            if (childCount > 0) {
              countParts.push(`하위 ${childCount}`);
            }
            if (articleCount > 0) {
              countParts.push(`아티클 ${articleCount}`);
            }
            return (
              <MigratedTreeRow
                showCheckbox
                showDelete
                showRetry
                nodeStatus={nodeStatus}
                errorHint={errorItem?.error_message ?? undefined}
                checked={selectedSectionAIds.includes(section.a_id)}
                label={section.name}
                level={level}
                nodeKey={`section:${section.id}`}
                hasChildren={hasChildren}
                isExpanded={isExpanded(`section:${section.id}`)}
                icon={<Layers size={15} />}
                countLabel={countParts.length > 0 ? countParts.join(" · ") : undefined}
                isDeleting={isDeleting}
                onExpandToggle={toggleNode}
                onCheckChange={(checked) => onToggleSection(section.a_id, checked)}
                onDelete={() => onDeleteSection(section.a_id)}
                onRetry={() => errorItem && onRetryDeleteMapping(errorItem.mapping_id)}
              />
            );
          }}
          renderSectionChildren={(section) => renderArticles(section)}
        />
      </ul>
    );
  }

  function renderCategories(brand: FetchDetailBrand) {
    if (!isExpanded(`brand:${brand.id}`)) {
      return null;
    }

    if (brand.categories.length === 0) {
      return <p className="tree-empty-child muted">카테고리 없음</p>;
    }

    return (
      <ul className="fetch-tree-children">
        {brand.categories.map((category) => {
          const sectionCount = countSectionsForCategory(category);
          const articleCount = countCategoryArticles(category);
          const nodeStatus = resolveNodeStatus(overlaySets, "categories", category.a_id);
          const errorItem = overlaySets.errorByTargetAId.get(category.a_id);
          return (
            <li key={category.id} className="fetch-tree-node">
              <MigratedTreeRow
                showCheckbox
                showDelete
                showRetry
                nodeStatus={nodeStatus}
                errorHint={errorItem?.error_message ?? undefined}
                checked={selectedCategoryAIds.includes(category.a_id)}
                label={category.name}
                level={1}
                nodeKey={`category:${category.id}`}
                hasChildren={sectionCount > 0}
                isExpanded={isExpanded(`category:${category.id}`)}
                icon={<Folder size={15} />}
                countLabel={
                  sectionCount > 0 ? `섹션 ${sectionCount}${articleCount > 0 ? ` · 아티클 ${articleCount}` : ""}` : undefined
                }
                isDeleting={isDeleting}
                onExpandToggle={toggleNode}
                onCheckChange={(checked) => onToggleCategory(category.a_id, checked)}
                onDelete={() => onDeleteCategory(category.a_id)}
                onRetry={() => errorItem && onRetryDeleteMapping(errorItem.mapping_id)}
              />
              {renderSections(category)}
            </li>
          );
        })}
      </ul>
    );
  }

  const hasMigrated =
    overlaySets.migrated.categories.size > 0 ||
    overlaySets.migrated.sections.size > 0 ||
    overlaySets.migrated.articles.size > 0;

  const hasBulkSelection = selectedCategoryAIds.length > 0 || selectedSectionAIds.length > 0;

  return (
    <div className="card fetch-tree-card target-migrated-tree">
      <div className="fetch-tree-toolbar">
        <h3>{title}</h3>
        <div className="fetch-tree-actions">
          {deleteErrorCount > 0 ? (
            <button
              type="button"
              className="button-ghost tree-retry-all-button"
              disabled={isDeleting || isMigrateRunning}
              onClick={onRetryDeleteAll}
            >
              {isDeleting ? "처리 중..." : `삭제 실패 ${deleteErrorCount}건 재시도`}
            </button>
          ) : null}
          <button
            type="button"
            className="migrate-danger-action"
            disabled={isDeleting || isMigrateRunning || !hasBulkSelection}
            onClick={onBulkDeleteSelected}
          >
            {isDeleting ? "삭제 중..." : "선택 항목 삭제"}
          </button>
        </div>
      </div>

      {!hasMigrated ? (
        <p className="muted">마이그레이션으로 생성된 항목이 없습니다. 마이그레이션 완료 후 여기에 강조 표시됩니다.</p>
      ) : null}

      {brands.length === 0 ? (
        <p className="muted">수집된 데이터가 없습니다.</p>
      ) : (
        <ul className="fetch-tree-root">
          {brands.map((brand) => {
            const categoryCount = brand.categories.length;
            const sectionCount = countBrandSections(brand);
            const articleCount = countBrandArticles(brand);
            const countParts: string[] = [];
            if (categoryCount > 0) {
              countParts.push(`카테고리 ${categoryCount}`);
            }
            if (sectionCount > 0) {
              countParts.push(`섹션 ${sectionCount}`);
            }
            if (articleCount > 0) {
              countParts.push(`아티클 ${articleCount}`);
            }

            return (
              <li key={brand.id} className="fetch-tree-node fetch-tree-node-brand">
                <MigratedTreeRow
                  showCheckbox={false}
                  showDelete={false}
                  showRetry={false}
                  label={brand.name}
                  level={0}
                  nodeKey={`brand:${brand.id}`}
                  hasChildren={categoryCount > 0}
                  isExpanded={isExpanded(`brand:${brand.id}`)}
                  icon={<Store size={16} />}
                  countLabel={countParts.length > 0 ? countParts.join(" · ") : undefined}
                  meta={<span className="badge badge-gray">{brand.subdomain}</span>}
                  isDeleting={isDeleting}
                  onExpandToggle={toggleNode}
                />
                {renderCategories(brand)}
              </li>
            );
          })}
        </ul>
      )}

      <p className="muted fetch-tree-hint">
        <span className="tree-migrated-legend" aria-hidden="true" />
        초록: 마이그레이션 생성
        <span className="tree-delete-error-legend" aria-hidden="true" />
        주황: 삭제 실패(재시도 가능). 카테고리·섹션은 체크 후 일괄 삭제할 수 있습니다.
      </p>
    </div>
  );
}
