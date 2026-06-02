"""
Help Center 카테고리·섹션 계층 트리 구성 유틸리티.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from db.models import Article, Section

T = TypeVar("T")


def build_nested_section_nodes(
    category_sections: list[Section],
    *,
    build_articles: Callable[[Section], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    /**
     * 카테고리 소속 섹션을 parent_section_id 기준 중첩 트리로 만든다.
     * @param {list[Section]} category_sections 동일 카테고리의 섹션 목록
     * @param {Callable} build_articles 섹션별 아티클 노드 목록 생성 함수
     * @returns {list[dict]} 루트 섹션 노드(각 노드에 children 포함)
     */
    """
    if not category_sections:
        return []

    nodes_by_a_id: dict[int, dict[str, Any]] = {}
    for section in category_sections:
        nodes_by_a_id[section.a_id] = {
            "id": section.id,
            "a_id": section.a_id,
            "name": section.name,
            "parent_a_id": section.a_parent_section_id,
            "articles": build_articles(section),
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for section in category_sections:
        node = nodes_by_a_id[section.a_id]
        parent_a_id = section.a_parent_section_id
        if parent_a_id is not None and parent_a_id in nodes_by_a_id:
            nodes_by_a_id[parent_a_id]["children"].append(node)
        else:
            roots.append(node)

    _sort_section_nodes(roots)
    return roots


def _sort_section_nodes(nodes: list[dict[str, Any]]) -> None:
    nodes.sort(key=lambda item: str(item.get("name", "")).casefold())
    for node in nodes:
        children = node.get("children")
        if isinstance(children, list) and children:
            _sort_section_nodes(children)


def count_sections_in_nodes(nodes: list[dict[str, Any]]) -> int:
    """
    /**
     * 중첩 섹션 노드의 총 개수(루트+하위)를 센다.
     */
    """
    total = 0
    for node in nodes:
        total += 1
        children = node.get("children")
        if isinstance(children, list):
            total += count_sections_in_nodes(children)
    return total


def iter_sections_in_nodes(nodes: list[dict[str, Any]]):
    """
    /**
     * 중첩 섹션 노드를 선행 순회한다.
     */
    """
    for node in nodes:
        yield node
        children = node.get("children")
        if isinstance(children, list):
            yield from iter_sections_in_nodes(children)
