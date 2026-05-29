import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, ExternalLink, FileText, Folder, Layers, Paperclip, Store } from "lucide-react";
import type { FetchDetailBrand, FetchDetailCategory, FetchDetailSection } from "../api/client";

interface FetchDataTreeProps {
  title: string;
  brands: FetchDetailBrand[];
}

type TreeNodeKey = string;

/**
 * 카테고리 하위 아티클 총 개수를 계산한다.
 * @param category 카테고리 노드
 */
function countCategoryArticles(category: FetchDetailCategory): number {
  return category.sections.reduce((sum, section) => sum + section.articles.length, 0);
}

/**
 * 브랜드 하위 섹션 총 개수를 계산한다.
 * @param brand 브랜드 노드
 */
function countBrandSections(brand: FetchDetailBrand): number {
  return brand.categories.reduce((sum, category) => sum + category.sections.length, 0);
}

/**
 * 브랜드 하위 아티클 총 개수를 계산한다.
 * @param brand 브랜드 노드
 */
function countBrandArticles(brand: FetchDetailBrand): number {
  return brand.categories.reduce((sum, category) => sum + countCategoryArticles(category), 0);
}

/**
 * 트리 전체에서 접기/펼치기에 사용할 노드 키 목록을 만든다.
 * @param brands 브랜드 트리 데이터
 */
function collectAllNodeKeys(brands: FetchDetailBrand[]): TreeNodeKey[] {
  const keys: TreeNodeKey[] = [];
  for (const brand of brands) {
    keys.push(`brand:${brand.id}`);
    for (const category of brand.categories) {
      keys.push(`category:${category.id}`);
      for (const section of category.sections) {
        keys.push(`section:${section.id}`);
      }
    }
  }
  return keys;
}

interface TreeNodeHeaderProps {
  nodeKey: TreeNodeKey;
  label: string;
  level: number;
  hasChildren: boolean;
  isExpanded: boolean;
  icon: ReactNode;
  meta?: ReactNode;
  countLabel?: string;
  onToggle: (nodeKey: TreeNodeKey) => void;
}

/**
 * 접기/펼치기 가능한 트리 노드 헤더를 렌더링한다.
 */
function TreeNodeHeader({
  nodeKey,
  label,
  level,
  hasChildren,
  isExpanded,
  icon,
  meta,
  countLabel,
  onToggle,
}: TreeNodeHeaderProps) {
  return (
    <button
      type="button"
      className={`tree-node-header tree-level-${level}`}
      onClick={() => {
        if (hasChildren) {
          onToggle(nodeKey);
        }
      }}
      aria-expanded={hasChildren ? isExpanded : undefined}
      disabled={!hasChildren}
    >
      <span className="tree-node-chevron" aria-hidden="true">
        {!hasChildren ? <span className="tree-node-chevron-placeholder" /> : isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </span>
      <span className="tree-node-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="tree-label">{label}</span>
      {countLabel ? <span className="tree-node-count">{countLabel}</span> : null}
      {meta}
    </button>
  );
}

/**
 * 수집된 Help Center 데이터를 접기/펼치기 가능한 트리로 표시한다.
 * @param title 트리 섹션 제목
 * @param brands 브랜드 → 카테고리 → 섹션 → 아티클 트리 데이터
 */
export default function FetchDataTree({ title, brands }: FetchDataTreeProps) {
  const [expandedKeys, setExpandedKeys] = useState<Set<TreeNodeKey>>(() => new Set());
  const allNodeKeys = useMemo(() => collectAllNodeKeys(brands), [brands]);

  useEffect(() => {
    setExpandedKeys(new Set());
  }, [brands]);

  /**
   * 노드 접기/펼치기 상태를 토글한다.
   * @param nodeKey 대상 노드 키
   */
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

  function expandAll() {
    setExpandedKeys(new Set(allNodeKeys));
  }

  function collapseAll() {
    setExpandedKeys(new Set());
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
        {section.articles.map((article) => (
          <li key={article.id} className="tree-article-row">
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
          </li>
        ))}
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
        {category.sections.map((section) => {
          const articleCount = section.articles.length;
          return (
            <li key={section.id} className="fetch-tree-node">
              <TreeNodeHeader
                nodeKey={`section:${section.id}`}
                label={section.name}
                level={2}
                hasChildren={articleCount > 0}
                isExpanded={isExpanded(`section:${section.id}`)}
                icon={<Layers size={15} />}
                countLabel={articleCount > 0 ? `아티클 ${articleCount}` : undefined}
                onToggle={toggleNode}
              />
              {renderArticles(section)}
            </li>
          );
        })}
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
          const sectionCount = category.sections.length;
          const articleCount = countCategoryArticles(category);
          return (
            <li key={category.id} className="fetch-tree-node">
              <TreeNodeHeader
                nodeKey={`category:${category.id}`}
                label={category.name}
                level={1}
                hasChildren={sectionCount > 0}
                isExpanded={isExpanded(`category:${category.id}`)}
                icon={<Folder size={15} />}
                countLabel={
                  sectionCount > 0 ? `섹션 ${sectionCount}${articleCount > 0 ? ` · 아티클 ${articleCount}` : ""}` : undefined
                }
                onToggle={toggleNode}
              />
              {renderSections(category)}
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <div className="card fetch-tree-card">
      <div className="fetch-tree-toolbar">
        <h3>{title}</h3>
        {brands.length > 0 ? (
          <div className="fetch-tree-actions">
            <button type="button" className="button-ghost" onClick={expandAll}>
              모두 펼치기
            </button>
            <button type="button" className="button-ghost" onClick={collapseAll}>
              모두 접기
            </button>
          </div>
        ) : null}
      </div>

      {brands.length === 0 ? (
        <p className="muted">수집된 데이터가 없습니다. 수집 실행 후 이 영역에 표시됩니다.</p>
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
                <TreeNodeHeader
                  nodeKey={`brand:${brand.id}`}
                  label={brand.name}
                  level={0}
                  hasChildren={categoryCount > 0}
                  isExpanded={isExpanded(`brand:${brand.id}`)}
                  icon={<Store size={16} />}
                  countLabel={countParts.length > 0 ? countParts.join(" · ") : undefined}
                  meta={
                    <>
                      <span className="badge badge-gray">{brand.subdomain}</span>
                      {!brand.has_help_center ? <span className="badge badge-yellow">Help Center 없음</span> : null}
                    </>
                  }
                  onToggle={toggleNode}
                />
                {renderCategories(brand)}
              </li>
            );
          })}
        </ul>
      )}

      <p className="muted fetch-tree-hint">브랜드·카테고리·섹션 행을 클릭하면 하위 항목을 펼치거나 접을 수 있습니다.</p>
    </div>
  );
}
