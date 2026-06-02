import type { FetchDetailBrand } from "../api/client";
import { walkSections } from "./sectionTreeUtils";

export interface FetchTreeChildMaps {
  brandToCategories: Map<number, number[]>;
  categoryToSections: Map<number, number[]>;
  sectionToArticles: Map<number, number[]>;
}

export interface FetchTreeAllIds {
  brandIds: number[];
  categoryIds: number[];
  sectionIds: number[];
  articleIds: number[];
}

/**
 * Fetch 트리의 부모-자식 ID 관계 맵을 생성한다.
 * @param brands 브랜드 트리 데이터
 */
export function buildFetchTreeChildMaps(brands: FetchDetailBrand[]): FetchTreeChildMaps {
  const brandToCategories = new Map<number, number[]>();
  const categoryToSections = new Map<number, number[]>();
  const sectionToArticles = new Map<number, number[]>();

  for (const brand of brands) {
    const categoryIds = brand.categories.map((category) => category.id);
    brandToCategories.set(brand.id, categoryIds);

    for (const category of brand.categories) {
      const sectionIds: number[] = [];
      categoryToSections.set(category.id, sectionIds);

      walkSections(category.sections, (section) => {
        sectionIds.push(section.id);
        sectionToArticles.set(
          section.id,
          section.articles.map((article) => article.id),
        );
      });
    }
  }

  return { brandToCategories, categoryToSections, sectionToArticles };
}

/**
 * Fetch 트리에 포함된 모든 노드 ID를 수집한다.
 * @param brands 브랜드 트리 데이터
 */
export function collectAllFetchTreeIds(brands: FetchDetailBrand[]): FetchTreeAllIds {
  const brandIds: number[] = [];
  const categoryIds: number[] = [];
  const sectionIds: number[] = [];
  const articleIds: number[] = [];

  for (const brand of brands) {
    brandIds.push(brand.id);
    for (const category of brand.categories) {
      categoryIds.push(category.id);
      walkSections(category.sections, (section) => {
        sectionIds.push(section.id);
        for (const article of section.articles) {
          articleIds.push(article.id);
        }
      });
    }
  }

  return { brandIds, categoryIds, sectionIds, articleIds };
}

/**
 * Fetch 트리의 A ID 맵을 생성한다(삭제 API 등에서 사용).
 * @param brands 브랜드 트리 데이터
 */
export function buildFetchTreeAIdMaps(brands: FetchDetailBrand[]) {
  const brandMap = new Map<number, number>();
  const categoryMap = new Map<number, number>();
  const sectionMap = new Map<number, number>();
  const articleMap = new Map<number, number>();

  for (const brand of brands) {
    brandMap.set(brand.id, brand.a_brand_id);
    for (const category of brand.categories) {
      categoryMap.set(category.id, category.a_id);
      walkSections(category.sections, (section) => {
        sectionMap.set(section.id, section.a_id);
        for (const article of section.articles) {
          articleMap.set(article.id, article.a_id);
        }
      });
    }
  }

  return { brandMap, categoryMap, sectionMap, articleMap };
}
