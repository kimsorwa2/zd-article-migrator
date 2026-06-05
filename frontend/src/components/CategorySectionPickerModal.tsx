import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  FolderOpen,
  Layers,
  MapPin,
  Store,
  X,
} from "lucide-react";
import type { AiOcrSectionSelection, FetchDetailBrand, FetchDetailResponse, FetchDetailSection } from "../api/client";
import {
  collectCategoryExpandKeys,
  collectSectionExpandKeys,
  countCategorySections,
} from "../utils/sectionTreeUtils";

interface CategorySectionPickerModalProps {
  open: boolean;
  fetchDetail: FetchDetailResponse | null;
  loading?: boolean;
  onClose: () => void;
  onSelect: (selection: AiOcrSectionSelection) => void;
}

interface SectionBranchProps {
  brand: FetchDetailBrand;
  categoryAId: number;
  categoryName: string;
  section: FetchDetailSection;
  depth: number;
  expandedSectionKeys: Set<string>;
  onToggleSection: (key: string) => void;
  onSelect: (selection: AiOcrSectionSelection) => void;
  onClose: () => void;
}

/**
 * 섹션·하위 섹션을 재귀적으로 렌더한다.
 */
function SectionBranch({
  brand,
  categoryAId,
  categoryName,
  section,
  depth,
  expandedSectionKeys,
  onToggleSection,
  onSelect,
  onClose,
}: SectionBranchProps) {
  const children = section.children ?? [];
  const hasChildren = children.length > 0;
  const sectionKey = `${brand.id}:${categoryAId}:${section.a_id}`;
  const expanded = expandedSectionKeys.has(sectionKey);

  function handleSelect() {
    onSelect({
      brandId: brand.id,
      brandName: brand.name,
      categoryAId,
      categoryName,
      sectionAId: section.a_id,
      sectionName: section.name,
    });
    onClose();
  }

  return (
    <li className={`csp-section-branch csp-section-depth-${Math.min(depth, 4)}`}>
      <div className={`csp-section-row-wrap${hasChildren && expanded ? " is-expanded" : ""}`}>
        {hasChildren ? (
          <button
            type="button"
            className="csp-section-chevron-btn"
            onClick={() => onToggleSection(sectionKey)}
            aria-expanded={expanded}
            aria-label={`${section.name} 하위 섹션 ${expanded ? "접기" : "펼치기"}`}
          >
            <span className="csp-chevron" aria-hidden="true">
              {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </span>
          </button>
        ) : (
          <span className="csp-section-chevron-placeholder" aria-hidden="true" />
        )}

        <button type="button" className="csp-section-row" onClick={handleSelect}>
          <Layers size={14} aria-hidden="true" />
          <span className="csp-section-label">{section.name}</span>
          {hasChildren ? <span className="csp-category-count">하위 {children.length}</span> : null}
          <span className="csp-section-action">선택</span>
        </button>
      </div>

      {hasChildren && expanded ? (
        <ul className="csp-section-children">
          {children.map((child) => (
            <SectionBranch
              key={child.id}
              brand={brand}
              categoryAId={categoryAId}
              categoryName={categoryName}
              section={child}
              depth={depth + 1}
              expandedSectionKeys={expandedSectionKeys}
              onToggleSection={onToggleSection}
              onSelect={onSelect}
              onClose={onClose}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/**
 * 수집된 Help Center 트리에서 카테고리·섹션(중첩 포함)을 선택하는 모달.
 */
export default function CategorySectionPickerModal({
  open,
  fetchDetail,
  loading = false,
  onClose,
  onSelect,
}: CategorySectionPickerModalProps) {
  const [expandedCategoryKeys, setExpandedCategoryKeys] = useState<Set<string>>(() => new Set());
  const [expandedSectionKeys, setExpandedSectionKeys] = useState<Set<string>>(() => new Set());

  const hcBrands = useMemo(
    () => (fetchDetail?.brands ?? []).filter((brand) => brand.has_help_center),
    [fetchDetail],
  );

  const allCategoryKeys = useMemo(
    () => hcBrands.flatMap((brand) => collectCategoryExpandKeys(brand.categories, brand.id)),
    [hcBrands],
  );

  const allSectionKeys = useMemo(
    () =>
      hcBrands.flatMap((brand) =>
        brand.categories.flatMap((category) =>
          collectSectionExpandKeys(category.sections, brand.id, category.a_id),
        ),
      ),
    [hcBrands],
  );

  useEffect(() => {
    if (!open) {
      return;
    }
    setExpandedCategoryKeys(new Set());
    setExpandedSectionKeys(new Set());
  }, [open, fetchDetail?.instance_id]);

  if (!open) {
    return null;
  }

  function toggleCategory(key: string) {
    setExpandedCategoryKeys((previous) => {
      const next = new Set(previous);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function toggleSection(key: string) {
    setExpandedSectionKeys((previous) => {
      const next = new Set(previous);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function expandAll() {
    setExpandedCategoryKeys(new Set(allCategoryKeys));
    setExpandedSectionKeys(new Set(allSectionKeys));
  }

  function collapseAll() {
    setExpandedCategoryKeys(new Set());
    setExpandedSectionKeys(new Set());
  }

  return (
    <div className="modal-overlay csp-overlay" onClick={onClose}>
      <div
        className="modal-panel csp-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="csp-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="csp-header">
          <div className="csp-header-text">
            <div className="csp-header-icon" aria-hidden="true">
              <MapPin size={20} />
            </div>
            <div>
              <h3 id="csp-modal-title">카테고리 · 섹션 선택</h3>
              <p className="csp-header-sub">
                {fetchDetail?.instance_name
                  ? `${fetchDetail.instance_name} — 섹션·하위 섹션 중 게시할 위치를 고르세요`
                  : "섹션·하위 섹션 중 게시할 위치를 고르세요"}
              </p>
            </div>
          </div>
          <button type="button" className="csp-close" onClick={onClose} aria-label="닫기">
            <X size={18} aria-hidden="true" />
          </button>
        </header>

        <div className="modal-body">
        {!loading && hcBrands.length > 0 ? (
          <div className="csp-toolbar">
            <button type="button" className="csp-toolbar-btn" onClick={expandAll}>
              모두 펼치기
            </button>
            <button type="button" className="csp-toolbar-btn" onClick={collapseAll}>
              모두 접기
            </button>
          </div>
        ) : null}

        <div className="csp-body">
          {loading ? (
            <div className="csp-state csp-state-loading">
              <span className="csp-spinner" aria-hidden="true" />
              <p>Help Center 구조를 불러오는 중...</p>
            </div>
          ) : null}

          {!loading && hcBrands.length === 0 ? (
            <div className="csp-state csp-state-empty">
              <FolderOpen size={32} strokeWidth={1.5} aria-hidden="true" />
              <p className="csp-state-title">수집된 데이터가 없습니다</p>
              <p className="muted">인스턴스 관리에서 Help Center 수집을 먼저 실행하세요.</p>
              <p className="muted csp-resync-hint">
                이미 수집했다면, 하위 섹션 반영을 위해 <strong>다시 수집</strong>이 필요할 수 있습니다.
              </p>
            </div>
          ) : null}

          {!loading && hcBrands.length > 0 ? (
            <div className="csp-brand-list">
              {hcBrands.map((brand) => (
                <section key={brand.id} className="csp-brand-card">
                  <div className="csp-brand-head">
                    <Store size={16} aria-hidden="true" className="csp-brand-icon" />
                    <span className="csp-brand-name">{brand.name}</span>
                    <span className="csp-brand-badge">{brand.subdomain}</span>
                  </div>

                  <ul className="csp-category-list">
                    {brand.categories.length === 0 ? (
                      <li className="csp-empty-inline muted">카테고리 없음</li>
                    ) : (
                      brand.categories.map((category) => {
                        const categoryKey = `${brand.id}:${category.a_id}`;
                        const expanded = expandedCategoryKeys.has(categoryKey);
                        const sectionCount = countCategorySections(category);

                        return (
                          <li key={category.id} className="csp-category-item">
                            <button
                              type="button"
                              className={`csp-category-row${expanded ? " is-expanded" : ""}`}
                              onClick={() => toggleCategory(categoryKey)}
                              aria-expanded={expanded}
                            >
                              <span className="csp-chevron" aria-hidden="true">
                                {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              </span>
                              <span className="csp-category-icon" aria-hidden="true">
                                <FolderOpen size={15} />
                              </span>
                              <span className="csp-category-label">{category.name}</span>
                              <span className="csp-category-count">섹션 {sectionCount}</span>
                            </button>

                            {expanded ? (
                              <ul className="csp-section-list csp-section-list-root">
                                {sectionCount === 0 ? (
                                  <li className="csp-empty-inline muted">섹션 없음</li>
                                ) : (
                                  category.sections.map((section) => (
                                    <SectionBranch
                                      key={section.id}
                                      brand={brand}
                                      categoryAId={category.a_id}
                                      categoryName={category.name}
                                      section={section}
                                      depth={0}
                                      expandedSectionKeys={expandedSectionKeys}
                                      onToggleSection={toggleSection}
                                      onSelect={onSelect}
                                      onClose={onClose}
                                    />
                                  ))
                                )}
                              </ul>
                            ) : null}
                          </li>
                        );
                      })
                    )}
                  </ul>
                </section>
              ))}
            </div>
          ) : null}
        </div>

        <footer className="csp-footer">
          <p className="muted">섹션(또는 하위 섹션)을 클릭하면 선택이 완료됩니다.</p>
        </footer>
        </div>
      </div>
    </div>
  );
}
