from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article, Brand, Category, Instance, Section
from services.fetch_progress import FetchProgressTracker
from services.help_center_tree import build_nested_section_nodes
from services.zendesk_client import ZendeskClient, ZendeskClientError


ARTICLES_PER_PAGE = 100
ARTICLES_CURSOR_PAGE_SIZE_PARAM = "page[size]"
ATTACHMENT_CHECK_CONCURRENCY = 5
ARTICLE_FETCH_PROGRESS_LOG_INTERVAL = 10
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncCounts:
    """
    /**
     * 동기화 처리 건수(생성/수정/삭제)를 보관한다.
     * @param {int} created 신규 생성 건수
     * @param {int} updated 기존 수정 건수
     * @param {int} deleted 원격에 없어 삭제한 건수
     * @returns {None} 데이터 모델이므로 반환값 없음
     */
    """

    created: int = 0
    updated: int = 0
    deleted: int = 0

    @property
    def total(self) -> int:
        return self.created + self.updated + self.deleted


@dataclass(slots=True)
class FetchBrandSummary:
    """
    /**
     * 브랜드별 수집 결과를 보관한다.
     * @param {int} brand_id 내부 브랜드 PK
     * @param {str} brand_name 브랜드 이름
     * @param {SyncCounts} categories 카테고리 동기화 결과
     * @param {SyncCounts} sections 섹션 동기화 결과
     * @param {SyncCounts} articles 아티클 동기화 결과
     * @returns {None} 데이터 모델이므로 반환값 없음
     */
    """

    brand_id: int
    brand_name: str
    categories: SyncCounts = field(default_factory=SyncCounts)
    sections: SyncCounts = field(default_factory=SyncCounts)
    articles: SyncCounts = field(default_factory=SyncCounts)


