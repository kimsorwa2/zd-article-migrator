from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article, Brand, Category, Instance, MigrationMapping, Section
from services.fetch_service import FetchService
from services.migrate_progress import MigrateProgressTracker
from services.zendesk_oauth_service import ZendeskOAuthError, ZendeskOAuthService
from services.zendesk_client import ZendeskClientError

DuplicatePolicy = Literal["skip", "update", "force"]
MigrateLogAction = Literal["created", "updated", "confirmed"]

# 작업 로그 조사(이/가) — 엔티티 유형별 고정
_MIGRATE_LOG_PARTICLE: dict[str, str] = {
    "category": "가",
    "brand": "가",
    "section": "이",
    "article": "이",
}
_MIGRATE_LOG_LABEL: dict[str, str] = {
    "category": "카테고리",
    "brand": "브랜드",
    "section": "섹션",
    "article": "아티클",
}
_MIGRATE_LOG_VERB: dict[MigrateLogAction, str] = {
    "created": "생성되었습니다",
    "updated": "갱신되었습니다",
    "confirmed": "확인되었습니다",
}

# 본문 HTML 내 Zendesk 인라인 첨부 경로 (예: /hc/article_attachments/29932965795737)
INLINE_ARTICLE_ATTACHMENT_URL_PATTERN = re.compile(
    r"https?://[^\"'>\s]+/hc/article_attachments/(\d+)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class MigrationScope:
    """
    /**
     * 마이그레이션 실행에 실제로 포함할 소스 엔티티 집합.
     * 아티클만 선택한 경우 해당 아티클의 섹션·카테고리·브랜드만 포함한다.
     */
    """

    brands: list[Brand]
    categories: list[Category]
    sections: list[Section]
    articles: list[Article]


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
    articles_skipped: int = 0
    scope_categories: int = 0
    scope_sections: int = 0
    scope_articles: int = 0


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

    session: AsyncSession
    instance: Instance
    brand: Brand
    subdomain: str
    allowed_locales: frozenset[str] = field(default_factory=lambda: frozenset({"ko", "en-us"}))
    default_locale: str = "ko"

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
    def _build_migrate_log_line(
        *,
        name: str,
        entity_type: str,
        entity_id: int,
        action: MigrateLogAction = "created",
    ) -> str:
        """
        /**
         * 마이그레이션 작업 로그 한 줄 문장을 만든다.
         * 예: 「A 카테고리(id:1234)가 생성되었습니다.」
         * @param {str} name 엔티티 표시 이름
         * @param {str} entity_type category | brand | section | article
         * @param {int} entity_id Zendesk A ID(타겟 기준)
         * @param {MigrateLogAction} action created | updated | confirmed
         * @returns {str} 사용자용 로그 문장
         */
        """
        label = _MIGRATE_LOG_LABEL.get(entity_type, entity_type)
        particle = _MIGRATE_LOG_PARTICLE.get(entity_type, "가")
        verb = _MIGRATE_LOG_VERB.get(action, _MIGRATE_LOG_VERB["created"])
        display_name = name.strip() or label
        return f"{display_name} {label}(id:{entity_id}){particle} {verb}."

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

    @staticmethod
    async def _upsert_target_category_snapshot(
        session: AsyncSession,
        *,
        target_instance_id: int,
        target_brand_id: int,
        target_category_a_id: int,
        name: str,
        locale: str | None,
    ) -> Category:
        """
        /**
         * 마이그레이션으로 생성·확정된 타겟 카테고리를 로컬 DB에 저장한다.
         * @returns {Category} 저장된 카테고리 엔티티
         */
        """
        row = await session.scalar(
            select(Category).where(
                Category.instance_id == target_instance_id,
                Category.a_id == target_category_a_id,
            )
        )
        if row is None:
            row = Category(
                instance_id=target_instance_id,
                brand_id=target_brand_id,
                a_id=target_category_a_id,
                name=name,
                locale=locale,
            )
            session.add(row)
        else:
            row.brand_id = target_brand_id
            row.name = name
            row.locale = locale
        return row

    @staticmethod
    async def _upsert_target_section_snapshot(
        session: AsyncSession,
        *,
        target_instance_id: int,
        target_category_a_id: int,
        target_section_a_id: int,
        name: str,
        description: str | None,
        locale: str | None,
    ) -> Section:
        """
        /**
         * 마이그레이션으로 생성·확정된 타겟 섹션을 로컬 DB에 저장한다.
         * @returns {Section} 저장된 섹션 엔티티
         */
        """
        row = await session.scalar(
            select(Section).where(
                Section.instance_id == target_instance_id,
                Section.a_id == target_section_a_id,
            )
        )
        if row is None:
            row = Section(
                instance_id=target_instance_id,
                a_id=target_section_a_id,
                a_category_id=target_category_a_id,
                name=name,
                description=description,
                locale=locale,
            )
            session.add(row)
        else:
            row.a_category_id = target_category_a_id
            row.name = name
            row.description = description
            row.locale = locale
        return row

    @staticmethod
    def _build_target_article_html_url(
        *,
        brand_subdomain: str,
        target_article_a_id: int,
        locale: str | None,
        draft: bool,
        zendesk_html_url: str | None = None,
    ) -> str:
        """
        /**
         * 타겟 Help Center 아티클 URL을 만든다. 소스 인스턴스 html_url은 사용하지 않는다.
         * @param {str | None} zendesk_html_url 타겟 Zendesk API가 반환한 html_url(있으면 우선)
         * @returns {str} 타겟 브랜드·아티클 ID 기준 URL
         */
        """
        if zendesk_html_url and brand_subdomain in zendesk_html_url:
            return zendesk_html_url
        return FetchService._build_article_html_url(
            brand_subdomain=brand_subdomain,
            article_a_id=target_article_a_id,
            locale=locale,
            draft=draft,
        )

    @classmethod
    async def _upsert_target_article_snapshot(
        cls,
        session: AsyncSession,
        *,
        target_instance_id: int,
        target_section_a_id: int,
        target_article_a_id: int,
        article: Article,
        brand_subdomain: str,
        article_locale: str | None = None,
        zendesk_html_url: str | None = None,
    ) -> Article:
        """
        /**
         * 마이그레이션으로 생성·확정된 타겟 아티클을 로컬 DB에 저장한다.
         * @returns {Article} 저장된 아티클 엔티티
         */
        """
        row = await session.scalar(
            select(Article).where(
                Article.instance_id == target_instance_id,
                Article.a_id == target_article_a_id,
            )
        )
        locale_for_url = article_locale if article_locale is not None else article.locale
        html_url = cls._build_target_article_html_url(
            brand_subdomain=brand_subdomain,
            target_article_a_id=target_article_a_id,
            locale=locale_for_url,
            draft=article.draft,
            zendesk_html_url=zendesk_html_url,
        )
        if row is None:
            row = Article(
                instance_id=target_instance_id,
                a_id=target_article_a_id,
                a_section_id=target_section_a_id,
                title=article.title,
                body=article.body,
                locale=article.locale,
                label_names=article.label_names,
                draft=article.draft,
                html_url=html_url,
                has_attachments=article.has_attachments,
            )
            session.add(row)
        else:
            row.a_section_id = target_section_a_id
            row.title = article.title
            row.body = article.body
            row.locale = article.locale
            row.label_names = article.label_names
            row.draft = article.draft
            row.html_url = html_url
            row.has_attachments = article.has_attachments
        return row

    @staticmethod
    async def _get_migrated_target_id(
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        entity_type: str,
        source_entity_id: int,
    ) -> int | None:
        """
        /**
         * 이미 마이그레이션된 엔티티의 타겟 Zendesk ID를 조회한다.
         * @returns {int | None} 타겟 A ID, 없으면 None
         */
        """
        mapping = await session.scalar(
            select(MigrationMapping).where(
                MigrationMapping.source_instance_id == source_instance_id,
                MigrationMapping.target_instance_id == target_instance_id,
                MigrationMapping.entity_type == entity_type,
                MigrationMapping.source_entity_id == source_entity_id,
                MigrationMapping.status == "migrated",
                MigrationMapping.target_entity_id.is_not(None),
            )
        )
        if mapping is None or mapping.target_entity_id is None:
            return None
        return mapping.target_entity_id

    @classmethod
    async def _resolve_migration_scope(
        cls,
        session: AsyncSession,
        source: Instance,
        brand_ids: list[int],
        category_ids: list[int],
        section_ids: list[int],
        article_ids: list[int],
    ) -> MigrationScope:
        """
        /**
         * UI 선택을 실제 마이그레이션 대상으로 축소·보완한다.
         * - 아티클만 선택: 해당 아티클 + 부모 섹션/카테고리/브랜드만
         * - 섹션만 선택: 해당 섹션의 모든 아티클 + 부모
         * - 카테고리/브랜드만 선택: 하위 전체 포함
         */
        """
        instance_id = source.id
        if not (brand_ids or category_ids or section_ids or article_ids):
            raise ValueError("마이그레이션할 항목을 하나 이상 선택하세요.")

        articles_by_id: dict[int, Article] = {}
        sections_by_id: dict[int, Section] = {}
        categories_by_id: dict[int, Category] = {}
        brands_by_id: dict[int, Brand] = {}

        leaf_is_article = bool(article_ids)
        leaf_is_section = bool(section_ids) and not article_ids
        leaf_is_category = bool(category_ids) and not section_ids and not article_ids
        leaf_is_brand = bool(brand_ids) and not category_ids and not section_ids and not article_ids

        if leaf_is_article:
            for row in (
                await session.execute(
                    select(Article)
                    .where(Article.instance_id == instance_id, Article.id.in_(article_ids))
                    .order_by(Article.id.asc())
                )
            ).scalars().all():
                articles_by_id[row.id] = row

        elif leaf_is_section:
            for section in (
                await session.execute(
                    select(Section)
                    .where(Section.instance_id == instance_id, Section.id.in_(section_ids))
                    .order_by(Section.id.asc())
                )
            ).scalars().all():
                sections_by_id[section.id] = section

            section_a_ids = [item.a_id for item in sections_by_id.values()]
            if section_a_ids:
                for row in (
                    await session.execute(
                        select(Article)
                        .where(Article.instance_id == instance_id, Article.a_section_id.in_(section_a_ids))
                        .order_by(Article.id.asc())
                    )
                ).scalars().all():
                    articles_by_id[row.id] = row

        elif leaf_is_category:
            category_query = select(Category).where(
                Category.instance_id == instance_id,
                Category.id.in_(category_ids),
            )
            if brand_ids:
                category_query = category_query.where(Category.brand_id.in_(brand_ids))

            for category in (await session.execute(category_query.order_by(Category.id.asc()))).scalars().all():
                categories_by_id[category.id] = category

            category_a_ids = [item.a_id for item in categories_by_id.values()]
            if category_a_ids:
                for section in (
                    await session.execute(
                        select(Section)
                        .where(Section.instance_id == instance_id, Section.a_category_id.in_(category_a_ids))
                        .order_by(Section.id.asc())
                    )
                ).scalars().all():
                    sections_by_id[section.id] = section

                section_a_ids = [item.a_id for item in sections_by_id.values()]
                if section_a_ids:
                    for row in (
                        await session.execute(
                            select(Article)
                            .where(Article.instance_id == instance_id, Article.a_section_id.in_(section_a_ids))
                            .order_by(Article.id.asc())
                        )
                    ).scalars().all():
                        articles_by_id[row.id] = row

        elif leaf_is_brand:
            for brand in (
                await session.execute(
                    select(Brand)
                    .where(Brand.instance_id == instance_id, Brand.id.in_(brand_ids))
                    .order_by(Brand.id.asc())
                )
            ).scalars().all():
                brands_by_id[brand.id] = brand

            brand_local_ids = list(brands_by_id.keys())
            if brand_local_ids:
                for category in (
                    await session.execute(
                        select(Category)
                        .where(Category.instance_id == instance_id, Category.brand_id.in_(brand_local_ids))
                        .order_by(Category.id.asc())
                    )
                ).scalars().all():
                    categories_by_id[category.id] = category

                category_a_ids = [item.a_id for item in categories_by_id.values()]
                if category_a_ids:
                    for section in (
                        await session.execute(
                            select(Section)
                            .where(Section.instance_id == instance_id, Section.a_category_id.in_(category_a_ids))
                            .order_by(Section.id.asc())
                        )
                    ).scalars().all():
                        sections_by_id[section.id] = section

                    section_a_ids = [item.a_id for item in sections_by_id.values()]
                    if section_a_ids:
                        for row in (
                            await session.execute(
                                select(Article)
                                .where(Article.instance_id == instance_id, Article.a_section_id.in_(section_a_ids))
                                .order_by(Article.id.asc())
                            )
                        ).scalars().all():
                            articles_by_id[row.id] = row

        # 아티클 선택 시 부모 섹션만 역추적(다른 섹션은 포함하지 않음)
        if articles_by_id:
            needed_section_a_ids = {item.a_section_id for item in articles_by_id.values()}
            if needed_section_a_ids:
                for section in (
                    await session.execute(
                        select(Section)
                        .where(Section.instance_id == instance_id, Section.a_id.in_(needed_section_a_ids))
                        .order_by(Section.id.asc())
                    )
                ).scalars().all():
                    sections_by_id[section.id] = section

        if sections_by_id:
            needed_category_a_ids = {item.a_category_id for item in sections_by_id.values()}
            if needed_category_a_ids:
                for category in (
                    await session.execute(
                        select(Category)
                        .where(Category.instance_id == instance_id, Category.a_id.in_(needed_category_a_ids))
                        .order_by(Category.id.asc())
                    )
                ).scalars().all():
                    categories_by_id[category.id] = category

        if categories_by_id:
            needed_brand_ids = {item.brand_id for item in categories_by_id.values()}
            missing_brand_ids = needed_brand_ids - set(brands_by_id.keys())
            if missing_brand_ids:
                for brand in (
                    await session.execute(
                        select(Brand)
                        .where(Brand.instance_id == instance_id, Brand.id.in_(missing_brand_ids))
                        .order_by(Brand.id.asc())
                    )
                ).scalars().all():
                    brands_by_id[brand.id] = brand

        if brand_ids:
            for brand in (
                await session.execute(
                    select(Brand)
                    .where(Brand.instance_id == instance_id, Brand.id.in_(brand_ids))
                    .order_by(Brand.id.asc())
                )
            ).scalars().all():
                brands_by_id[brand.id] = brand

        return MigrationScope(
            brands=sorted(brands_by_id.values(), key=lambda item: item.id),
            categories=sorted(categories_by_id.values(), key=lambda item: item.id),
            sections=sorted(sections_by_id.values(), key=lambda item: item.id),
            articles=sorted(articles_by_id.values(), key=lambda item: item.id),
        )

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

        target_hc = TargetHelpCenter(session=session, instance=target, brand=brand, subdomain=subdomain)
        return await cls._load_target_help_center_locales(target_hc)

    @classmethod
    async def _load_target_help_center_locales(cls, target_hc: TargetHelpCenter) -> TargetHelpCenter:
        """
        /**
         * 타겟 Help Center에서 사용 가능한 locale 목록을 Zendesk API로 조회한다.
         * @param {TargetHelpCenter} target_hc 타겟 Help Center 컨텍스트
         * @returns {TargetHelpCenter} locale 정보가 채워진 컨텍스트
         */
        """
        try:
            payload = await ZendeskOAuthService.get_json(target_hc.session, target_hc.instance, url=f"{target_hc.base_url}/locales.json",
            )
        except ZendeskClientError:
            return target_hc

        raw_locales = payload.get("locales", [])
        allowed: set[str] = set()
        default_locale = target_hc.default_locale

        root_default = payload.get("default_locale")
        if isinstance(root_default, str) and root_default.strip():
            default_locale = root_default.strip().lower().replace("_", "-")

        for item in raw_locales:
            code, is_default = cls._parse_help_center_locale_entry(item)
            if not code:
                continue
            allowed.add(code)
            if is_default:
                default_locale = code

        if allowed and default_locale not in allowed:
            default_locale = next(iter(sorted(allowed)))

        if not allowed:
            return target_hc

        return replace(
            target_hc,
            allowed_locales=frozenset(allowed),
            default_locale=default_locale,
        )

    @staticmethod
    def _parse_help_center_locale_entry(item: object) -> tuple[str | None, bool]:
        """
        /**
         * Zendesk locales.json 항목을 (locale 코드, 기본 여부)로 파싱한다.
         * API는 문자열 배열(["ko", "en-us"]) 또는 객체 배열을 모두 반환할 수 있다.
         * @param {object} item locales 배열의 한 요소
         * @returns {tuple[str | None, bool]} 정규화된 locale, default 플래그
         */
        """
        if isinstance(item, str):
            code = item.strip().lower().replace("_", "-")
            return (code or None, False)

        if isinstance(item, dict):
            raw_code = item.get("locale") or item.get("code") or item.get("id")
            code = str(raw_code or "").strip().lower().replace("_", "-")
            return (code or None, bool(item.get("default")))

        return (None, False)

    @staticmethod
    async def _load_target_categories(target_hc: TargetHelpCenter) -> dict[str, int]:
        """
        /**
         * 타겟 Zendesk 카테고리를 이름 기준 사전으로 조회한다.
         * @param {TargetHelpCenter} target_hc 타겟 Help Center 컨텍스트
         * @returns {dict[str, int]} 카테고리명 -> 타겟 카테고리 ID
         */
        """
        payload = await ZendeskOAuthService.get_json(target_hc.session, target_hc.instance, url=f"{target_hc.base_url}/categories.json",
        )
        categories = payload.get("categories", [])
        return {item["name"]: item["id"] for item in categories}

    @classmethod
    async def _create_target_category(
        cls,
        target_hc: TargetHelpCenter,
        name: str,
        locale: str | None = None,
    ) -> int:
        """
        /**
         * 타겟 Zendesk에 카테고리를 생성한다.
         * @param {TargetHelpCenter} target_hc 타겟 Help Center 컨텍스트
         * @param {str} name 생성할 카테고리 이름
         * @param {str | None} locale 카테고리 locale(미지정 시 ko)
         * @returns {int} 생성된 타겟 카테고리 ID
         */
        """
        payload = await ZendeskOAuthService.post_json(
            target_hc.session,
            target_hc.instance,
            f"{target_hc.base_url}/categories.json",
            json_body={
                "category": {
                    "name": name,
                    "locale": cls._normalize_help_center_locale(locale, target_hc),
                }
            },
        )
        return payload["category"]["id"]

    @classmethod
    async def _create_target_section(
        cls,
        target_hc: TargetHelpCenter,
        category_id: int,
        name: str,
        description: str | None,
        locale: str | None = None,
        parent_section_id: int | None = None,
    ) -> int:
        """
        /**
         * 타겟 Zendesk에 섹션을 생성한다.
         * parent_section_id는 Guide Enterprise에서만 사용(기본은 카테고리 직속 섹션).
         */
        """
        section_body: dict[str, object] = {
            "name": name,
            "locale": cls._normalize_help_center_locale(locale, target_hc),
        }
        if description:
            section_body["description"] = description
        if parent_section_id is not None:
            section_body["parent_section_id"] = parent_section_id

        payload = await ZendeskOAuthService.post_json(
            target_hc.session,
            target_hc.instance,
            f"{target_hc.base_url}/categories/{category_id}/sections.json",
            json_body={"section": section_body},
        )
        return payload["section"]["id"]

    @staticmethod
    def _normalize_help_center_locale(locale: str | None, target_hc: TargetHelpCenter) -> str:
        """
        /**
         * 소스 locale을 타겟 Help Center에서 허용하는 locale로 변환한다.
         * 예: 소스 ko-kr → 타겟 ko (d3v-gsneotek 등은 ko-kr 미지원)
         * @param {str | None} locale DB에 저장된 locale
         * @param {TargetHelpCenter} target_hc 타겟 Help Center(allowed_locales 포함)
         * @returns {str} 타겟 API에 전달할 locale
         */
        """
        preferred = (locale or target_hc.default_locale).strip().lower().replace("_", "-")
        if not preferred:
            preferred = target_hc.default_locale

        allowed = target_hc.allowed_locales
        if preferred in allowed:
            return preferred

        base_language = preferred.split("-")[0]
        if base_language in allowed:
            return base_language

        for candidate in (target_hc.default_locale, "ko", "en-us"):
            if candidate in allowed:
                return candidate

        return target_hc.default_locale

    @staticmethod
    def _replace_body_url_variants(body: str, source_url: str, target_url: str) -> str:
        """
        /**
         * 본문 HTML에서 원본 URL과 HTML 이스케이프 형태를 모두 치환한다.
         */
        """
        updated = body.replace(source_url, target_url)
        escaped_source = source_url.replace("&", "&amp;")
        escaped_target = target_url.replace("&", "&amp;")
        return updated.replace(escaped_source, escaped_target)

    @classmethod
    async def _target_article_exists(cls, target_hc: TargetHelpCenter, target_article_id: int) -> bool:
        """
        /**
         * 타겟 Zendesk에 아티클이 실제로 존재하는지 확인한다.
         * @param {TargetHelpCenter} target_hc 타겟 Help Center 컨텍스트
         * @param {int} target_article_id 타겟 아티클 A ID
         * @returns {bool} 존재하면 True
         */
        """
        try:
            await ZendeskOAuthService.get_json(target_hc.session, target_hc.instance, url=f"{target_hc.base_url}/articles/{target_article_id}.json",
            )
            return True
        except ZendeskClientError as error:
            if "status=404" in str(error) or "RecordNotFound" in str(error):
                return False
            raise

    @classmethod
    async def _ensure_target_article_id(
        cls,
        target_hc: TargetHelpCenter,
        target_section_id: int,
        article: Article,
        preferred_article_id: int | None,
        *,
        source_instance_id: int,
        target_instance_id: int,
        report_progress: bool,
    ) -> int:
        """
        /**
         * 타겟 아티클 ID를 반환한다. 매핑 ID가 Zendesk에 없으면 새로 생성한다.
         * @returns {int} 사용할 타겟 아티클 A ID
         */
        """
        if preferred_article_id is not None and await cls._target_article_exists(target_hc, preferred_article_id):
            return preferred_article_id

        if preferred_article_id is not None and report_progress:
            await MigrateProgressTracker.append_log(
                source_instance_id,
                target_instance_id,
                (
                    f"{article.title} 아티클: 타겟(id:{preferred_article_id})이 Zendesk에 없어 "
                    "새 아티클을 생성합니다."
                ),
            )

        target_article_id, _ = await cls._create_target_article(target_hc, target_section_id, article)
        return target_article_id

    @classmethod
    async def _create_target_article(
        cls, target_hc: TargetHelpCenter, section_id: int, article: Article
    ) -> tuple[int, str | None]:
        """
        /**
         * 타겟 Zendesk에 아티클을 생성한다(초기 translation 포함).
         */
        """
        locale = cls._normalize_help_center_locale(article.locale, target_hc)
        payload = await ZendeskOAuthService.post_json(
            target_hc.session,
            target_hc.instance,
            f"{target_hc.base_url}/sections/{section_id}/articles.json",
            json_body={
                "article": {
                    "title": article.title,
                    "body": article.body or "",
                    "locale": locale,
                    "draft": article.draft,
                    "label_names": article.label_names or [],
                },
                "notify_subscribers": False,
            },
        )
        created = payload["article"]
        return int(created["id"]), created.get("html_url")

    @classmethod
    async def _save_article_translation(
        cls,
        target_hc: TargetHelpCenter,
        target_article_id: int,
        article: Article,
        body: str,
    ) -> None:
        """
        /**
         * 아티클 title/body/draft는 Translations API로만 저장한다.
         * (Article PATCH/PUT은 본문을 갱신하지 않음)
         */
        """
        locale = cls._normalize_help_center_locale(article.locale, target_hc)
        translation_payload = {
            "translation": {
                "title": article.title,
                "body": body,
                "draft": article.draft,
            }
        }
        put_url = f"{target_hc.base_url}/articles/{target_article_id}/translations/{locale}.json"
        try:
            await ZendeskOAuthService.put_json(
                target_hc.session,
                target_hc.instance,
                put_url,
                json_body=translation_payload,
            )
        except ZendeskClientError:
            await ZendeskOAuthService.post_json(
                target_hc.session,
                target_hc.instance,
                f"{target_hc.base_url}/articles/{target_article_id}/translations.json",
                json_body={
                    "translation": {
                        "locale": locale,
                        "title": article.title,
                        "body": body,
                        "draft": article.draft,
                    }
                },
            )

    @staticmethod
    async def _patch_article_labels(
        target_hc: TargetHelpCenter,
        target_article_id: int,
        label_names: list[str] | None,
    ) -> None:
        """
        /**
         * 아티클 메타데이터(label_names)만 PATCH로 갱신한다.
         */
        """
        await ZendeskOAuthService.patch_json(
            target_hc.session,
            target_hc.instance,
            f"{target_hc.base_url}/articles/{target_article_id}.json",
            json_body={"article": {"label_names": label_names or []}},
        )

    @classmethod
    async def _finalize_target_article(
        cls,
        *,
        source: Instance,
        target_hc: TargetHelpCenter,
        source_subdomain: str,
        source_article_id: int,
        target_article_id: int,
        article: Article,
        source_instance_id: int,
        target_instance_id: int,
        report_progress: bool = False,
    ) -> None:
        """
        /**
         * 첨부 재업로드·본문 URL 치환 후 translation과 label을 저장한다.
         */
        """
        # Zendesk는 translation 저장 후에야 첨부 업로드 API가 동작하는 경우가 있다.
        await cls._save_article_translation(
            target_hc=target_hc,
            target_article_id=target_article_id,
            article=article,
            body=article.body or "",
        )
        replaced_body = await cls._sync_attachments_and_replace_body(
            source=source,
            target_hc=target_hc,
            source_subdomain=source_subdomain,
            source_article_id=source_article_id,
            target_article_id=target_article_id,
            body=article.body,
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
            report_progress=report_progress,
        )
        final_body = replaced_body if replaced_body is not None else (article.body or "")
        if final_body != (article.body or ""):
            await cls._save_article_translation(
                target_hc=target_hc,
                target_article_id=target_article_id,
                article=article,
                body=final_body,
            )
        await cls._patch_article_labels(
            target_hc=target_hc,
            target_article_id=target_article_id,
            label_names=article.label_names,
        )

    @staticmethod
    async def _sync_attachments_and_replace_body(
        source: Instance,
        target_hc: TargetHelpCenter,
        source_subdomain: str,
        source_article_id: int,
        target_article_id: int,
        body: str | None,
        *,
        source_instance_id: int,
        target_instance_id: int,
        report_progress: bool = False,
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

        attachments_payload = await ZendeskOAuthService.get_json(
            target_hc.session,
            source,
            f"https://{source_subdomain}.zendesk.com/api/v2/help_center/articles/{source_article_id}/attachments.json",
        )
        attachments = attachments_payload.get("article_attachments", [])
        updated_body = body
        attachment_id_to_target_url: dict[str, str] = {}

        async def _upload_with_fallback(
            *,
            filename: str,
            content_type: str,
            content: bytes,
            log_context: str,
        ) -> str | None:
            """
            /**
             * 타겟 아티클에 첨부를 업로드한다. 404 등 일부 오류는 로그만 남기고 건너뛴다.
             */
            """
            try:
                upload_payload = await ZendeskOAuthService.upload_attachment(
                    target_hc.session,
                    target_hc.instance,
                    article_id=target_article_id,
                    filename=filename,
                    content_type=content_type,
                    content=content,
                    target_subdomain=target_hc.subdomain,
                )
                return upload_payload.get("article_attachment", {}).get("content_url")
            except ZendeskClientError as error:
                if report_progress:
                    await MigrateProgressTracker.append_log(
                        source_instance_id,
                        target_instance_id,
                        f"첨부 업로드 건너뜀 ({log_context}): {error}",
                    )
                return None

        # 첨부파일을 하나씩 재업로드하고 본문 내 원본 URL을 새 URL로 대체한다.
        for attachment in attachments:
            source_url = attachment.get("content_url")
            attachment_id = attachment.get("id")
            if not source_url:
                continue

            binary = await ZendeskOAuthService.get_bytes(target_hc.session, source, source_url)
            target_url = await _upload_with_fallback(
                filename=attachment.get("file_name", f"attachment-{source_article_id}"),
                content_type=attachment.get("content_type", "application/octet-stream"),
                content=binary,
                log_context=attachment.get("file_name", "첨부파일"),
            )
            if not target_url:
                continue

            updated_body = MigrationService._replace_body_url_variants(updated_body, source_url, target_url)
            if attachment_id is not None:
                attachment_id_to_target_url[str(attachment_id)] = target_url

        # 본문에만 있고 attachments API 목록과 다른 인라인 경로(/hc/article_attachments/{id}) 처리
        for match in INLINE_ARTICLE_ATTACHMENT_URL_PATTERN.finditer(updated_body):
            inline_source_url = match.group(0)
            attachment_id = match.group(1)
            if attachment_id in attachment_id_to_target_url:
                target_url = attachment_id_to_target_url[attachment_id]
                updated_body = MigrationService._replace_body_url_variants(
                    updated_body,
                    inline_source_url,
                    target_url,
                )
                continue

            inline_download_url = (
                f"https://{source_subdomain}.zendesk.com/hc/article_attachments/{attachment_id}"
            )
            try:
                binary = await ZendeskOAuthService.get_bytes(target_hc.session, source, inline_download_url)
            except ZendeskClientError:
                continue

            target_url = await _upload_with_fallback(
                filename=f"inline-attachment-{attachment_id}",
                content_type="application/octet-stream",
                content=binary,
                log_context=f"인라인 첨부 {attachment_id}",
            )
            if not target_url:
                continue

            attachment_id_to_target_url[attachment_id] = target_url
            updated_body = MigrationService._replace_body_url_variants(updated_body, inline_source_url, target_url)

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

        scope = await cls._resolve_migration_scope(
            session=session,
            source=source,
            brand_ids=brand_ids,
            category_ids=category_ids,
            section_ids=section_ids,
            article_ids=article_ids,
        )
        selected_brands = scope.brands
        selected_categories = scope.categories
        selected_sections = scope.sections
        selected_articles = scope.articles

        if not selected_categories and not selected_sections and not selected_articles:
            raise ValueError(
                "이관할 카테고리·섹션·아티클이 없습니다. "
                "소스 인스턴스에서 Help Center 수집을 다시 실행했는지 확인하고, "
                "트리에서 카테고리·섹션·아티클을 선택한 뒤 마이그레이션하세요."
            )

        summary = MigrationSummary(
            scope_categories=len(selected_categories),
            scope_sections=len(selected_sections),
            scope_articles=len(selected_articles),
        )

        if report_progress:
            scope_message = (
                f"이관 대상 확인: 카테고리 {len(selected_categories)}개, "
                f"섹션 {len(selected_sections)}개, 아티클 {len(selected_articles)}개"
            )
            await MigrateProgressTracker.set_total_steps(
                source_instance_id,
                target_instance_id,
                max(1, len(selected_categories) + len(selected_sections) + len(selected_articles)),
            )
            await MigrateProgressTracker.update_step(
                source_instance_id,
                target_instance_id,
                current_step=0,
                phase="preparing",
                message=scope_message,
                log_line=scope_message,
            )

        target_categories_by_name = await cls._load_target_categories(target_hc)
        category_a_to_target_category_id: dict[int, int] = {}
        category_a_to_brand_subdomain: dict[int, str] = {}
        section_target_map: dict[int, int] = {}
        section_a_to_source_subdomain: dict[int, str] = {}

        progress_step = 0

        async def _progress_tick(phase: str, message: str, log_line: str | None = None) -> None:
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
                log_line=log_line,
            )

        # 1) 소스 카테고리 -> 타겟 카테고리 (Zendesk 구조와 동일)
        for category in selected_categories:
            source_brand = next((brand for brand in selected_brands if brand.id == category.brand_id), None)
            if source_brand is not None:
                category_a_to_brand_subdomain[category.a_id] = source_brand.subdomain

            existing_target_category_id = await cls._get_migrated_target_id(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="category",
                source_entity_id=category.a_id,
            )
            category_created = False
            if existing_target_category_id is not None:
                target_category_id = existing_target_category_id
            else:
                target_category_id = target_categories_by_name.get(category.name)
                if target_category_id is None:
                    target_category_id = await cls._create_target_category(
                        target_hc,
                        category.name,
                        locale=category.locale,
                    )
                    target_categories_by_name[category.name] = target_category_id
                    category_created = True

            if category_created:
                summary.categories += 1
                log_line = cls._build_migrate_log_line(
                    name=category.name,
                    entity_type="category",
                    entity_id=target_category_id,
                    action="created",
                )
                await _progress_tick("category", f"카테고리 생성: {category.name}", log_line)

            category_a_to_target_category_id[category.a_id] = target_category_id
            await cls._upsert_mapping(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="category",
                source_entity_id=category.a_id,
                target_entity_id=target_category_id,
                status="migrated",
            )
            await cls._upsert_target_category_snapshot(
                session,
                target_instance_id=target.id,
                target_brand_id=target_hc.brand.id,
                target_category_a_id=target_category_id,
                name=category.name,
                locale=category.locale,
            )

        # 브랜드는 Help Center API 컨텍스트만 사용(Zendesk 카테고리로 생성하지 않음)

        # 2) 소스 섹션 -> 타겟 섹션 (카테고리 직속, parent_section_id 미사용)
        for section in selected_sections:
            target_category_id = category_a_to_target_category_id.get(section.a_category_id)
            if target_category_id is None:
                raise ValueError(
                    f"섹션 '{section.name}'의 부모 카테고리를 타겟에 연결할 수 없습니다. "
                    "소스·타겟 매핑 상태를 확인한 뒤 다시 시도하세요."
                )

            parent_category = next(
                (item for item in selected_categories if item.a_id == section.a_category_id),
                None,
            )
            section_locale = section.locale or (parent_category.locale if parent_category else None)

            existing_target_section_id = await cls._get_migrated_target_id(
                session=session,
                source_instance_id=source.id,
                target_instance_id=target.id,
                entity_type="section",
                source_entity_id=section.a_id,
            )
            section_created = False
            if existing_target_section_id is not None:
                target_section_id = existing_target_section_id
            else:
                target_section_id = await cls._create_target_section(
                    target_hc,
                    target_category_id,
                    section.name,
                    section.description,
                    locale=section_locale,
                )
                summary.sections += 1
                section_created = True

            if section_created:
                section_log = cls._build_migrate_log_line(
                    name=section.name,
                    entity_type="section",
                    entity_id=target_section_id,
                    action="created",
                )
                await _progress_tick("section", f"섹션 생성: {section.name}", section_log)

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
            await cls._upsert_target_section_snapshot(
                session,
                target_instance_id=target.id,
                target_category_a_id=target_category_id,
                target_section_a_id=target_section_id,
                name=section.name,
                description=section.description,
                locale=section_locale,
            )

        # 4) 아티클 생성/업데이트
        for article in selected_articles:
            target_section_id = section_target_map.get(article.a_section_id)
            if target_section_id is None:
                raise ValueError(
                    f"아티클 '{article.title}'의 부모 섹션을 타겟에 연결할 수 없습니다. "
                    "섹션·카테고리 마이그레이션을 먼저 확인하세요."
                )

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
                    summary.articles_skipped += 1
                    if report_progress:
                        skip_log = (
                            f"{article.title} 아티클(id:{existing_mapping.target_entity_id})은 "
                            "기존 매핑이 있어 건너뛰었습니다. (정책: skip)"
                        )
                        await MigrateProgressTracker.append_log(
                            source_instance_id,
                            target_instance_id,
                            skip_log,
                        )
                    continue
                if duplicate_policy in {"update", "force"}:
                    source_subdomain = section_a_to_source_subdomain.get(article.a_section_id, source.subdomain)
                    previous_target_article_id = existing_mapping.target_entity_id
                    target_article_id = await cls._ensure_target_article_id(
                        target_hc,
                        target_section_id,
                        article,
                        previous_target_article_id,
                        source_instance_id=source.id,
                        target_instance_id=target.id,
                        report_progress=report_progress,
                    )
                    await cls._finalize_target_article(
                        source=source,
                        target_hc=target_hc,
                        source_subdomain=source_subdomain,
                        source_article_id=article.a_id,
                        target_article_id=target_article_id,
                        article=article,
                        source_instance_id=source.id,
                        target_instance_id=target.id,
                        report_progress=report_progress,
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
                    await cls._upsert_target_article_snapshot(
                        session,
                        target_instance_id=target.id,
                        target_section_a_id=target_section_id,
                        target_article_a_id=target_article_id,
                        article=article,
                        brand_subdomain=target_hc.subdomain,
                        article_locale=cls._normalize_help_center_locale(article.locale, target_hc),
                    )
                    summary.articles += 1
                    article_action: MigrateLogAction = (
                        "created" if target_article_id != previous_target_article_id else "updated"
                    )
                    article_log = cls._build_migrate_log_line(
                        name=article.title,
                        entity_type="article",
                        entity_id=target_article_id,
                        action=article_action,
                    )
                    await _progress_tick(
                        "article",
                        f"아티클 {'생성' if article_action == 'created' else '갱신'}: {article.title[:60]}",
                        article_log,
                    )
                continue

            target_article_id, zendesk_html_url = await cls._create_target_article(
                target_hc,
                target_section_id,
                article,
            )
            source_subdomain = section_a_to_source_subdomain.get(article.a_section_id, source.subdomain)
            await cls._finalize_target_article(
                source=source,
                target_hc=target_hc,
                source_subdomain=source_subdomain,
                source_article_id=article.a_id,
                target_article_id=target_article_id,
                article=article,
                source_instance_id=source.id,
                target_instance_id=target.id,
                report_progress=report_progress,
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
            await cls._upsert_target_article_snapshot(
                session,
                target_instance_id=target.id,
                target_section_a_id=target_section_id,
                target_article_a_id=target_article_id,
                article=article,
                brand_subdomain=target_hc.subdomain,
                article_locale=cls._normalize_help_center_locale(article.locale, target_hc),
                zendesk_html_url=zendesk_html_url,
            )
            summary.articles += 1
            article_log = cls._build_migrate_log_line(
                name=article.title,
                entity_type="article",
                entity_id=target_article_id,
                action="created",
            )
            await _progress_tick("article", f"아티클 생성: {article.title[:60]}", article_log)

        created_or_updated = summary.categories + summary.sections + summary.articles
        if created_or_updated == 0:
            skip_hint = (
                f" 건너뛴 아티클 {summary.articles_skipped}건(skip 정책·기존 매핑)."
                if summary.articles_skipped
                else ""
            )
            raise ValueError(
                "선택한 항목이 타겟 Zendesk에 생성·갱신되지 않았습니다."
                f"{skip_hint} "
                "중복 정책을 update로 바꾸거나, 타겟에서 삭제·매핑 정리 후 다시 시도하세요."
            )

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
                if mapping.entity_type == "category":
                    delete_error_category_a_ids.append(target_a_id)
                elif mapping.entity_type == "section":
                    delete_error_section_a_ids.append(target_a_id)
                elif mapping.entity_type == "article":
                    delete_error_article_a_ids.append(target_a_id)
                continue

            if mapping.entity_type == "category":
                migrated_category_a_ids.append(target_a_id)
            elif mapping.entity_type == "section":
                migrated_section_a_ids.append(target_a_id)
            elif mapping.entity_type == "article":
                migrated_article_a_ids.append(target_a_id)

        valid_category_a_ids = set(
            (
                await session.execute(
                    select(Category.a_id).where(Category.instance_id == target_instance_id)
                )
            ).scalars().all()
        )
        valid_section_a_ids = set(
            (
                await session.execute(
                    select(Section.a_id).where(Section.instance_id == target_instance_id)
                )
            ).scalars().all()
        )
        valid_article_a_ids = set(
            (
                await session.execute(
                    select(Article.a_id).where(Article.instance_id == target_instance_id)
                )
            ).scalars().all()
        )

        migrated_category_a_ids = [item for item in migrated_category_a_ids if item in valid_category_a_ids]
        migrated_section_a_ids = [item for item in migrated_section_a_ids if item in valid_section_a_ids]
        migrated_article_a_ids = [item for item in migrated_article_a_ids if item in valid_article_a_ids]
        delete_error_category_a_ids = [item for item in delete_error_category_a_ids if item in valid_category_a_ids]
        delete_error_section_a_ids = [item for item in delete_error_section_a_ids if item in valid_section_a_ids]
        delete_error_article_a_ids = [item for item in delete_error_article_a_ids if item in valid_article_a_ids]
        delete_error_items = [
            item
            for item in delete_error_items
            if (
                (item["mapping_entity_type"] == "category" and item["target_a_id"] in valid_category_a_ids)
                or (item["mapping_entity_type"] == "section" and item["target_a_id"] in valid_section_a_ids)
                or (item["mapping_entity_type"] == "article" and item["target_a_id"] in valid_article_a_ids)
            )
        ]

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

    @classmethod
    async def clear_migration_mappings(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
    ) -> int:
        """
        /**
         * 소스·타겟 인스턴스 쌍의 migration_mappings를 모두 삭제한다.
         * 타겟 Help Center 수집 데이터(categories/sections/articles)는 유지한다.
         * @returns {int} 삭제된 매핑 행 수
         */
        """
        await cls._get_instance(session=session, instance_id=source_instance_id)
        await cls._get_instance(session=session, instance_id=target_instance_id)

        result = await session.execute(
            delete(MigrationMapping).where(
                MigrationMapping.source_instance_id == source_instance_id,
                MigrationMapping.target_instance_id == target_instance_id,
            )
        )
        await session.commit()
        return int(result.rowcount or 0)

    @classmethod
    async def get_migrated_target_tree(
        cls,
        session: AsyncSession,
        source_instance_id: int,
        target_instance_id: int,
        target_brand_id: int | None = None,
    ) -> dict:
        """
        /**
         * migration_mappings와 타겟 DB 스냅샷으로 마이그레이션 생성 항목만 트리를 구성한다.
         * Zendesk 전체 재수집 없이 타겟 패널에 표시할 때 사용한다.
         * @returns {dict} FetchDetailResponse 호환 트리 데이터
         */
        """
        source = await cls._get_instance(session=session, instance_id=source_instance_id)
        target_hc = await cls._resolve_target_help_center(
            session=session,
            target_instance_id=target_instance_id,
            target_brand_id=target_brand_id,
        )
        target = target_hc.instance
        brand = target_hc.brand

        mappings = (
            await session.execute(
                select(MigrationMapping).where(
                    MigrationMapping.source_instance_id == source.id,
                    MigrationMapping.target_instance_id == target.id,
                    MigrationMapping.status.in_(("migrated", "delete_error")),
                    MigrationMapping.target_entity_id.is_not(None),
                )
            )
        ).scalars().all()

        mapped_category_a_ids: set[int] = set()
        mapped_section_a_ids: set[int] = set()
        mapped_article_a_ids: set[int] = set()

        for mapping in mappings:
            target_a_id = mapping.target_entity_id
            if target_a_id is None:
                continue
            if mapping.entity_type == "category":
                mapped_category_a_ids.add(target_a_id)
            elif mapping.entity_type == "section":
                mapped_section_a_ids.add(target_a_id)
            elif mapping.entity_type == "article":
                mapped_article_a_ids.add(target_a_id)

        # 타겟 인스턴스 DB(수집 데이터)와 동일한 계층으로 트리를 만든다. 소스 이름·유령 매핑으로 노드를 늘리지 않는다.
        target_categories = (
            await session.execute(
                select(Category).where(
                    Category.instance_id == target.id,
                    Category.brand_id == brand.id,
                ).order_by(Category.name.asc())
            )
        ).scalars().all()
        target_sections = (
            await session.execute(
                select(Section).where(Section.instance_id == target.id).order_by(Section.name.asc())
            )
        ).scalars().all()
        target_articles = (
            await session.execute(
                select(Article).where(Article.instance_id == target.id).order_by(Article.title.asc())
            )
        ).scalars().all()

        categories_by_a_id = {row.a_id: row for row in target_categories}
        sections_by_a_id = {row.a_id: row for row in target_sections}
        articles_by_a_id = {row.a_id: row for row in target_articles}

        # Zendesk/DB에 실제로 있는 타겟 ID만 사용(삭제된 엔티티를 가리키는 옛 매핑 제외)
        mapped_category_a_ids &= set(categories_by_a_id.keys())
        mapped_section_a_ids &= set(sections_by_a_id.keys())
        mapped_article_a_ids &= set(articles_by_a_id.keys())

        included_section_a_ids = set(mapped_section_a_ids)
        included_article_a_ids = set(mapped_article_a_ids)

        for article_a_id in mapped_article_a_ids:
            article_row = articles_by_a_id.get(article_a_id)
            if article_row is not None:
                included_section_a_ids.add(article_row.a_section_id)

        included_category_a_ids = set(mapped_category_a_ids)
        for section_a_id in included_section_a_ids:
            section_row = sections_by_a_id.get(section_a_id)
            if section_row is not None:
                included_category_a_ids.add(section_row.a_category_id)

        sections_by_category_a_id: dict[int, list[Section]] = {}
        for section in target_sections:
            if section.a_category_id not in included_category_a_ids:
                continue
            if section.a_id not in included_section_a_ids:
                continue
            sections_by_category_a_id.setdefault(section.a_category_id, []).append(section)

        articles_by_section_a_id: dict[int, list[Article]] = {}
        for article in target_articles:
            if article.a_section_id not in included_section_a_ids:
                continue
            if article.a_id not in included_article_a_ids:
                continue
            articles_by_section_a_id.setdefault(article.a_section_id, []).append(article)

        sorted_categories: list[dict] = []
        for category in target_categories:
            if category.a_id not in included_category_a_ids:
                continue

            category_sections = sections_by_category_a_id.get(category.a_id, [])

            def _articles_for_migrated_section(section: Section) -> list[dict]:
                section_articles = articles_by_section_a_id.get(section.a_id, [])
                return [
                    {
                        "id": article.id,
                        "a_id": article.a_id,
                        "title": article.title,
                        "draft": article.draft,
                        "html_url": cls._build_target_article_html_url(
                            brand_subdomain=brand.subdomain,
                            target_article_a_id=article.a_id,
                            locale=cls._normalize_help_center_locale(article.locale, target_hc),
                            draft=article.draft,
                            zendesk_html_url=article.html_url,
                        ),
                        "has_attachments": article.has_attachments,
                    }
                    for article in section_articles
                ]

            from services.help_center_tree import (
                build_nested_section_nodes,
                count_sections_in_nodes,
                iter_sections_in_nodes,
            )

            section_nodes = build_nested_section_nodes(
                category_sections,
                build_articles=_articles_for_migrated_section,
            )

            sorted_categories.append(
                {
                    "id": category.id,
                    "a_id": category.a_id,
                    "name": category.name,
                    "sections": section_nodes,
                }
            )

        total_sections = sum(
            count_sections_in_nodes(category["sections"]) for category in sorted_categories
        )
        total_articles = sum(
            len(section["articles"])
            for category in sorted_categories
            for section in iter_sections_in_nodes(category["sections"])
        )

        brand_node = {
            "id": brand.id,
            "a_brand_id": brand.a_brand_id,
            "name": brand.name,
            "subdomain": brand.subdomain,
            "has_help_center": brand.has_help_center,
            "categories": sorted_categories,
        }

        return {
            "source_instance_id": source.id,
            "target_instance_id": target.id,
            "instance_id": target.id,
            "instance_name": target.name or target.subdomain,
            "summary": {
                "total_brands": 1,
                "total_categories": len(sorted_categories),
                "total_sections": total_sections,
                "total_articles": total_articles,
            },
            "brands": [brand_node],
            "mapping_record_count": len(mappings),
        }
