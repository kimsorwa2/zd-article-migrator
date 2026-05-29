from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article, Brand, Category, Instance, MigrationMapping, Section
from services.migration_service import MigrationService
from services.zendesk_client import ZendeskClient, ZendeskClientError


@dataclass(slots=True)
class DeletePreviewSummary:
    """
    /**
     * 삭제 미리보기 요약 정보를 표현한다.
     * @param {int} categories 삭제 예정 카테고리 수
     * @param {int} sections 삭제 예정 섹션 수
     * @param {int} articles 삭제 예정 아티클 수
     * @returns {None} 데이터 모델이므로 반환값 없음
     */
    """

    categories: int = 0
    sections: int = 0
    articles: int = 0


@dataclass(slots=True)
class DeleteFailedItem:
    """
    /**
     * 삭제에 실패한 매핑 항목 정보.
     */
    """

    mapping_id: int
    entity_type: str
    target_a_id: int
    error_message: str


@dataclass(slots=True)
class DeleteExecuteResult:
    """
    /**
     * 삭제 실행·재시도 결과(요약 + 실패 목록).
     */
    """

    summary: DeletePreviewSummary
    failed_items: list[DeleteFailedItem]


@dataclass(slots=True)
class DeleteSourceSelection:
    """
    /**
     * 삭제 API에 전달할 소스 Zendesk A ID 묶음.
     */
    """

    brand_a_ids: list[int]
    category_a_ids: list[int]
    section_a_ids: list[int]
    article_a_ids: list[int]


