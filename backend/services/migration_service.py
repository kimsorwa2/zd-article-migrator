from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article, Brand, Category, Instance, MigrationMapping, Section
from services.migrate_progress import MigrateProgressTracker
from services.zendesk_client import ZendeskClient

DuplicatePolicy = Literal["skip", "update", "force"]


@dataclass(slots=True)
class MigrationSummary:
    """
    /**
     * 마이그레이션 실행 결과 요약 정보를 표현한다.
     * @param {int} brands 브랜드 처리 건수
     * @param {int} categories 카테고리 처리 건수
     * @param {int} sections 섹션 처리 건수
     * @param {int} articles 아티클 처리 건수
     * @returns {None} 데이터 모델이므로 반환값 없음
     */
    """

    brands: int = 0
    categories: int = 0
    sections: int = 0
    articles: int = 0


@dataclass(slots=True)
class TargetHelpCenter:
    """
    /**
     * 타겟 Zendesk Help Center API 호출에 사용할 인스턴스·브랜드 정보.
     * @param {Instance} instance 타겟 인스턴스(인증 정보)
     * @param {Brand} brand Help Center를 가진 타겟 브랜드
     * @param {str} subdomain Help Center API용 브랜드 서브도메인
     */
    """

    instance: Instance
    brand: Brand
    subdomain: str

    @property
    def base_url(self) -> str:
        return f"https://{self.subdomain}.zendesk.com/api/v2/help_center"