class FetchService:
    """
    /**
     * 소스 Zendesk 데이터 수집 및 DB 업서트 로직을 제공한다.
     * @returns {None} 서비스 클래스이므로 반환값 없음
     */
    """

    @classmethod
    async def _ensure_brands(cls, session: AsyncSession, instance: Instance) -> None:
        """
        /**
         * 인스턴스에 브랜드 정보가 없으면 Zendesk API로 조회해 저장한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {Instance} instance 대상 인스턴스
         * @returns {None}
         */
        """
        existing_query = select(Brand).where(Brand.instance_id == instance.id)
        existing_brands = (await session.execute(existing_query)).scalars().all()
        if existing_brands:
            return

        zendesk_brands = await ZendeskClient.get_brands(
            main_subdomain=instance.subdomain,
            email=instance.email,
            api_token=instance.api_token,
        )
        for brand in zendesk_brands:
            session.add(
                Brand(
                    instance_id=instance.id,
                    a_brand_id=brand.id,
                    name=brand.name,
                    subdomain=brand.subdomain,
                    has_help_center=brand.has_help_center,
                    is_selected=True,
                )
            )
        await session.flush()

    @classmethod
    async def _fetch_json_with_context(
        cls,
        *,
        url: str,
        email: str,
        api_token: str,
        brand_name: str,
        fetch_step: str,
    ) -> dict:
        """
        /**
         * Zendesk API 호출 실패 시 디버깅 가능한 문맥 정보를 포함해 예외를 래핑한다.
         * @param {str} url Zendesk 요청 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {str} brand_name 현재 수집 중인 브랜드 이름
         * @param {str} fetch_step 수집 단계 식별자(categories/sections/articles)
         * @returns {dict} Zendesk JSON 응답 페이로드
         */
        """
        try:
            return await ZendeskClient.get_json(url=url, email=email, api_token=api_token)
        except ZendeskClientError as error:
            error_message = f"[수집 실패] 브랜드={brand_name}, 단계={fetch_step}, URL={url}, 원인={error}"
            logger.error(error_message)
            raise ZendeskClientError(error_message) from error

    @staticmethod
    def _build_articles_cursor_start_url(base_url: str) -> str:
        """
        /**
         * Help Center 아티클 목록 커서 페이지네이션 첫 요청 URL을 만든다.
         * @param {str} base_url 브랜드 Help Center API 베이스 URL
         * @returns {str} page[size]가 포함된 첫 페이지 URL
         */
        """
        query = urlencode({ARTICLES_CURSOR_PAGE_SIZE_PARAM: str(ARTICLES_PER_PAGE)})
        return f"{base_url}/articles.json?{query}"

    @staticmethod
    def _resolve_cursor_next_page_url(payload: dict) -> str | None:
        """
        /**
         * Zendesk 커서 페이지네이션 응답에서 다음 페이지 URL을 추출한다.
         * 오프셋 방식 next_page는 100페이지 제한이 있어 사용하지 않는다.
         * @param {dict} payload Zendesk JSON 응답
         * @returns {str | None} 다음 페이지 URL 또는 None(종료)
         */
        """
        meta = payload.get("meta")
        if isinstance(meta, dict) and meta.get("has_more") is False:
            return None

        links = payload.get("links")
        if isinstance(links, dict):
            next_url = links.get("next")
            if isinstance(next_url, str) and next_url.strip():
                if isinstance(meta, dict) and meta.get("has_more") is True:
                    return next_url.strip()
                if not isinstance(meta, dict):
                    return next_url.strip()

        if isinstance(meta, dict) and meta.get("has_more") is True:
            raise ZendeskClientError("커서 페이지네이션 응답에 links.next가 없습니다.")

        return None

    @classmethod
    async def _fetch_all_help_center_articles(
        cls,
        *,
        instance_id: int,
        brand_index: int,
        base_url: str,
        email: str,
        api_token: str,
        brand_name: str,
    ) -> list[dict]:
        """
        /**
         * Help Center 아티클 전체를 커서 페이지네이션으로 수집한다.
         * @param {str} base_url 브랜드 Help Center API 베이스 URL
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {str} brand_name 브랜드 이름(로그용)
         * @returns {list[dict]} 수집된 아티클 JSON 목록
         */
        """
        article_items: list[dict] = []
        next_page_url: str | None = cls._build_articles_cursor_start_url(base_url)
        page_index = 0

        while next_page_url:
            page_index += 1
            articles_payload = await cls._fetch_json_with_context(
                url=next_page_url,
                email=email,
                api_token=api_token,
                brand_name=brand_name,
                fetch_step="articles",
            )
            batch = articles_payload.get("articles", [])
            if isinstance(batch, list):
                article_items.extend(batch)

            if page_index == 1 or page_index % ARTICLE_FETCH_PROGRESS_LOG_INTERVAL == 0:
                logger.info(
                    "아티클 커서 수집 진행: brand=%s, page=%s, batch=%s, total=%s",
                    brand_name,
                    page_index,
                    len(batch) if isinstance(batch, list) else 0,
                    len(article_items),
                )
                await FetchProgressTracker.update_brand_step(
                    instance_id,
                    brand_index=brand_index,
                    brand_name=brand_name,
                    phase="articles",
                    message=f"{brand_name} 아티클 API 수집 중 — {len(article_items):,}건 ({page_index}페이지)",
                    article_page=page_index,
                    articles_collected=len(article_items),
                )

            next_page_url = cls._resolve_cursor_next_page_url(articles_payload)

        logger.info("아티클 커서 수집 완료: brand=%s, pages=%s, total=%s", brand_name, page_index, len(article_items))
        return article_items

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """
        /**
         * Zendesk datetime 문자열을 파이썬 datetime으로 변환한다.
         * @param {str | None} value Zendesk ISO datetime 문자열
         * @returns {datetime | None} 변환된 datetime 또는 None
         */
        """
        if not value:
            return None

        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)

    @staticmethod
    def _build_article_html_url(
        *,
        brand_subdomain: str,
        article_a_id: int,
        locale: str | None,
        draft: bool,
    ) -> str:
        """
        /**
         * Zendesk Help Center 아티클 공개/관리 URL을 생성한다.
         * @param {str} brand_subdomain 브랜드 서브도메인
         * @param {int} article_a_id 소스 아티클 A ID
         * @param {str | None} locale 아티클 로케일
         * @param {bool} draft 초안 여부
         * @returns {str} Help Center 아티클 URL
         */
        """
        locale_segment = (locale or "en-us").replace("_", "-").lower()
        if draft:
            return f"https://{brand_subdomain}.zendesk.com/hc/admin/articles/{article_a_id}/edit"
        return f"https://{brand_subdomain}.zendesk.com/hc/{locale_segment}/articles/{article_a_id}"

    @classmethod
    async def _enrich_articles_with_attachment_flags(
        cls,
        *,
        instance_id: int,
        brand_index: int,
        brand_subdomain: str,
        email: str,
        api_token: str,
        brand_name: str,
        article_items: list[dict],
    ) -> None:
        """
        /**
         * 아티클 목록에 첨부파일 존재 여부를 병렬로 조회해 항목에 반영한다.
         * @param {str} brand_subdomain 브랜드 서브도메인
         * @param {str} email Zendesk 로그인 이메일
         * @param {str} api_token Zendesk API 토큰
         * @param {str} brand_name 브랜드 이름(로깅용)
         * @param {list[dict]} article_items Zendesk 아티클 목록(제자리 수정)
         * @returns {None}
         */
        """
        if not article_items:
            return

        total = len(article_items)
        checked_count = 0
        progress_lock = asyncio.Lock()
        semaphore = asyncio.Semaphore(ATTACHMENT_CHECK_CONCURRENCY)

        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=brand_index,
            brand_name=brand_name,
            phase="attachments",
            message=f"{brand_name} 첨부파일 확인 중 (0/{total:,})",
            articles_collected=total,
            attachments_checked=0,
            attachments_total=total,
        )

        async def check_one(item: dict) -> None:
            nonlocal checked_count
            article_a_id = item["id"]
            attachments_url = (
                f"https://{brand_subdomain}.zendesk.com/api/v2/help_center/articles/{article_a_id}/attachments.json"
            )
            async with semaphore:
                try:
                    payload = await cls._fetch_json_with_context(
                        url=attachments_url,
                        email=email,
                        api_token=api_token,
                        brand_name=brand_name,
                        fetch_step="article_attachments",
                    )
                    item["_has_attachments"] = len(payload.get("article_attachments", [])) > 0
                except ZendeskClientError as error:
                    item["_has_attachments"] = False
                    await FetchProgressTracker.add_warning(
                        instance_id,
                        phase="article_attachments",
                        brand_name=brand_name,
                        message=f"article a_id={article_a_id}: {error}",
                    )
                except Exception as error:
                    item["_has_attachments"] = False
                    await FetchProgressTracker.add_warning(
                        instance_id,
                        phase="article_attachments",
                        brand_name=brand_name,
                        message=f"article a_id={article_a_id}: {error}",
                    )

            async with progress_lock:
                checked_count += 1
                should_report = checked_count == 1 or checked_count == total or checked_count % 100 == 0
            if should_report:
                await FetchProgressTracker.update_brand_step(
                    instance_id,
                    brand_index=brand_index,
                    brand_name=brand_name,
                    phase="attachments",
                    message=f"{brand_name} 첨부파일 확인 중 ({checked_count:,}/{total:,})",
                    articles_collected=total,
                    attachments_checked=checked_count,
                    attachments_total=total,
                )

        await asyncio.gather(*(check_one(item) for item in article_items))
        logger.info(
            "아티클 첨부파일 확인 완료: brand=%s, articles=%s, with_attachments=%s",
            brand_name,
            len(article_items),
            sum(1 for item in article_items if item.get("_has_attachments")),
        )

    @classmethod
    async def _sync_categories(
        cls,
        session: AsyncSession,
        instance_id: int,
        brand: Brand,
        categories: list[dict],
    ) -> SyncCounts:
        """
        /**
         * 카테고리를 동기화한다. 신규 생성, 기존 수정, 원격에 없는 항목 삭제를 수행한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} instance_id 인스턴스 ID
         * @param {Brand} brand 대상 브랜드 엔티티
         * @param {list[dict]} categories Zendesk 카테고리 목록
         * @returns {SyncCounts} 동기화 처리 건수
         */
        """
        counts = SyncCounts()
        fetched_ids = {item["id"] for item in categories}

        for item in categories:
            query = select(Category).where(
                Category.instance_id == instance_id,
                Category.a_id == item["id"],
            )
            row = await session.scalar(query)
            is_new = row is None
            if is_new:
                row = Category(instance_id=instance_id, brand_id=brand.id, a_id=item["id"], name=item["name"])
                session.add(row)
                counts.created += 1
            else:
                counts.updated += 1

            row.brand_id = brand.id
            row.name = item["name"]
            row.locale = item.get("locale")
            row.position = item.get("position")
            row.a_created_at = cls._parse_datetime(item.get("created_at"))
            row.a_updated_at = cls._parse_datetime(item.get("updated_at"))

        stale_query = select(Category).where(
            Category.instance_id == instance_id,
            Category.brand_id == brand.id,
        )
        if fetched_ids:
            stale_query = stale_query.where(Category.a_id.not_in(fetched_ids))
        stale_rows = (await session.execute(stale_query)).scalars().all()
        for stale_row in stale_rows:
            await session.delete(stale_row)
            counts.deleted += 1

        return counts

    @classmethod
    async def _sync_sections(
        cls,
        session: AsyncSession,
        instance_id: int,
        brand_category_a_ids: set[int],
        sections: list[dict],
    ) -> SyncCounts:
        """
        /**
         * 섹션을 동기화한다. 신규 생성, 기존 수정, 원격에 없는 항목 삭제를 수행한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} instance_id 인스턴스 ID
         * @param {set[int]} brand_category_a_ids 브랜드 소속 카테고리 A ID 집합
         * @param {list[dict]} sections Zendesk 섹션 목록
         * @returns {SyncCounts} 동기화 처리 건수
         */
        """
        counts = SyncCounts()
        fetched_ids = {item["id"] for item in sections}

        for item in sections:
            query = select(Section).where(
                Section.instance_id == instance_id,
                Section.a_id == item["id"],
            )
            row = await session.scalar(query)
            if row is None:
                parent_section_id = item.get("parent_section_id")
                row = Section(
                    instance_id=instance_id,
                    a_id=item["id"],
                    a_category_id=item["category_id"],
                    a_parent_section_id=int(parent_section_id) if parent_section_id else None,
                    name=item["name"],
                )
                session.add(row)
                counts.created += 1
            else:
                counts.updated += 1

            row.a_category_id = item["category_id"]
            parent_section_id = item.get("parent_section_id")
            row.a_parent_section_id = int(parent_section_id) if parent_section_id else None
            row.name = item["name"]
            row.locale = item.get("locale")
            row.position = item.get("position")
            row.description = item.get("description")
            row.a_created_at = cls._parse_datetime(item.get("created_at"))
            row.a_updated_at = cls._parse_datetime(item.get("updated_at"))

        if not brand_category_a_ids:
            return counts

        stale_query = select(Section).where(
            Section.instance_id == instance_id,
            Section.a_category_id.in_(brand_category_a_ids),
        )
        if fetched_ids:
            stale_query = stale_query.where(Section.a_id.not_in(fetched_ids))
        stale_rows = (await session.execute(stale_query)).scalars().all()
        for stale_row in stale_rows:
            await session.delete(stale_row)
            counts.deleted += 1

        return counts

    @classmethod
    async def _sync_articles(
        cls,
        session: AsyncSession,
        instance_id: int,
        brand_subdomain: str,
        brand_section_a_ids: set[int],
        articles: list[dict],
    ) -> SyncCounts:
        """
        /**
         * 아티클을 동기화한다. 신규 생성, 기존 수정, 원격에 없는 항목 삭제를 수행한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} instance_id 인스턴스 ID
         * @param {set[int]} brand_section_a_ids 브랜드 소속 섹션 A ID 집합
         * @param {list[dict]} articles Zendesk 아티클 목록
         * @returns {SyncCounts} 동기화 처리 건수
         */
        """
        counts = SyncCounts()
        fetched_ids = {item["id"] for item in articles}

        for item in articles:
            query = select(Article).where(
                Article.instance_id == instance_id,
                Article.a_id == item["id"],
            )
            row = await session.scalar(query)
            if row is None:
                row = Article(
                    instance_id=instance_id,
                    a_id=item["id"],
                    a_section_id=item["section_id"],
                    title=item["title"],
                    draft=item.get("draft", False),
                )
                session.add(row)
                counts.created += 1
            else:
                counts.updated += 1

            row.a_section_id = item["section_id"]
            row.title = item["title"]
            row.body = item.get("body")
            row.locale = item.get("locale")
            row.label_names = item.get("label_names", [])
            row.draft = item.get("draft", False)
            row.html_url = item.get("html_url") or cls._build_article_html_url(
                brand_subdomain=brand_subdomain,
                article_a_id=item["id"],
                locale=item.get("locale"),
                draft=item.get("draft", False),
            )
            row.has_attachments = bool(item.get("_has_attachments", False))
            row.a_created_at = cls._parse_datetime(item.get("created_at"))
            row.a_updated_at = cls._parse_datetime(item.get("updated_at"))

        if not brand_section_a_ids:
            return counts

        stale_query = select(Article).where(
            Article.instance_id == instance_id,
            Article.a_section_id.in_(brand_section_a_ids),
        )
        if fetched_ids:
            stale_query = stale_query.where(Article.a_id.not_in(fetched_ids))
        stale_rows = (await session.execute(stale_query)).scalars().all()
        for stale_row in stale_rows:
            await session.delete(stale_row)
            counts.deleted += 1

        return counts

    @classmethod
    async def _sync_one_brand(
        cls,
        session: AsyncSession,
        *,
        instance: Instance,
        instance_id: int,
        brand: Brand,
        brand_index: int,
        brand_total: int,
    ) -> FetchBrandSummary | None:
        """
        /**
         * 단일 브랜드의 카테고리·섹션·아티클을 Zendesk에서 수집해 DB에 반영한다.
         * @returns {FetchBrandSummary | None} Help Center 없으면 None
         */
        """
        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=brand_index,
            brand_name=brand.name,
            phase="brand_meta",
            message=f"브랜드 메타 조회 중 ({brand_index}/{brand_total}): {brand.name}",
        )
        brand_meta_url = f"https://{instance.subdomain}.zendesk.com/api/v2/brands/{brand.a_brand_id}"
        brand_meta_payload = await cls._fetch_json_with_context(
            url=brand_meta_url,
            email=instance.email,
            api_token=instance.api_token,
            brand_name=brand.name,
            fetch_step="brand_meta",
        )
        brand_meta = brand_meta_payload.get("brand", {})
        if isinstance(brand_meta, dict):
            meta_subdomain = brand_meta.get("subdomain")
            if isinstance(meta_subdomain, str) and meta_subdomain.strip():
                brand.subdomain = meta_subdomain.strip()
            brand.has_help_center = bool(brand_meta.get("has_help_center", brand.has_help_center))

        if not brand.has_help_center:
            logger.info(
                "브랜드 수집 건너뜀: instance_id=%s, brand=%s, reason=has_help_center=false",
                instance_id,
                brand.name,
            )
            return None

        logger.info("브랜드 수집 시작: instance_id=%s, brand=%s(%s)", instance_id, brand.name, brand.subdomain)
        summary = FetchBrandSummary(brand_id=brand.id, brand_name=brand.name)

        base_url = f"https://{brand.subdomain}.zendesk.com/api/v2/help_center"
        categories_url = f"{base_url}/categories.json"

        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=brand_index,
            brand_name=brand.name,
            phase="categories",
            message=f"{brand.name} 카테고리 수집 중",
        )
        categories_payload = await cls._fetch_json_with_context(
            url=categories_url,
            email=instance.email,
            api_token=instance.api_token,
            brand_name=brand.name,
            fetch_step="categories",
        )
        category_items = categories_payload.get("categories", [])
        summary.categories = await cls._sync_categories(
            session=session,
            instance_id=instance_id,
            brand=brand,
            categories=category_items,
        )
        brand_category_a_ids = {item["id"] for item in category_items}

        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=brand_index,
            brand_name=brand.name,
            phase="sections",
            message=f"{brand.name} 섹션 수집 중",
        )
        sections_payload = await cls._fetch_json_with_context(
            url=f"{base_url}/sections.json",
            email=instance.email,
            api_token=instance.api_token,
            brand_name=brand.name,
            fetch_step="sections",
        )
        section_items = sections_payload.get("sections", [])
        summary.sections = await cls._sync_sections(
            session=session,
            instance_id=instance_id,
            brand_category_a_ids=brand_category_a_ids,
            sections=section_items,
        )
        brand_section_a_ids = {item["id"] for item in section_items}

        article_items = await cls._fetch_all_help_center_articles(
            instance_id=instance_id,
            brand_index=brand_index,
            base_url=base_url,
            email=instance.email,
            api_token=instance.api_token,
            brand_name=brand.name,
        )

        await cls._enrich_articles_with_attachment_flags(
            instance_id=instance_id,
            brand_index=brand_index,
            brand_subdomain=brand.subdomain,
            email=instance.email,
            api_token=instance.api_token,
            brand_name=brand.name,
            article_items=article_items,
        )

        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=brand_index,
            brand_name=brand.name,
            phase="saving",
            message=f"{brand.name} DB 저장 중 ({len(article_items):,} 아티클)",
            articles_collected=len(article_items),
        )
        summary.articles = await cls._sync_articles(
            session=session,
            instance_id=instance_id,
            brand_subdomain=brand.subdomain,
            brand_section_a_ids=brand_section_a_ids,
            articles=article_items,
        )

        logger.info(
            "브랜드 수집 완료: instance_id=%s, brand=%s, categories=%s, sections=%s, articles=%s",
            instance_id,
            brand.name,
            summary.categories.total,
            summary.sections.total,
            summary.articles.total,
        )
        return summary

    @classmethod
    async def sync_source_brand(
        cls,
        session: AsyncSession,
        *,
        instance_id: int,
        brand_id: int,
    ) -> list[FetchBrandSummary]:
        """
        /**
         * 선택한 브랜드 한 개만 수집한다.
         * @param {int} instance_id 인스턴스 ID
         * @param {int} brand_id DB 브랜드 PK
         * @returns {list[FetchBrandSummary]} 수집 결과(0~1건)
         */
        """
        instance = await session.get(Instance, instance_id)
        if instance is None:
            raise ValueError("인스턴스를 찾을 수 없습니다.")

        brand = await session.scalar(
            select(Brand).where(Brand.id == brand_id, Brand.instance_id == instance_id)
        )
        if brand is None:
            raise ValueError("브랜드를 찾을 수 없습니다.")
        if not brand.is_selected:
            raise ValueError("인스턴스에 선택되지 않은 브랜드입니다.")

        await FetchProgressTracker.start(instance_id)
        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=0,
            brand_name=brand.name,
            phase="preparing",
            message=f"「{brand.name}」 브랜드 수집을 준비하는 중입니다.",
        )

        await cls._ensure_brands(session=session, instance=instance)
        await FetchProgressTracker.set_brand_total(instance_id, 1)

        summary = await cls._sync_one_brand(
            session,
            instance=instance,
            instance_id=instance_id,
            brand=brand,
            brand_index=1,
            brand_total=1,
        )
        summaries = [summary] if summary is not None else []

        instance.last_fetched_at = datetime.now(UTC)
        await session.commit()
        logger.info(
            "브랜드 단건 수집 완료: instance_id=%s, brand_id=%s, brand=%s",
            instance_id,
            brand_id,
            brand.name,
        )
        return summaries

    @classmethod
    async def sync_source_instance(cls, session: AsyncSession, instance_id: int) -> list[FetchBrandSummary]:
        """
        /**
         * 소스 인스턴스의 선택된 브랜드 데이터를 순차 수집한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} instance_id 수집 대상 인스턴스 ID
         * @returns {list[FetchBrandSummary]} 브랜드별 수집 결과 요약
         */
        """
        instance = await session.get(Instance, instance_id)
        if instance is None:
            raise ValueError("인스턴스를 찾을 수 없습니다.")

        await FetchProgressTracker.start(instance_id)
        await FetchProgressTracker.update_brand_step(
            instance_id,
            brand_index=0,
            brand_name="",
            phase="preparing",
            message="전체 브랜드 수집을 준비하는 중입니다.",
        )

        await cls._ensure_brands(session=session, instance=instance)

        brands_query = select(Brand).where(
            Brand.instance_id == instance_id,
            Brand.is_selected.is_(True),
            Brand.has_help_center.is_(True),
        )
        brands_result = await session.execute(brands_query)
        brands = brands_result.scalars().all()
        brand_total = len(brands)
        await FetchProgressTracker.set_brand_total(instance_id, brand_total)

        summaries: list[FetchBrandSummary] = []
        brand_index = 0

        # 브랜드별로 순차 호출하여 API rate limit 초과를 방지한다.
        for brand in brands:
            brand_index += 1
            summary = await cls._sync_one_brand(
                session,
                instance=instance,
                instance_id=instance_id,
                brand=brand,
                brand_index=brand_index,
                brand_total=brand_total,
            )
            if summary is not None:
                summaries.append(summary)

        instance.last_fetched_at = datetime.now(UTC)
        await session.commit()
        logger.info("인스턴스 수집 완료: instance_id=%s, processed_brands=%s", instance_id, len(summaries))

        return summaries

    @classmethod
    async def get_fetch_detail(cls, session: AsyncSession, instance_id: int) -> dict:
        """
        /**
         * DB에 저장된 수집 데이터를 브랜드 트리 형태로 조회한다.
         * @param {AsyncSession} session 비동기 DB 세션
         * @param {int} instance_id 조회할 소스 인스턴스 ID
         * @returns {dict} 수집 요약 및 브랜드 트리 데이터
         */
        """
        instance = await session.get(Instance, instance_id)
        if instance is None:
            raise ValueError("인스턴스를 찾을 수 없습니다.")
        brands = (
            await session.execute(
                select(Brand)
                .where(Brand.instance_id == instance_id, Brand.is_selected.is_(True))
                .order_by(Brand.name.asc())
            )
        ).scalars().all()
        categories = (
            await session.execute(
                select(Category).where(Category.instance_id == instance_id).order_by(Category.name.asc())
            )
        ).scalars().all()
        sections = (
            await session.execute(
                select(Section).where(Section.instance_id == instance_id).order_by(Section.name.asc())
            )
        ).scalars().all()
        articles = (
            await session.execute(
                select(Article).where(Article.instance_id == instance_id).order_by(Article.title.asc())
            )
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
        for brand in brands:
            brand_categories = categories_by_brand.get(brand.id, [])

            def _articles_for_brand_section(section: Section) -> list[dict]:
                return [
                    {
                        "id": article.id,
                        "a_id": article.a_id,
                        "title": article.title,
                        "draft": article.draft,
                        "html_url": article.html_url
                        or cls._build_article_html_url(
                            brand_subdomain=brand.subdomain,
                            article_a_id=article.a_id,
                            locale=article.locale,
                            draft=article.draft,
                        ),
                        "has_attachments": article.has_attachments,
                    }
                    for article in articles_by_section_a_id.get(section.a_id, [])
                ]

            brand_node = {
                "id": brand.id,
                "a_brand_id": brand.a_brand_id,
                "name": brand.name,
                "subdomain": brand.subdomain,
                "has_help_center": brand.has_help_center,
                "categories": [],
            }

            for category in brand_categories:
                category_sections = sections_by_category_a_id.get(category.a_id, [])
                category_node = {
                    "id": category.id,
                    "a_id": category.a_id,
                    "name": category.name,
                    "sections": build_nested_section_nodes(
                        category_sections,
                        build_articles=_articles_for_brand_section,
                    ),
                }

                brand_node["categories"].append(category_node)

            tree.append(brand_node)

        return {
            "instance_id": instance.id,
            "instance_name": instance.name or instance.subdomain,
            "last_fetched_at": instance.last_fetched_at,
            "summary": {
                "total_brands": len(brands),
                "total_categories": len(categories),
                "total_sections": len(sections),
                "total_articles": len(articles),
            },
            "brands": tree,
        }
