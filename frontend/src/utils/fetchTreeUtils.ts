import type { FetchDetailBrand, FetchDetailCategory } from "../api/client";

/**
 * 카테고리 하위 아티클 총 개수를 계산한다.
 * @param category 카테고리 노드
 */
export function countCategoryArticles(category: FetchDetailCategory): number {
  return category.sections.reduce((sum, section) => sum + section.articles.length, 0);
}

/**
 * 브랜드 하위 섹션 총 개수를 계산한다.
 * @param brand 브랜드 노드
 */
export function countBrandSections(brand: FetchDetailBrand): number {
  return brand.categories.reduce((sum, category) => sum + category.sections.length, 0);
}

/**
 * 브랜드 하위 아티클 총 개수를 계산한다.
 * @param brand 브랜드 노드
 */
export function countBrandArticles(brand: FetchDetailBrand): number {
  return brand.categories.reduce((sum, category) => sum + countCategoryArticles(category), 0);
}

/**
 * 접기/펼치기에 사용할 노드 키 목록을 수집한다.
 * @param brands 브랜드 트리 데이터
 */
export function collectAllNodeKeys(brands: FetchDetailBrand[]): string[] {
  const keys: string[] = [];
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