class MigrationService:
    """
    /**
     * A -> B 구조 기반 마이그레이션 1차 로직을 제공한다.
     * @returns {None} 서비스 클래스이므로 반환값 없음
     */
    """

    @staticmethod
    async def _get_instance(session: AsyncSession, instance_id: int) -> Instance:
        """
        /**
         * 인스턴스를 조회한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} instance_id 조회할 인스턴스 ID
         * @returns {Instance} 조회된 인스턴스 엔티티
         */
        """
        instance = await session.get(Instance, instance_id)
        if instance is None:
            raise ValueError("인스턴스를 찾을 수 없습니다.")
        return instance

    @staticmethod
    async def _upsert_mapping(
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        entity_type: str,
        source_entity_id: int,
        target_entity_id: int,
        status: str,
    ) -> None:
        """
        /**
         * migration_mappings 레코드를 생성하거나 갱신한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} source_instance_id 소스 인스턴스 ID
         * @param {int} target_instance_id 타겟 인스턴스 ID
         * @param {str} entity_type 엔티티 타입(brand/category/section/article)
         * @param {int} source_entity_id 소스 엔티티 ID
         * @param {int} target_entity_id 타겟 엔티티 ID
         * @param {str} status 매핑 상태값
         * @returns {None} 반환값 없음
         */
        """
        query = select(MigrationMapping).where(
            MigrationMapping.source_instance_id == source_instance_id,
            MigrationMapping.target_instance_id == target_instance_id,
            MigrationMapping.entity_type == entity_type,
            MigrationMapping.source_entity_id == source_entity_id,
        )
        mapping = await session.scalar(query)
        now = datetime.now(UTC)

        if mapping is None:
            mapping = MigrationMapping(
                source_instance_id=source_instance_id,
                target_instance_id=target_instance_id,
                entity_type=entity_type,
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                status=status,
                migrated_at=now,
                synced_at=now,
            )
            session.add(mapping)
            return

        mapping.target_entity_id = target_entity_id
        mapping.status = status
        mapping.synced_at = now
        if mapping.migrated_at is None:
            mapping.migrated_at = now
        mapping.error_message = None

    @classmethod
    async def _resolve_target_help_center(
        cls,
        session: AsyncSession,
        target_instance_id: int,
        target_brand_id: int | None,
    ) -> TargetHelpCenter:
        """
        /**
         * 타겟 인스턴스에서 Help Center API에 사용할 브랜드를 결정한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} target_instance_id 타겟 인스턴스 ID
         * @param {int | None} target_brand_id 선택한 타겟 브랜드 로컬 ID
         * @returns {TargetHelpCenter} 타겟 Help Center 호출 컨텍스트
         */
        """
        target = await cls._get_instance(session=session, instance_id=target_instance_id)
        brands = (
            await session.execute(
                select(Brand)
                .where(
                    Brand.instance_id == target.id,
                    Brand.is_selected.is_(True),
                    Brand.has_help_center.is_(True),
                )
                .order_by(Brand.name.asc())
            )
        ).scalars().all()

        if not brands:
            raise ValueError("타겟에 Help Center 브랜드가 없습니다. 인스턴스 메뉴에서 수집을 먼저 실행하세요.")

        if target_brand_id is not None:
            brand = next((item for item in brands if item.id == target_brand_id), None)
            if brand is None:
                raise ValueError("선택한 타겟 브랜드를 찾을 수 없습니다.")
        elif len(brands) == 1:
            brand = brands[0]
        else:
            raise ValueError("타겟에 브랜드가 여러 개입니다. 마이그레이션할 타겟 브랜드를 선택하세요.")

        subdomain = brand.subdomain.strip()
        if not subdomain:
            raise ValueError("타겟 브랜드 서브도메인이 비어 있습니다.")

        return TargetHelpCenter(instance=target, brand=brand, subdomain=subdomain)

    @staticmethod
    async def _load_target_categories(target_hc: TargetHelpCenter) -> dict[str, int]:
        """
        /**
         * 타겟 Zendesk 카테고리를 이름 기준 사전으로 조회한다.
         * @param {TargetHelpCenter} target_hc 타겟 Help Center 컨텍스트
         * @returns {dict[str, int]} 카테고리명 -> 타겟 카테고리 ID
         */
        """
        payload = await ZendeskClient.get_json(
            url=f"{target_hc.base_url}/categories.json",
            email=target_hc.instance.email,
            api_token=target_hc.instance.api_token,
        )
        categories = payload.get("categories", [])
        return {item["name"]: item["id"] for item in categories}

    @staticmethod
    async def _create_target_category(target_hc: TargetHelpCenter, name: str) -> int:
        """
        /**
         * 타겟 Zendesk에 카테고리를 생성한다.
         * @param {TargetHelpCenter} target_hc 타겟 Help Center 컨텍스트
         * @param {str} name 생성할 카테고리 이름
         * @returns {int} 생성된 타겟 카테고리 ID
         */
        """
        payload = await ZendeskClient.post_json(
            url=f"{target_hc.base_url}/categories.json",
            email=target_hc.instance.email,
            api_token=target_hc.instance.api_token,
            json={"category": {"name": name}},
        )
        return payload["category"]["id"]

    @staticmethod
    async def _create_target_section(
        target_hc: TargetHelpCenter,
        category_id: int,
        name: str,
        description: str | None,
        parent_section_id: int | None = None,
    ) -> int:
        """
        /**
         * 타겟 Zendesk에 섹션을 생성한다.
         * @param {Instance} target 타겟 인스턴스 정보
         * @param {int} category_id 생성 대상 카테고리 ID
         * @param {str} name 섹션 이름
         * @param {str | None} description 섹션 설명
         * @param {int | None} parent_section_id 하위 섹션일 경우 부모 섹션 ID
         * @returns {int} 생성된 타겟 섹션 ID
         */
        """
        section_body: dict[str, object] = {"name": name}
        if description:
            section_body["description"] = description
        if parent_section_id is not None:
            section_body["parent_section_id"] = parent_section_id

        payload = await ZendeskClient.post_json(
            url=f"{target_hc.base_url}/categories/{category_id}/sections.json",
            email=target_hc.instance.email,
            api_token=target_hc.instance.api_token,
            json={"section": section_body},
        )
        return payload["section"]["id"]

    @staticmethod
    async def _create_target_article(target_hc: TargetHelpCenter, section_id: int, article: Article) -> int:
        """
        /**
         * 타겟 Zendesk에 아티클을 생성한다.
         * @param {Instance} target 타겟 인스턴스 정보
         * @param {int} section_id 생성 대상 타겟 섹션 ID
         * @param {Article} article 소스 아티클 엔티티
         * @returns {int} 생성된 타겟 아티클 ID
         */
        """
        payload = await ZendeskClient.post_json(
            url=f"{target_hc.base_url}/sections/{section_id}/articles.json",
            email=target_hc.instance.email,
            api_token=target_hc.instance.api_token,
            json={
                "article": {
                    "title": article.title,
                    "body": article.body or "",
                    "draft": article.draft,
                    "label_names": article.label_names or [],
                }
            },
        )
        return payload["article"]["id"]

    @staticmethod
    async def _update_target_article(
        target_hc: TargetHelpCenter,
        target_article_id: int,
        article: Article,
        body: str | None = None,
    ) -> None:
        """
        /**
         * 기존 타겟 아티클을 업데이트한다.
         * @param {Instance} target 타겟 인스턴스 정보
         * @param {int} target_article_id 수정할 타겟 아티클 ID
         * @param {Article} article 소스 아티클 엔티티
         * @returns {None} 반환값 없음
         */
        """
        await ZendeskClient.patch_json(
            url=f"{target_hc.base_url}/articles/{target_article_id}.json",
            email=target_hc.instance.email,
            api_token=target_hc.instance.api_token,
            json={
                "article": {
                    "title": article.title,
                    "body": body if body is not None else (article.body or ""),
                    "draft": article.draft,
                    "label_names": article.label_names or [],
                }
            },
        )

    @staticmethod
    async def _sync_attachments_and_replace_body(
        source: Instance,
        target_hc: TargetHelpCenter,
        source_subdomain: str,
        source_article_id: int,
        target_article_id: int,
        body: str | None,
    ) -> str | None:
        """
        /**
         * 소스 아티클 첨부파일을 타겟으로 재업로드하고 본문 URL을 치환한다.
         * @param {Instance} source 소스 인스턴스 정보
         * @param {Instance} target 타겟 인스턴스 정보
         * @param {str} source_subdomain 소스 브랜드 서브도메인
         * @param {int} source_article_id 소스 아티클 A ID
         * @param {int} target_article_id 타겟 아티클 ID
         * @param {str | None} body 기존 아티클 본문
         * @returns {str | None} 첨부파일 URL이 치환된 본문
         */
        """
        if not body:
            return body

        attachments_payload = await ZendeskClient.get_json(
            url=f"https://{source_subdomain}.zendesk.com/api/v2/help_center/articles/{source_article_id}/attachments.json",
            email=source.email,
            api_token=source.api_token,
        )
        attachments = attachments_payload.get("article_attachments", [])
        updated_body = body

        # 첨부파일을 하나씩 재업로드하고 본문 내 원본 URL을 새 URL로 대체한다.
        for attachment in attachments:
            source_url = attachment.get("content_url")
            if not source_url:
                continue

            binary = await ZendeskClient.get_bytes(
                url=source_url,
                email=source.email,
                api_token=source.api_token,
            )
            upload_payload = await ZendeskClient.upload_attachment(
                article_id=target_article_id,
                filename=attachment.get("file_name", f"attachment-{source_article_id}"),
                content_type=attachment.get("content_type", "application/octet-stream"),
                content=binary,
                target_subdomain=target_hc.subdomain,
                email=target_hc.instance.email,
                api_token=target_hc.instance.api_token,
            )
            target_url = upload_payload.get("article_attachment", {}).get("content_url")
            if not target_url:
                continue

            updated_body = updated_body.replace(source_url, target_url)

            # HTML 이스케이프 형태로 들어간 URL도 치환해 누락을 줄인다.
            escaped_source_url = re.sub(r"&", "&amp;", source_url)
            escaped_target_url = re.sub(r"&", "&amp;", target_url)
            updated_body = updated_body.replace(escaped_source_url, escaped_target_url)

        return updated_body

    @classmethod
    async def execute(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        duplicate_policy: DuplicatePolicy,
        brand_ids: list[int],
        category_ids: list[int],
        section_ids: list[int],
        article_ids: list[int],
        target_brand_id: int | None = None,
        report_progress: bool = False,
    ) -> MigrationSummary:
        """
        /**
         * 선택한 엔티티를 순서대로 타겟 Zendesk로 마이그레이션한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} source_instance_id 소스 인스턴스 ID
         * @param {int} target_instance_id 타겟 인스턴스 ID
         * @param {"skip" | "update" | "force"} duplicate_policy 중복 처리 정책
         * @param {list[int]} brand_ids 선택 브랜드 로컬 ID 목록
         * @param {list[int]} category_ids 선택 카테고리 로컬 ID 목록
         * @param {list[int]} section_ids 선택 섹션 로컬 ID 목록
         * @param {list[int]} article_ids 선택 아티클 로컬 ID 목록
         * @param {int | None} target_brand_id 타겟 Help Center 브랜드 로컬 ID
         * @returns {MigrationSummary} 마이그레이션 처리 요약
         */
        """
        if source_instance_id == target_instance_id:
            raise ValueError("소스와 타겟 인스턴스는 서로 달라야 합니다.")

        source = await cls._get_instance(session=session, instance_id=source_instance_id)
        target_hc = await cls._resolve_target_help_center(
            session=session,
            target_instance_id=target_instance_id,
            target_brand_id=target_brand_id,
        )
        target = target_hc.instance

        summary = MigrationSummary()

        target_categories_by_name = await cls._load_target_categories(target_hc)
        brand_mapping: dict[int, int] = {}

        brand_query = select(Brand).where(Brand.instance_id == source.id)
        if brand_ids:
            brand_query = brand_query.where(Brand.id.in_(brand_ids))
        selected_brands = (await session.execute(brand_query.order_by(Brand.id.asc()))).scalars().all()

        category_target_section_map: dict[int, int] = {}
        category_query = select(Category).where(Category.instance_id == source.id)
        if brand_ids:
            category_query = category_query.where(Category.brand_id.in_(brand_ids))
        if category_ids:
            category_query = category_query.where(Category.id.in_(category_ids))
        selected_categories = (await session.execute(category_query.order_by(Category.id.asc()))).scalars().all()
        category_a_to_target_category_id: dict[int, int] = {}
        category_a_to_brand_subdomain: dict[int, str] = {}

        section_query = select(Section).where(Section.instance_id == source.id)
        if category_ids:
            category_a_ids_for_filter = [category.a_id for category in selected_categories]
            if category_a_ids_for_filter:
                section_query = section_query.where(Section.a_category_id.in_(category_a_ids_for_filter))
        if section_ids:
            section_query = section_query.where(Section.id.in_(section_ids))
        selected_sections = (await session.execute(section_query.order_by(Section.id.asc()))).scalars().all()

        section_target_map: dict[int, int] = {}
        section_a_to_source_subdomain: dict[int, str] = {}

        article_query = select(Article).where(Article.instance_id == source.id)
        if section_ids:
            section_a_ids_for_filter = [section.a_id for section in selected_sections]
            if section_a_ids_for_filter:
                article_query = article_query.where(Article.a_section_id.in_(section_a_ids_for_filter))
        if article_ids:
            article_query = article_query.where(Article.id.in_(article_ids))
        selected_articles = (await session.execute(article_query.order_by(Article.id.asc()))).scalars().all()

        progress_step = 0
        total_steps = max(
            1,
            len(selected_brands)
            + len(selected_categories)
            + len(selected_sections)
            + len(selected_articles),
        )

        async def _progress_tick(phase: str, message: str) -> None:
            nonlocal progress_step
            if not report_progress:
                return
            progress_step += 1
            await MigrateProgressTracker.update_step(
                source_instance_id,
                target_instance_id,
                current_step=progress_step,
                phase=phase,
                message=message,
            )

        # 1) 브랜드 -> 타겟 카테고리
        for brand in selected_brands:
            target_category_id = target_categories_by_name.get(brand.name)
            if target_category_id is None:
                target_category_id = await cls._create_target_category(target_hc, brand.name)
                target_categories_by_name[brand.name] = target_category_id

            brand_mapping[brand.id] = target_category_id
            await cls._upsert_mapping(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="brand",
                source_entity_id=brand.a_brand_id,
                target_entity_id=target_category_id,
                status="migrated",
            )
            summary.brands += 1
            await _progress_tick("brand", f"브랜드 → 카테고리: {brand.name}")

        # 2) A 카테고리 -> B 상위 섹션
        for category in selected_categories:
            parent_category_id = brand_mapping.get(category.brand_id)
            if parent_category_id is None:
                continue

            category_a_to_target_category_id[category.a_id] = parent_category_id
            source_brand = next((brand for brand in selected_brands if brand.id == category.brand_id), None)
            if source_brand is not None:
                category_a_to_brand_subdomain[category.a_id] = source_brand.subdomain
            target_section_id = await cls._create_target_section(
                target_hc,
                parent_category_id,
                category.name,
                None,
                None,
            )
            category_target_section_map[category.a_id] = target_section_id
            await cls._upsert_mapping(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="category",
                source_entity_id=category.a_id,
                target_entity_id=target_section_id,
                status="migrated",
            )
            summary.categories += 1
            await _progress_tick("category", f"카테고리 → 섹션: {category.name}")

        # 3) A 섹션 -> B 하위 섹션
        for section in selected_sections:
            parent_top_section_id = category_target_section_map.get(section.a_category_id)
            if parent_top_section_id is None:
                continue
            target_category_id = category_a_to_target_category_id.get(section.a_category_id)
            if target_category_id is None:
                continue

            target_section_id = await cls._create_target_section(
                target_hc,
                target_category_id,
                section.name,
                section.description,
                parent_top_section_id,
            )
            section_target_map[section.a_id] = target_section_id
            source_subdomain = category_a_to_brand_subdomain.get(section.a_category_id, source.subdomain)
            section_a_to_source_subdomain[section.a_id] = source_subdomain
            await cls._upsert_mapping(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="section",
                source_entity_id=section.a_id,
                target_entity_id=target_section_id,
                status="migrated",
            )
            summary.sections += 1
            await _progress_tick("section", f"섹션 → 하위 섹션: {section.name}")

        # 4) 아티클 생성/업데이트
        for article in selected_articles:
            target_section_id = section_target_map.get(article.a_section_id)
            if target_section_id is None:
                continue

            existing_mapping = await session.scalar(
                select(MigrationMapping).where(
                    MigrationMapping.source_instance_id == source.id,
                    MigrationMapping.target_instance_id == target.id,
                    MigrationMapping.entity_type == "article",
                    MigrationMapping.source_entity_id == article.a_id,
                )
            )

            if existing_mapping is not None and existing_mapping.target_entity_id is not None:
                if duplicate_policy == "skip":
                    continue
                if duplicate_policy in {"update", "force"}:
                    source_subdomain = section_a_to_source_subdomain.get(article.a_section_id, source.subdomain)
                    replaced_body = await cls._sync_attachments_and_replace_body(
                        source=source,
                        target_hc=target_hc,
                        source_subdomain=source_subdomain,
                        source_article_id=article.a_id,
                        target_article_id=existing_mapping.target_entity_id,
                        body=article.body,
                    )
                    await cls._update_target_article(
                        target_hc,
                        existing_mapping.target_entity_id,
                        article,
                        replaced_body,
                    )
                    await cls._upsert_mapping(
                        session=session,
                        source_instance_id=source.id,
                        target_instance_id=target.id,
                        entity_type="article",
                        source_entity_id=article.a_id,
                        target_entity_id=existing_mapping.target_entity_id,
                        status="migrated",
                    )
                    summary.articles += 1
                continue

            target_article_id = await cls._create_target_article(
                target_hc,
                target_section_id,
                article,
            )
            source_subdomain = section_a_to_source_subdomain.get(article.a_section_id, source.subdomain)
            replaced_body = await cls._sync_attachments_and_replace_body(
                source=source,
                target_hc=target_hc,
                source_subdomain=source_subdomain,
                source_article_id=article.a_id,
                target_article_id=target_article_id,
                body=article.body,
            )
            if replaced_body is not None and replaced_body != (article.body or ""):
                await cls._update_target_article(
                    target_hc,
                    target_article_id,
                    article,
                    replaced_body,
                )
            await cls._upsert_mapping(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="article",
                source_entity_id=article.a_id,
                target_entity_id=target_article_id,
                status="migrated",
            )
            summary.articles += 1
            await _progress_tick("article", f"아티클 처리: {article.title[:60]}")

        await session.commit()
        return summary

    @classmethod
    async def get_target_overlay(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
    ) -> dict:
        """
        /**
         * 타겟 Help Center 트리 하이라이트·삭제용 migrated 매핑 정보를 반환한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} source_instance_id 소스 인스턴스 ID
         * @param {int} target_instance_id 타겟 인스턴스 ID
         * @returns {dict} 타겟 Zendesk A ID 기준 오버레이 맵
         */
        """
        await cls._get_instance(session=session, instance_id=source_instance_id)
        await cls._get_instance(session=session, instance_id=target_instance_id)

        mappings = (
            await session.execute(
                select(MigrationMapping).where(
                    MigrationMapping.source_instance_id == source_instance_id,
                    MigrationMapping.target_instance_id == target_instance_id,
                    MigrationMapping.status.in_(("migrated", "delete_error")),
                    MigrationMapping.target_entity_id.is_not(None),
                )
            )
        ).scalars().all()

        migrated_category_a_ids: list[int] = []
        migrated_section_a_ids: list[int] = []
        migrated_article_a_ids: list[int] = []
        delete_error_category_a_ids: list[int] = []
        delete_error_section_a_ids: list[int] = []
        delete_error_article_a_ids: list[int] = []
        items: list[dict] = []
        delete_error_items: list[dict] = []

        for mapping in mappings:
            target_a_id = mapping.target_entity_id
            if target_a_id is None:
                continue
            item = {
                "mapping_id": mapping.id,
                "mapping_entity_type": mapping.entity_type,
                "source_a_id": mapping.source_entity_id,
                "target_a_id": target_a_id,
                "status": mapping.status,
                "error_message": mapping.error_message,
            }
            items.append(item)

            if mapping.status == "delete_error":
                delete_error_items.append(item)
                if mapping.entity_type == "brand":
                    delete_error_category_a_ids.append(target_a_id)
                elif mapping.entity_type in {"category", "section"}:
                    delete_error_section_a_ids.append(target_a_id)
                elif mapping.entity_type == "article":
                    delete_error_article_a_ids.append(target_a_id)
                continue

            if mapping.entity_type == "brand":
                migrated_category_a_ids.append(target_a_id)
            elif mapping.entity_type in {"category", "section"}:
                migrated_section_a_ids.append(target_a_id)
            elif mapping.entity_type == "article":
                migrated_article_a_ids.append(target_a_id)

        return {
            "source_instance_id": source_instance_id,
            "target_instance_id": target_instance_id,
            "items": items,
            "migrated_target_category_a_ids": sorted(set(migrated_category_a_ids)),
            "migrated_target_section_a_ids": sorted(set(migrated_section_a_ids)),
            "migrated_target_article_a_ids": sorted(set(migrated_article_a_ids)),
            "delete_error_target_category_a_ids": sorted(set(delete_error_category_a_ids)),
            "delete_error_target_section_a_ids": sorted(set(delete_error_section_a_ids)),
            "delete_error_target_article_a_ids": sorted(set(delete_error_article_a_ids)),
            "delete_error_items": delete_error_items,
        }

    @classmethod
    async def get_selection_tree(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
    ) -> list[dict]:
        """
        /**
         * 소스 인스턴스 데이터와 매핑 상태를 결합한 선택 트리를 구성한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} source_instance_id 소스 인스턴스 ID
         * @param {int} target_instance_id 타겟 인스턴스 ID
         * @returns {list[dict]} 브랜드 루트 기반 중첩 트리 데이터
         */
        """
        source = await cls._get_instance(session=session, instance_id=source_instance_id)
        await cls._get_instance(session=session, instance_id=target_instance_id)

        mappings = (
            await session.execute(
                select(MigrationMapping).where(
                    MigrationMapping.source_instance_id == source.id,
                    MigrationMapping.target_instance_id == target_instance_id,
                )
            )
        ).scalars().all()
        status_map = {(mapping.entity_type, mapping.source_entity_id): mapping.status for mapping in mappings}

        brands = (
            await session.execute(
                select(Brand).where(Brand.instance_id == source.id, Brand.is_selected.is_(True)).order_by(Brand.name.asc())
            )
        ).scalars().all()
        categories = (
            await session.execute(select(Category).where(Category.instance_id == source.id).order_by(Category.name.asc()))
        ).scalars().all()
        sections = (
            await session.execute(select(Section).where(Section.instance_id == source.id).order_by(Section.name.asc()))
        ).scalars().all()
        articles = (
            await session.execute(select(Article).where(Article.instance_id == source.id).order_by(Article.title.asc()))
        ).scalars().all()

        categories_by_brand: dict[int, list[Category]] = {}
        for category in categories:
            categories_by_brand.setdefault(category.brand_id, []).append(category)

        sections_by_category_a_id: dict[int, list[Section]] = {}
        for section in sections:
            sections_by_category_a_id.setdefault(section.a_category_id, []).append(section)

        articles_by_section_a_id: dict[int, list[Article]] = {}
        for article in articles:
            articles_by_section_a_id.setdefault(article.a_section_id, []).append(article)

        tree: list[dict] = []

        # 브랜드 -> 카테고리 -> 섹션 -> 아티클 순서로 선택 트리 데이터를 구성한다.
        for brand in brands:
            brand_node = {
                "id": brand.id,
                "a_brand_id": brand.a_brand_id,
                "name": brand.name,
                "status": status_map.get(("brand", brand.a_brand_id), "unmapped"),
                "categories": [],
            }

            for category in categories_by_brand.get(brand.id, []):
                category_node = {
                    "id": category.id,
                    "a_id": category.a_id,
                    "name": category.name,
                    "status": status_map.get(("category", category.a_id), "unmapped"),
                    "sections": [],
                }

                for section in sections_by_category_a_id.get(category.a_id, []):
                    section_node = {
                        "id": section.id,
                        "a_id": section.a_id,
                        "name": section.name,
                        "status": status_map.get(("section", section.a_id), "unmapped"),
                        "articles": [],
                    }

                    for article in articles_by_section_a_id.get(section.a_id, []):
                        section_node["articles"].append(
                            {
                                "id": article.id,
                                "a_id": article.a_id,
                                "title": article.title,
                                "status": status_map.get(("article", article.a_id), "unmapped"),
                            }
                        )

                    category_node["sections"].append(section_node)

                brand_node["categories"].append(category_node)

            tree.append(brand_node)

        return tree
