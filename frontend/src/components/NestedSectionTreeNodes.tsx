import type { ReactNode } from "react";
import type { FetchDetailSection } from "../api/client";
import { countCategorySections } from "../utils/sectionTreeUtils";

export { countCategorySections };

interface NestedSectionTreeNodesProps {
  sections: FetchDetailSection[];
  level: number;
  isExpanded: (nodeKey: string) => boolean;
  renderSectionNode: (section: FetchDetailSection, level: number, hasChildren: boolean) => ReactNode;
  renderSectionChildren: (section: FetchDetailSection) => ReactNode;
}

/**
 * 중첩 섹션(children) 트리를 재귀 렌더한다.
 */
export function NestedSectionTreeNodes({
  sections,
  level,
  isExpanded,
  renderSectionNode,
  renderSectionChildren,
}: NestedSectionTreeNodesProps) {
  return (
    <>
      {sections.map((section) => {
        const childSections = section.children ?? [];
        const hasChildSections = childSections.length > 0;
        const hasArticles = section.articles.length > 0;
        const hasChildren = hasChildSections || hasArticles;
        const sectionExpanded = isExpanded(`section:${section.id}`);

        return (
          <li key={section.id} className="fetch-tree-node">
            {renderSectionNode(section, level, hasChildren)}
            {sectionExpanded ? (
              <>
                {renderSectionChildren(section)}
                {hasChildSections ? (
                  <ul className="fetch-tree-children">
                    <NestedSectionTreeNodes
                      sections={childSections}
                      level={level + 1}
                      isExpanded={isExpanded}
                      renderSectionNode={renderSectionNode}
                      renderSectionChildren={renderSectionChildren}
                    />
                  </ul>
                ) : null}
              </>
            ) : null}
          </li>
        );
      })}
    </>
  );
}

/**
 * 카테고리의 루트 섹션 개수(하위 포함)를 반환한다.
 */
export function countSectionsForCategory(category: { sections: FetchDetailSection[] }): number {
  return countCategorySections(category);
}
