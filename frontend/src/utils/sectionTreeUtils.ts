import type { FetchDetailCategory, FetchDetailSection } from "../api/client";

/**
 * 중첩 섹션 트리를 순회한다.
 * @param sections 루트 섹션 목록
 * @param visit 각 섹션 노드 콜백
 */
export function walkSections(
  sections: FetchDetailSection[],
  visit: (section: FetchDetailSection) => void,
): void {
  for (const section of sections) {
    visit(section);
    if (section.children && section.children.length > 0) {
      walkSections(section.children, visit);
    }
  }
}

/**
 * 카테고리 하위 섹션 총 개수(하위 섹션 포함)를 센다.
 */
export function countCategorySections(category: Pick<FetchDetailCategory, "sections">): number {
  let total = 0;
  walkSections(category.sections, () => {
    total += 1;
  });
  return total;
}

/**
 * 카테고리 하위 아티클 총 개수를 센다.
 */
export function countCategoryArticlesNested(category: Pick<FetchDetailCategory, "sections">): number {
  let total = 0;
  walkSections(category.sections, (section) => {
    total += section.articles.length;
  });
  return total;
}

/**
 * 브랜드 하위 섹션 총 개수를 센다.
 */
export function countBrandSectionsNested(
  brand: { categories: FetchDetailCategory[] },
): number {
  return brand.categories.reduce((sum, category) => sum + countCategorySections(category), 0);
}

/**
 * 모달·트리 펼치기용 섹션 확장 키를 수집한다.
 */
export function collectSectionExpandKeys(
  sections: FetchDetailSection[],
  brandId: number,
  categoryAId: number,
): string[] {
  const keys: string[] = [];
  walkSections(sections, (section) => {
    if (section.children && section.children.length > 0) {
      keys.push(`${brandId}:${categoryAId}:${section.a_id}`);
    }
  });
  return keys;
}

/**
 * 카테고리 펼치기용 키를 수집한다.
 */
export function collectCategoryExpandKeys(
  categories: FetchDetailCategory[],
  brandId: number,
): string[] {
  return categories.map((category) => `${brandId}:${category.a_id}`);
}