class DeleteService:
    """
    /**
     * 타겟 Zendesk 삭제 처리 및 매핑 정리 로직을 제공한다.
     * migrated 매핑이 있는 항목만 삭제한다.
     */
    """

    @staticmethod
    async def _get_target_instance(session: AsyncSession, target_instance_id: int) -> Instance:
        target = await session.get(Instance, target_instance_id)
        if target is None:
            raise ValueError("타겟 인스턴스를 찾을 수 없습니다.")
        return target

    @classmethod
    async def _get_migrated_mappings(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        entity_type: str,
        source_entity_ids: list[int],
    ) -> list[MigrationMapping]:
        if not source_entity_ids:
            return []

        query = select(MigrationMapping).where(
            MigrationMapping.source_instance_id == source_instance_id,
            MigrationMapping.target_instance_id == target_instance_id,
            MigrationMapping.entity_type == entity_type,
            MigrationMapping.source_entity_id.in_(source_entity_ids),
            MigrationMapping.status == "migrated",
        )
        return (await session.execute(query)).scalars().all()

    @classmethod
    async def resolve_source_selection(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        *,
        brand_a_ids: list[int],
        category_a_ids: list[int],
        section_a_ids: list[int],
        article_a_ids: list[int],
        target_category_a_ids: list[int],
        target_section_a_ids: list[int],
        target_article_a_ids: list[int],
    ) -> DeleteSourceSelection:
        """
        /**
         * 타겟 트리 선택을 소스 A ID로 확장하거나, 직접 전달된 소스 ID를 병합한다.
         * 카테고리·섹션 선택 시 하위 migrated 아티클·섹션도 포함한다.
         */
        """
        await MigrationService._get_instance(session=session, instance_id=source_instance_id)
        await cls._get_target_instance(session=session, target_instance_id=target_instance_id)

        mappings = (
            await session.execute(
                select(MigrationMapping).where(
                    MigrationMapping.source_instance_id == source_instance_id,
                    MigrationMapping.target_instance_id == target_instance_id,
                    MigrationMapping.status == "migrated",
                    MigrationMapping.target_entity_id.is_not(None),
                )
            )
        ).scalars().all()

        brand_by_target: dict[int, MigrationMapping] = {}
        category_by_target: dict[int, MigrationMapping] = {}
        section_by_target: dict[int, MigrationMapping] = {}
        article_by_target: dict[int, MigrationMapping] = {}

        for mapping in mappings:
            target_id = mapping.target_entity_id
            if target_id is None:
                continue
            if mapping.entity_type == "brand":
                brand_by_target[target_id] = mapping
            elif mapping.entity_type == "category":
                category_by_target[target_id] = mapping
            elif mapping.entity_type == "section":
                section_by_target[target_id] = mapping
            elif mapping.entity_type == "article":
                article_by_target[target_id] = mapping

        brands = (
            await session.execute(select(Brand).where(Brand.instance_id == source_instance_id))
        ).scalars().all()
        categories = (
            await session.execute(select(Category).where(Category.instance_id == source_instance_id))
        ).scalars().all()
        sections = (
            await session.execute(select(Section).where(Section.instance_id == source_instance_id))
        ).scalars().all()
        articles = (
            await session.execute(select(Article).where(Article.instance_id == source_instance_id))
        ).scalars().all()

        brand_a_to_id = {brand.a_brand_id: brand.id for brand in brands}
        categories_by_brand_id: dict[int, list[Category]] = {}
        for category in categories:
            categories_by_brand_id.setdefault(category.brand_id, []).append(category)

        sections_by_category_a_id: dict[int, list[Section]] = {}
        for section in sections:
            sections_by_category_a_id.setdefault(section.a_category_id, []).append(section)

        articles_by_section_a_id: dict[int, list[Article]] = {}
        for article in articles:
            articles_by_section_a_id.setdefault(article.a_section_id, []).append(article)

        migrated_brand_a: set[int] = set()
        migrated_category_a: set[int] = set()
        migrated_section_a: set[int] = set()
        migrated_article_a: set[int] = set()

        for mapping in mappings:
            if mapping.entity_type == "brand":
                migrated_brand_a.add(mapping.source_entity_id)
            elif mapping.entity_type == "category":
                migrated_category_a.add(mapping.source_entity_id)
            elif mapping.entity_type == "section":
                migrated_section_a.add(mapping.source_entity_id)
            elif mapping.entity_type == "article":
                migrated_article_a.add(mapping.source_entity_id)

        def expand_brand(brand_a_id: int) -> None:
            if brand_a_id not in migrated_brand_a:
                return
            migrated_brand_a.add(brand_a_id)
            brand_local_id = brand_a_to_id.get(brand_a_id)
            if brand_local_id is None:
                return
            for category in categories_by_brand_id.get(brand_local_id, []):
                if category.a_id in migrated_category_a:
                    expand_category(category.a_id)

        def expand_category(category_a_id: int) -> None:
            if category_a_id not in migrated_category_a:
                return
            migrated_category_a.add(category_a_id)
            for section in sections_by_category_a_id.get(category_a_id, []):
                if section.a_id in migrated_section_a:
                    expand_section(section.a_id)

        def expand_section(section_a_id: int) -> None:
            if section_a_id not in migrated_section_a:
                return
            migrated_section_a.add(section_a_id)
            for article in articles_by_section_a_id.get(section_a_id, []):
                if article.a_id in migrated_article_a:
                    migrated_article_a.add(article.a_id)

        for target_category_a_id in target_category_a_ids:
            mapping = brand_by_target.get(target_category_a_id)
            if mapping is not None:
                expand_brand(mapping.source_entity_id)

        for target_section_a_id in target_section_a_ids:
            category_mapping = category_by_target.get(target_section_a_id)
            if category_mapping is not None:
                expand_category(category_mapping.source_entity_id)
                continue
            section_mapping = section_by_target.get(target_section_a_id)
            if section_mapping is not None:
                expand_section(section_mapping.source_entity_id)

        for target_article_a_id in target_article_a_ids:
            mapping = article_by_target.get(target_article_a_id)
            if mapping is not None:
                migrated_article_a.add(mapping.source_entity_id)

        for brand_a_id in brand_a_ids:
            expand_brand(brand_a_id)
        for category_a_id in category_a_ids:
            expand_category(category_a_id)
        for section_a_id in section_a_ids:
            expand_section(section_a_id)
        for article_a_id in article_a_ids:
            if article_a_id in migrated_article_a:
                migrated_article_a.add(article_a_id)

        return DeleteSourceSelection(
            brand_a_ids=sorted(migrated_brand_a),
            category_a_ids=sorted(migrated_category_a),
            section_a_ids=sorted(migrated_section_a),
            article_a_ids=sorted(migrated_article_a),
        )

    @classmethod
    async def preview(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        brand_a_ids: list[int],
        category_a_ids: list[int],
        section_a_ids: list[int],
        article_a_ids: list[int],
        target_category_a_ids: list[int] | None = None,
        target_section_a_ids: list[int] | None = None,
        target_article_a_ids: list[int] | None = None,
        target_brand_id: int | None = None,
    ) -> DeletePreviewSummary:
        selection = await cls.resolve_source_selection(
            session=session,
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
            brand_a_ids=brand_a_ids,
            category_a_ids=category_a_ids,
            section_a_ids=section_a_ids,
            article_a_ids=article_a_ids,
            target_category_a_ids=target_category_a_ids or [],
            target_section_a_ids=target_section_a_ids or [],
            target_article_a_ids=target_article_a_ids or [],
        )
        await cls._get_target_instance(session=session, target_instance_id=target_instance_id)
        summary = DeletePreviewSummary()

        brand_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "brand", selection.brand_a_ids
        )
        category_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "category", selection.category_a_ids
        )
        section_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "section", selection.section_a_ids
        )
        article_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "article", selection.article_a_ids
        )

        summary.categories += len(brand_mappings)
        summary.sections += len(category_mappings) + len(section_mappings)
        summary.articles += len(article_mappings)
        return summary

    @classmethod
    async def execute(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        brand_a_ids: list[int],
        category_a_ids: list[int],
        section_a_ids: list[int],
        article_a_ids: list[int],
        target_category_a_ids: list[int] | None = None,
        target_section_a_ids: list[int] | None = None,
        target_article_a_ids: list[int] | None = None,
        target_brand_id: int | None = None,
    ) -> DeleteExecuteResult:
        selection = await cls.resolve_source_selection(
            session=session,
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
            brand_a_ids=brand_a_ids,
            category_a_ids=category_a_ids,
            section_a_ids=section_a_ids,
            article_a_ids=article_a_ids,
            target_category_a_ids=target_category_a_ids or [],
            target_section_a_ids=target_section_a_ids or [],
            target_article_a_ids=target_article_a_ids or [],
        )

        target_hc = await MigrationService._resolve_target_help_center(
            session=session,
            target_instance_id=target_instance_id,
            target_brand_id=target_brand_id,
        )

        brand_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "brand", selection.brand_a_ids
        )
        category_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "category", selection.category_a_ids
        )
        section_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "section", selection.section_a_ids
        )
        article_mappings = await cls._get_migrated_mappings(
            session, source_instance_id, target_instance_id, "article", selection.article_a_ids
        )

        result = await cls._delete_mappings(
            session=session,
            target_hc=target_hc,
            article_mappings=article_mappings,
            section_mappings=section_mappings,
            category_mappings=category_mappings,
            brand_mappings=brand_mappings,
        )
        await session.commit()
        return result

    @classmethod
    async def retry_failed(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        target_brand_id: int | None = None,
        mapping_ids: list[int] | None = None,
    ) -> DeleteExecuteResult:
        """
        /**
         * delete_error 상태 매핑에 대해 Zendesk 삭제를 다시 시도한다.
         */
        """
        await cls._get_target_instance(session=session, target_instance_id=target_instance_id)
        target_hc = await MigrationService._resolve_target_help_center(
            session=session,
            target_instance_id=target_instance_id,
            target_brand_id=target_brand_id,
        )

        query = select(MigrationMapping).where(
            MigrationMapping.source_instance_id == source_instance_id,
            MigrationMapping.target_instance_id == target_instance_id,
            MigrationMapping.status == "delete_error",
            MigrationMapping.target_entity_id.is_not(None),
        )
        if mapping_ids:
            query = query.where(MigrationMapping.id.in_(mapping_ids))

        failed_mappings = (await session.execute(query.order_by(MigrationMapping.id.asc()))).scalars().all()
        if not failed_mappings:
            return DeleteExecuteResult(summary=DeletePreviewSummary(), failed_items=[])

        brand_mappings = [item for item in failed_mappings if item.entity_type == "brand"]
        category_mappings = [item for item in failed_mappings if item.entity_type == "category"]
        section_mappings = [item for item in failed_mappings if item.entity_type == "section"]
        article_mappings = [item for item in failed_mappings if item.entity_type == "article"]

        result = await cls._delete_mappings(
            session=session,
            target_hc=target_hc,
            article_mappings=article_mappings,
            section_mappings=section_mappings,
            category_mappings=category_mappings,
            brand_mappings=brand_mappings,
        )
        await session.commit()
        return result

    @classmethod
    async def _delete_mappings(
        cls,
        *,
        session: AsyncSession,
        target_hc,
        article_mappings: list[MigrationMapping],
        section_mappings: list[MigrationMapping],
        category_mappings: list[MigrationMapping],
        brand_mappings: list[MigrationMapping],
    ) -> DeleteExecuteResult:
        """
        /**
         * 매핑 목록을 Zendesk에서 삭제한다(아티클 → 섹션 → 카테고리 순).
         */
        """
        summary = DeletePreviewSummary()
        failed_items: list[DeleteFailedItem] = []
        base_url = f"https://{target_hc.subdomain}.zendesk.com"

        async def delete_with_status(mapping: MigrationMapping, endpoint: str, counter: str) -> None:
            if mapping.target_entity_id is None:
                return
            try:
                await ZendeskClient.delete(
                    url=f"{base_url}{endpoint}",
                    email=target_hc.instance.email,
                    api_token=target_hc.instance.api_token,
                )
                await session.delete(mapping)
                if counter == "articles":
                    summary.articles += 1
                elif counter == "sections":
                    summary.sections += 1
                elif counter == "categories":
                    summary.categories += 1
            except ZendeskClientError as error:
                mapping.status = "delete_error"
                mapping.error_message = str(error)
                mapping.synced_at = datetime.now(UTC)
                failed_items.append(
                    DeleteFailedItem(
                        mapping_id=mapping.id,
                        entity_type=mapping.entity_type,
                        target_a_id=mapping.target_entity_id,
                        error_message=str(error),
                    )
                )

        for mapping in article_mappings:
            await delete_with_status(
                mapping, f"/api/v2/help_center/articles/{mapping.target_entity_id}.json", "articles"
            )

        for mapping in section_mappings:
            await delete_with_status(
                mapping, f"/api/v2/help_center/sections/{mapping.target_entity_id}.json", "sections"
            )

        for mapping in category_mappings:
            await delete_with_status(
                mapping, f"/api/v2/help_center/sections/{mapping.target_entity_id}.json", "sections"
            )

        for mapping in brand_mappings:
            await delete_with_status(
                mapping, f"/api/v2/help_center/categories/{mapping.target_entity_id}.json", "categories"
            )

        return DeleteExecuteResult(summary=summary, failed_items=failed_items)
