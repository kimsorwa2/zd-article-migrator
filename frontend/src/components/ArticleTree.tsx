import type { MigrateTreeNodeBrand } from "../api/client";

interface ArticleTreeProps {
  title: string;
  brands: MigrateTreeNodeBrand[];
  selectedBrandIds: number[];
  selectedCategoryIds: number[];
  selectedSectionIds: number[];
  selectedArticleIds: number[];
  onToggleBrand: (id: number, checked: boolean) => void;
  onToggleCategory: (id: number, checked: boolean) => void;
  onToggleSection: (id: number, checked: boolean) => void;
  onToggleArticle: (id: number, checked: boolean) => void;
}

function statusToBadge(status: string): string {
  if (status === "migrated") return "badge-green";
  if (status.includes("error")) return "badge-red";
  if (status === "needs_update") return "badge-yellow";
  return "badge-gray";
}

export default function ArticleTree({
  title,
  brands,
  selectedBrandIds,
  selectedCategoryIds,
  selectedSectionIds,
  selectedArticleIds,
  onToggleBrand,
  onToggleCategory,
  onToggleSection,
  onToggleArticle,
}: ArticleTreeProps) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {brands.length === 0 ? (
        <p className="muted">트리 데이터가 없습니다.</p>
      ) : (
        <ul className="simple-list tree-list">
          {brands.map((brand) => (
            <li key={brand.id}>
              <label className="tree-row">
                <input
                  type="checkbox"
                  checked={selectedBrandIds.includes(brand.id)}
                  onChange={(event) => onToggleBrand(brand.id, event.target.checked)}
                />
                <span className="tree-label">{brand.name}</span>
                <span className={`badge ${statusToBadge(brand.status)}`}>{brand.status}</span>
              </label>

              <ul className="simple-list tree-list">
                {brand.categories.map((category) => (
                  <li key={category.id}>
                    <label className="tree-row">
                      <input
                        type="checkbox"
                        checked={selectedCategoryIds.includes(category.id)}
                        onChange={(event) => onToggleCategory(category.id, event.target.checked)}
                      />
                      <span className="tree-label">{category.name}</span>
                      <span className={`badge ${statusToBadge(category.status)}`}>{category.status}</span>
                    </label>

                    <ul className="simple-list tree-list">
                      {category.sections.map((section) => (
                        <li key={section.id}>
                          <label className="tree-row">
                            <input
                              type="checkbox"
                              checked={selectedSectionIds.includes(section.id)}
                              onChange={(event) => onToggleSection(section.id, event.target.checked)}
                            />
                            <span className="tree-label">{section.name}</span>
                            <span className={`badge ${statusToBadge(section.status)}`}>{section.status}</span>
                          </label>
                          <ul className="simple-list tree-list">
                            {section.articles.map((article) => (
                              <li key={article.id}>
                                <label className="tree-row">
                                  <input
                                    type="checkbox"
                                    checked={selectedArticleIds.includes(article.id)}
                                    onChange={(event) => onToggleArticle(article.id, event.target.checked)}
                                  />
                                  <span className="tree-label">{article.title}</span>
                                  <span className={`badge ${statusToBadge(article.status)}`}>{article.status}</span>
                                </label>
                              </li>
                            ))}
                          </ul>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
