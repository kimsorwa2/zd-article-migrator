from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ZendeskApiOperation:
    """
    Zendesk API 카탈로그의 단일 operation 정의.

    @param id UI·localStorage 식별자 (product prefix 포함 권장)
    @param category 문서 대분류 (H2)
    @param group 문서 중분류 (H3)
    @param label UI 표시 라벨
    @param method HTTP 메서드
    @param path_template /api/v2/... 경로 템플릿
    @param path_params path placeholder 이름 목록
    @param doc_url 공식 레퍼런스 URL
    @param sample_body POST/PUT/PATCH 샘플 본문
    @param default_query 기본 쿼리 파라미터
    """

    id: str
    category: str
    group: str
    label: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_template: str
    doc_url: str
    path_params: tuple[str, ...] = ()
    sample_body: dict[str, Any] | None = None
    default_query: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ZendeskApiGroup:
    """카탈로그 중분류 그룹."""

    id: str
    label: str
    operations: tuple[ZendeskApiOperation, ...]


@dataclass(frozen=True, slots=True)
class ZendeskApiCategory:
    """카탈로그 대분류."""

    id: str
    label: str
    groups: tuple[ZendeskApiGroup, ...]


@dataclass(frozen=True, slots=True)
class ZendeskApiProduct:
    """Zendesk API capability 영역 (Ticketing, Help Center 등)."""

    id: str
    label: str
    doc_url: str
    categories: tuple[ZendeskApiCategory, ...]


def slugify_catalog_label(value: str) -> str:
    """라벨을 카탈로그 id용 slug로 변환한다."""
    normalized = value.strip().lower().replace(" ", "-")
    return "".join(char for char in normalized if char.isalnum() or char == "-")


def build_categories_from_operations(
    operations: tuple[ZendeskApiOperation, ...],
) -> tuple[ZendeskApiCategory, ...]:
    """
    flat operation 목록을 문서 대·중분류 계층으로 묶어 반환한다.

    @param operations product별 operation 튜플
    @returns 대분류 튜플
    """
    category_map: dict[str, dict[str, list[ZendeskApiOperation]]] = {}

    for operation in operations:
        category_map.setdefault(operation.category, {})
        category_map[operation.category].setdefault(operation.group, [])
        category_map[operation.category][operation.group].append(operation)

    categories: list[ZendeskApiCategory] = []
    for category_label, groups in category_map.items():
        group_items: list[ZendeskApiGroup] = []
        for group_label, group_operations in groups.items():
            group_id = f"{slugify_catalog_label(category_label)}-{slugify_catalog_label(group_label)}"
            group_items.append(
                ZendeskApiGroup(
                    id=group_id,
                    label=group_label,
                    operations=tuple(group_operations),
                )
            )
        categories.append(
            ZendeskApiCategory(
                id=slugify_catalog_label(category_label),
                label=category_label,
                groups=tuple(group_items),
            )
        )
    return tuple(categories)
