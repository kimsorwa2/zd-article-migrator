import { useEffect, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, FileText, Folder, Layers, Store } from "lucide-react";
import type { FetchDetailBrand, FetchDetailCategory, FetchDetailSection } from "../api/client";
import { countBrandArticles, countBrandSections, countCategoryArticles } from "../utils/fetchTreeUtils";
import { NestedSectionTreeNodes, countSectionsForCategory } from "./NestedSectionTreeNodes";

interface SelectableSourceTreeProps {
  brands: FetchDetailBrand[];
  selectedBrandIds: number[];
  selectedCategoryIds: number[];
  selectedSectionIds: number[];
  selectedArticleIds: number[];
  onToggleBrand: (id: number, checked: boolean) => void;
  onToggleCategory: (id: number, checked: boolean) => void;
  onToggleSection: (id: number, checked: boolean) => void;
  onToggleArticle: (id: number, checked: boolean) => void;
}

type TreeNodeKey = string;

interface SelectableTreeRowProps {
  checked: boolean;
  onCheckChange: (checked: boolean) => void;
  nodeKey: TreeNodeKey;
  label: string;
  level: number;
  hasChildren: boolean;
  isExpanded: boolean;
  icon: ReactNode;
  meta?: ReactNode;
  countLabel?: string;
  onExpandToggle: (nodeKey: TreeNodeKey) => void;
}

/**
 * 체크박스와 접기/펼치기가 함께 있는 트리 행을 렌더링한다.
 */
function SelectableTreeRow({
  checked,
  onCheckChange,
  nodeKey,
  label,
  level,
  hasChildren,
  isExpanded,
  icon,
  meta,
  countLabel,
  onExpandToggle,
}: SelectableTreeRowProps) {
  return (
    <div className={`tree-select-row tree-level-${level}`}>
      <input
        type="checkbox"
        className="tree-select-checkbox"
        checked={checked}
        onChange={(event) => onCheckChange(event.target.checked)}
        aria-label={`${label} 선택`}
      />
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
    </div>
  );
}

/**
 * 소스 Help Center 구조를 체크박스와 함께 접기/펼치기 가능한 트리로 표시한다.
 */
export default function SelectableSourceTree({
  brands,
  selectedBrandIds,
  selectedCategoryIds,
  selectedSectionIds,
  selectedArticleIds,
  onToggleBrand,
  onToggleCategory,
  onToggleSection,
  onToggleArticle,
}: SelectableSourceTreeProps) {
  const [expandedKeys, setExpandedKeys] = useState<Set<TreeNodeKey>>(() => new Set());

  useEffect(() => {
    setExpandedKeys(new Set());
  }, [brands]);

  function toggleExpand(nodeKey: TreeNodeKey) {
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
        {section.articles.map((article) => (
          <li key={article.id} className="tree-article-row tree-select-article-row">
            <input
              type="checkbox"
              className="tree-select-checkbox"
              checked={selectedArticleIds.includes(article.id)}
              onChange={(event) => onToggleArticle(article.id, event.target.checked)}
              aria-label={`${article.title} 선택`}
            />
            <FileText size={14} aria-hidden="true" className="tree-node-icon-muted" />
            <span className="tree-label">{article.title}</span>
            {article.draft ? <span className="badge badge-yellow">초안</span> : null}
            {article.has_attachments ? <span className="badge badge-gray">첨부</span> : null}
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
        <NestedSectionTreeNodes
          sections={category.sections}
          level={2}
          isExpanded={isExpanded}
          renderSectionNode={(section, level, hasChildren) => {
            const childCount = section.children?.length ?? 0;
            const articleCount = section.articles.length;
            const countParts: string[] = [];
            if (childCount > 0) {
              countParts.push(`하위 ${childCount}`);
            }
            if (articleCount > 0) {
              countParts.push(`아티클 ${articleCount}`);
            }
            return (
              <SelectableTreeRow
                checked={selectedSectionIds.includes(section.id)}
                onCheckChange={(checked) => onToggleSection(section.id, checked)}
                nodeKey={`section:${section.id}`}
                label={section.name}
                level={level}
                hasChildren={hasChildren}
                isExpanded={isExpanded(`section:${section.id}`)}
                icon={<Layers size={15} />}
                countLabel={countParts.length > 0 ? countParts.join(" · ") : undefined}
                onExpandToggle={toggleExpand}
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
          return (
            <li key={category.id} className="fetch-tree-node">
              <SelectableTreeRow
                checked={selectedCategoryIds.includes(category.id)}
                onCheckChange={(checked) => onToggleCategory(category.id, checked)}
                nodeKey={`category:${category.id}`}
                label={category.name}
                level={1}
                hasChildren={sectionCount > 0}
                isExpanded={isExpanded(`category:${category.id}`)}
                icon={<Folder size={15} />}
                countLabel={
                  sectionCount > 0 ? `섹션 ${sectionCount}${articleCount > 0 ? ` · 아티클 ${articleCount}` : ""}` : undefined
                }
                onExpandToggle={toggleExpand}
              />
              {renderSections(category)}
            </li>
          );
        })}
      </ul>
    );
  }

  if (brands.length === 0) {
    return <p className="muted">수집된 소스 데이터가 없습니다. 데이터 수집 후 다시 선택해 주세요.</p>;
  }

  return (
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
            <SelectableTreeRow
              checked={selectedBrandIds.includes(brand.id)}
              onCheckChange={(checked) => onToggleBrand(brand.id, checked)}
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
              onExpandToggle={toggleExpand}
            />
            {renderCategories(brand)}
          </li>
        );
      })}
    </ul>
  );
}
