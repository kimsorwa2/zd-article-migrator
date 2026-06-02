"""
소스 인스턴스 아티클 본문 이미지 → AI-OCR → 타겟 인스턴스 아티클 생성 서비스.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article, Brand, Category, Instance, Section
from services.ai_ocr_log import AiOcrLogCollector, AiOcrServiceError
from services.ai_ocr_service import AiOcrService, html_body_to_preview_text
from services.article_from_image import image_bytes_to_article, resolve_media_type
from services.migration_service import INLINE_ARTICLE_ATTACHMENT_URL_PATTERN
from services.zendesk_client import ZendeskClient, ZendeskClientError

IMG_SRC_PATTERN = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_AVAILABILITY_OK = "ok"
IMAGE_AVAILABILITY_EXTERNAL_PASTE = "external_paste"
IMAGE_AVAILABILITY_UNKNOWN = "unknown"
EXTERNAL_PASTE_HINT = (
    "Zendesk 에디터에서 이미지를 '파일 업로드'로 다시 넣거나, "
    "이 화면에서 로컬 이미지 파일을 지정한 뒤 OCR을 실행하세요."
)


class ImageConvertService:
    """
    /**
     * 이미지가 삽입된 소스 아티클을 OCR 분석해 타겟 Help Center 아티클 초안을 만든다.
     */
    """

    @classmethod
    def extract_image_urls(cls, body: str | None) -> list[str]:
        """
        /**
         * HTML 본문에서 OCR 대상 이미지 URL을 순서대로 추출한다.
         * @param {str | None} body 아티클 HTML 본문
         * @returns {list[str]} 중복 제거된 이미지 URL 목록
         */
        """
        if not body:
            return []

        found: list[str] = []
        seen: set[str] = set()

        def add_url(raw_url: str) -> None:
            url = raw_url.strip()
            if not url or url in seen:
                return
            seen.add(url)
            found.append(url)

        for match in IMG_SRC_PATTERN.finditer(body):
            add_url(match.group(1))

        for match in INLINE_ARTICLE_ATTACHMENT_URL_PATTERN.finditer(body):
            add_url(match.group(0))

        return found

    @classmethod
    def _article_has_inline_images(cls, body: str | None, has_attachments: bool) -> bool:
        """
        /**
         * 아티클이 OCR 변환 대상(본문 이미지)인지 판별한다.
         */
        """
        if cls.extract_image_urls(body):
            return True
        if not body:
            return has_attachments
        lowered = body.lower()
        return "<img" in lowered or "article_attachments" in lowered or has_attachments

    @classmethod
    async def _get_instance(cls, session: AsyncSession, instance_id: int) -> Instance:
        instance = await session.get(Instance, instance_id)
        if instance is None:
            raise ValueError("인스턴스를 찾을 수 없습니다.")
        return instance

    @classmethod
    async def _get_known_subdomains(cls, session: AsyncSession, instance_id: int) -> set[str]:
        """
        /**
         * 인스턴스 메인·브랜드 서브도메인 집합을 반환한다(외부 붙여넣기 URL 판별용).
         */
        """
        instance = await cls._get_instance(session, instance_id)
        subdomains = {instance.subdomain.strip().lower()}
        rows = await session.execute(select(Brand.subdomain).where(Brand.instance_id == instance_id))
        for (subdomain,) in rows.all():
            if subdomain and subdomain.strip():
                subdomains.add(subdomain.strip().lower())
        return subdomains

    @classmethod
    def _diagnose_image_source(
        cls,
        source_url: str,
        *,
        known_subdomains: set[str],
        attachment_meta: dict[str, dict[str, str]],
    ) -> tuple[str, str | None]:
        """
        /**
         * 본문 이미지 URL이 API로 받을 수 있는지 사전 진단한다.
         * @returns {tuple} (availability, reason)
         */
        """
        inline_match = INLINE_ARTICLE_ATTACHMENT_URL_PATTERN.search(source_url)
        if inline_match is None:
            return IMAGE_AVAILABILITY_UNKNOWN, None

        attachment_id = inline_match.group(1)
        if attachment_meta.get(attachment_id):
            return IMAGE_AVAILABILITY_OK, None

        parsed = urlparse(source_url)
        host = (parsed.hostname or "").lower()
        if host.endswith(".zendesk.com"):
            host_subdomain = host.split(".", maxsplit=1)[0]
            if host_subdomain not in known_subdomains:
                return (
                    IMAGE_AVAILABILITY_EXTERNAL_PASTE,
                    (
                        f"본문 URL이 현재 인스턴스에 없는 Zendesk 호스트({host_subdomain})를 가리킵니다. "
                        "다른 Help Center/브랜드에서 이미지를 붙여넣으면 파일이 이 계정에 복사되지 않아 "
                        f"API로 다운로드할 수 없습니다. {EXTERNAL_PASTE_HINT}"
                    ),
                )

        if "article_attachments" in source_url and attachment_id not in attachment_meta:
            return (
                IMAGE_AVAILABILITY_EXTERNAL_PASTE,
                (
                    "인라인 첨부 URL이 있으나 이 아티클의 첨부 목록(attachments API)에 없습니다. "
                    f"다른 Zendesk에서 붙여넣은 이미지일 수 있습니다. {EXTERNAL_PASTE_HINT}"
                ),
            )

        return IMAGE_AVAILABILITY_UNKNOWN, None

    @classmethod
    async def _get_article(cls, session: AsyncSession, *, instance_id: int, article_id: int) -> Article:
        article = await session.scalar(
            select(Article).where(Article.id == article_id, Article.instance_id == instance_id)
        )
        if article is None:
            raise ValueError("아티클을 찾을 수 없습니다.")
        return article

    @classmethod
    async def _resolve_brand_and_section(
        cls,
        session: AsyncSession,
        *,
        instance_id: int,
        article: Article,
    ) -> tuple[Brand, Section]:
        """
        /**
         * 아티클이 속한 브랜드·섹션을 DB에서 조회한다.
         */
        """
        section = await session.scalar(
            select(Section).where(
                Section.instance_id == instance_id,
                Section.a_id == article.a_section_id,
            )
        )
        if section is None:
            raise ValueError("아티클 섹션 정보를 찾을 수 없습니다. 인스턴스 데이터를 다시 수집하세요.")

        category = await session.scalar(
            select(Category).where(
                Category.instance_id == instance_id,
                Category.a_id == section.a_category_id,
            )
        )
        if category is None:
            raise ValueError("아티클 카테고리 정보를 찾을 수 없습니다.")

        brand = await session.get(Brand, category.brand_id)
        if brand is None or brand.instance_id != instance_id:
            raise ValueError("아티클 브랜드 정보를 찾을 수 없습니다.")

        return brand, section

    @classmethod
    def _rewrite_inline_attachment_url(cls, url: str, *, brand_subdomain: str) -> str | None:
        """
        /**
         * 본문에 남아 있는 타 브랜드 호스트의 인라인 첨부 URL을 현재 브랜드 호스트로 맞춘다.
         * @param {str} url 절대 URL
         * @param {str} brand_subdomain 아티클이 속한 Help Center 브랜드 서브도메인
         * @returns {str | None} 재작성된 URL(인라인 첨부가 아니면 None)
         */
        """
        match = INLINE_ARTICLE_ATTACHMENT_URL_PATTERN.search(url)
        if match is None:
            return None
        attachment_id = match.group(1)
        return f"https://{brand_subdomain}.zendesk.com/hc/article_attachments/{attachment_id}"

    @classmethod
    def _normalize_image_url(cls, url: str, *, brand_subdomain: str) -> str:
        """
        /**
         * 상대 경로 이미지 URL을 절대 URL로 변환한다.
         * Zendesk 인라인 첨부는 본문에 다른 브랜드 호스트가 남아 있어도 현재 브랜드로 통일한다.
         */
        """
        trimmed = url.strip()
        if trimmed.startswith("//"):
            absolute = f"https:{trimmed}"
        elif trimmed.startswith("/"):
            absolute = f"https://{brand_subdomain}.zendesk.com{trimmed}"
        elif trimmed.startswith("http://") or trimmed.startswith("https://"):
            absolute = trimmed
        else:
            absolute = urljoin(f"https://{brand_subdomain}.zendesk.com/", trimmed)

        rewritten = cls._rewrite_inline_attachment_url(absolute, brand_subdomain=brand_subdomain)
        return rewritten if rewritten is not None else absolute

    @classmethod
    def _guess_filename(cls, url: str, *, index: int) -> str:
        path = urlparse(url).path
        name = Path(path).name
        if name and "." in name:
            return name
        return f"article-image-{index + 1}.jpg"

    @classmethod
    def _is_supported_image(cls, *, content_type: str, filename: str) -> bool:
        if content_type.lower().startswith("image/"):
            return Path(filename).suffix.lower() in IMAGE_EXTENSIONS or content_type.lower() in {
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif",
            }
        return Path(filename).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}

    @classmethod
    async def _load_attachment_meta(
        cls,
        *,
        instance: Instance,
        brand_subdomain: str,
        article_a_id: int,
    ) -> dict[str, dict[str, str]]:
        """
        /**
         * Zendesk 첨부 API에서 content_url/id → 파일 메타를 조회한다.
         */
        """
        try:
            payload = await ZendeskClient.get_json(
                url=(
                    f"https://{brand_subdomain}.zendesk.com/api/v2/help_center/"
                    f"articles/{article_a_id}/attachments.json"
                ),
                email=instance.email,
                api_token=instance.api_token,
            )
        except ZendeskClientError:
            return {}

        mapping: dict[str, dict[str, str]] = {}
        for attachment in payload.get("article_attachments", []):
            content_url = attachment.get("content_url")
            attachment_id = attachment.get("id")
            meta = {
                "filename": str(attachment.get("file_name") or ""),
                "content_type": str(attachment.get("content_type") or "application/octet-stream"),
                "content_url": str(content_url) if content_url else "",
            }
            if content_url:
                mapping[str(content_url)] = meta
                normalized_content_url = cls._normalize_image_url(
                    str(content_url),
                    brand_subdomain=brand_subdomain,
                )
                mapping[normalized_content_url] = meta
            if attachment_id is not None:
                mapping[str(attachment_id)] = meta
        return mapping

    @classmethod
    async def _download_image(
        cls,
        *,
        instance: Instance,
        brand_subdomain: str,
        source_url: str,
        index: int,
        attachment_meta: dict[str, dict[str, str]],
        known_subdomains: set[str] | None = None,
    ) -> tuple[bytes, str, str]:
        """
        /**
         * 소스 Zendesk에서 이미지 바이너리를 다운로드한다.
         * @returns {tuple} (bytes, filename, content_type)
         */
        """
        normalized_url = cls._normalize_image_url(source_url, brand_subdomain=brand_subdomain)
        meta = attachment_meta.get(normalized_url) or attachment_meta.get(source_url)

        inline_match = INLINE_ARTICLE_ATTACHMENT_URL_PATTERN.search(normalized_url)
        if inline_match is not None:
            attachment_id = inline_match.group(1)
            id_meta = attachment_meta.get(attachment_id)
            if id_meta is not None:
                meta = id_meta if meta is None else meta
            content_url = (id_meta or {}).get("content_url") if id_meta else None
            download_url = (
                content_url
                if content_url
                else f"https://{brand_subdomain}.zendesk.com/hc/article_attachments/{attachment_id}"
            )
        else:
            download_url = normalized_url

        filename = (meta or {}).get("filename") or cls._guess_filename(download_url, index=index)
        content_type = (meta or {}).get("content_type") or "application/octet-stream"

        try:
            binary = await ZendeskClient.get_bytes(
                url=download_url,
                email=instance.email,
                api_token=instance.api_token,
            )
        except ZendeskClientError as error:
            if "status=404" in str(error):
                subdomains = known_subdomains or {brand_subdomain.lower()}
                _, paste_reason = cls._diagnose_image_source(
                    source_url,
                    known_subdomains=subdomains,
                    attachment_meta=attachment_meta,
                )
                if paste_reason:
                    raise ValueError(paste_reason) from error
                raise ValueError(
                    "본문 이미지를 Zendesk에서 찾을 수 없습니다. "
                    "파일이 삭제되었거나 본문 URL이 유효하지 않을 수 있습니다. "
                    f"{EXTERNAL_PASTE_HINT}"
                ) from error
            raise

        if not cls._is_supported_image(content_type=content_type, filename=filename):
            raise ValueError(f"지원하지 않는 이미지 형식입니다: {filename}")

        return binary, filename, content_type

    @classmethod
    async def list_image_articles(
        cls,
        session: AsyncSession,
        *,
        source_instance_id: int,
        query: str | None = None,
    ) -> list[dict]:
        """
        /**
         * 본문에 이미지가 포함된 소스 아티클 목록을 반환한다.
         */
        """
        await cls._get_instance(session, source_instance_id)

        stmt = (
            select(Article, Section.name)
            .outerjoin(
                Section,
                (Section.instance_id == Article.instance_id) & (Section.a_id == Article.a_section_id),
            )
            .where(
                Article.instance_id == source_instance_id,
                or_(
                    Article.body.ilike("%<img%"),
                    Article.body.ilike("%article_attachments%"),
                    Article.has_attachments.is_(True),
                ),
            )
            .order_by(Article.title.asc())
        )

        rows = await session.execute(stmt)
        items: list[dict] = []
        needle = query.strip().lower() if query and query.strip() else None

        for article, section_name in rows.all():
            if not cls._article_has_inline_images(article.body, article.has_attachments):
                continue
            if needle and needle not in article.title.lower():
                continue

            image_count = len(cls.extract_image_urls(article.body))
            if image_count == 0 and article.has_attachments:
                image_count = 1

            items.append(
                {
                    "id": article.id,
                    "a_id": article.a_id,
                    "title": article.title,
                    "html_url": article.html_url,
                    "section_name": section_name or "—",
                    "image_count": image_count,
                    "label_names": article.label_names or [],
                }
            )

        return items

    @classmethod
    async def get_article_detail(
        cls,
        session: AsyncSession,
        *,
        source_instance_id: int,
        article_id: int,
    ) -> dict:
        """
        /**
         * 선택한 아티클 상세와 본문 이미지 URL 목록을 반환한다.
         */
        """
        article = await cls._get_article(session, instance_id=source_instance_id, article_id=article_id)
        brand, section = await cls._resolve_brand_and_section(
            session,
            instance_id=source_instance_id,
            article=article,
        )

        instance = await cls._get_instance(session, source_instance_id)
        known_subdomains = await cls._get_known_subdomains(session, source_instance_id)
        attachment_meta = await cls._load_attachment_meta(
            instance=instance,
            brand_subdomain=brand.subdomain,
            article_a_id=article.a_id,
        )

        image_urls = cls.extract_image_urls(article.body)
        images: list[dict] = []
        for index, url in enumerate(image_urls):
            availability, availability_reason = cls._diagnose_image_source(
                url,
                known_subdomains=known_subdomains,
                attachment_meta=attachment_meta,
            )
            images.append(
                {
                    "index": index,
                    "source_url": cls._normalize_image_url(url, brand_subdomain=brand.subdomain),
                    "filename": cls._guess_filename(url, index=index),
                    "availability": availability,
                    "availability_reason": availability_reason,
                }
            )

        return {
            "id": article.id,
            "a_id": article.a_id,
            "title": article.title,
            "html_url": article.html_url,
            "section_name": section.name,
            "label_names": article.label_names or [],
            "body": article.body,
            "images": images,
            "brand_subdomain": brand.subdomain,
        }

    @classmethod
    async def get_image_preview_bytes(
        cls,
        session: AsyncSession,
        *,
        source_instance_id: int,
        article_id: int,
        image_index: int,
    ) -> tuple[bytes, str]:
        """
        /**
         * 아티클 본문 이미지 미리보기 바이너리를 반환한다.
         */
        """
        article = await cls._get_article(session, instance_id=source_instance_id, article_id=article_id)
        brand, _section = await cls._resolve_brand_and_section(
            session,
            instance_id=source_instance_id,
            article=article,
        )

        image_urls = cls.extract_image_urls(article.body)
        if image_index < 0 or image_index >= len(image_urls):
            raise ValueError("이미지 인덱스가 올바르지 않습니다.")

        instance = await cls._get_instance(session, source_instance_id)
        known_subdomains = await cls._get_known_subdomains(session, source_instance_id)
        attachment_meta = await cls._load_attachment_meta(
            instance=instance,
            brand_subdomain=brand.subdomain,
            article_a_id=article.a_id,
        )

        source_url = image_urls[image_index]
        availability, availability_reason = cls._diagnose_image_source(
            source_url,
            known_subdomains=known_subdomains,
            attachment_meta=attachment_meta,
        )
        if availability == IMAGE_AVAILABILITY_EXTERNAL_PASTE and availability_reason:
            raise ValueError(availability_reason)

        binary, filename, content_type = await cls._download_image(
            instance=instance,
            brand_subdomain=brand.subdomain,
            source_url=source_url,
            index=image_index,
            attachment_meta=attachment_meta,
            known_subdomains=known_subdomains,
        )
        _ = filename
        return binary, content_type

    @classmethod
    def _merge_ocr_results(
        cls,
        *,
        source_title: str,
        source_labels: list[str],
        ocr_results: list[dict],
    ) -> dict:
        """
        /**
         * 여러 이미지 OCR 결과를 하나의 아티클 초안으로 병합한다.
         */
        """
        if not ocr_results:
            raise ValueError("OCR 결과가 없습니다.")

        if len(ocr_results) == 1:
            single = ocr_results[0]
            labels = list(dict.fromkeys([*(source_labels or []), *(single.get("label_names") or [])]))
            return {
                "title": str(single.get("title") or source_title).strip() or source_title,
                "html_body": str(single.get("html_body") or ""),
                "label_names": labels[:7],
                "detected_product": str(single.get("detected_product") or "unknown"),
                "maintenance_cycle": single.get("maintenance_cycle"),
            }

        html_parts: list[str] = []
        merged_labels = list(dict.fromkeys(source_labels or []))
        maintenance_cycle = None

        for index, result in enumerate(ocr_results, start=1):
            html_parts.append(f"<h3>이미지 {index}</h3>")
            html_parts.append(str(result.get("html_body") or ""))
            for label in result.get("label_names") or []:
                if label not in merged_labels:
                    merged_labels.append(str(label))
            if maintenance_cycle is None and result.get("maintenance_cycle"):
                maintenance_cycle = result.get("maintenance_cycle")

        first = ocr_results[0]
        return {
            "title": str(first.get("title") or source_title).strip() or source_title,
            "html_body": "\n".join(html_parts),
            "label_names": merged_labels[:7],
            "detected_product": str(first.get("detected_product") or "unknown"),
            "maintenance_cycle": maintenance_cycle,
        }

    @classmethod
    async def analyze_article(
        cls,
        session: AsyncSession,
        *,
        source_instance_id: int,
        article_id: int,
        image_overrides: dict[int, tuple[bytes, str, str]] | None = None,
    ) -> dict:
        """
        /**
         * 소스 아티클 본문 이미지를 AI-OCR 분석해 타겟 생성용 초안을 만든다.
         */
        """
        log = AiOcrLogCollector()
        article = await cls._get_article(session, instance_id=source_instance_id, article_id=article_id)
        instance = await cls._get_instance(session, source_instance_id)
        brand, section = await cls._resolve_brand_and_section(
            session,
            instance_id=source_instance_id,
            article=article,
        )

        image_urls = cls.extract_image_urls(article.body)
        if not image_urls:
            message = "본문에서 OCR 가능한 이미지를 찾지 못했습니다."
            log.error("이미지 없음", message)
            raise AiOcrServiceError(message, log)

        try:
            provider, api_key, model_id, api_secret, aws_region = await AiOcrService._require_active_vision_config(
                session
            )
        except ValueError as error:
            log.error("설정 오류", str(error))
            raise AiOcrServiceError(str(error), log) from error

        system_prompt, user_prompt, _prompt_template_id = await AiOcrService._get_resolved_prompts(session)
        known_subdomains = await cls._get_known_subdomains(session, source_instance_id)
        attachment_meta = await cls._load_attachment_meta(
            instance=instance,
            brand_subdomain=brand.subdomain,
            article_a_id=article.a_id,
        )

        log.info(
            "이미지 아티클 OCR 시작",
            "\n".join(
                [
                    f"소스: {instance.name or instance.subdomain} (article a_id={article.a_id})",
                    f"제목: {article.title}",
                    f"섹션: {section.name}",
                    f"이미지 수: {len(image_urls)}",
                ]
            ),
        )

        ocr_results: list[dict] = []
        image_previews: list[dict] = []

        for index, source_url in enumerate(image_urls):
            override = (image_overrides or {}).get(index)
            if override is not None:
                binary, filename, content_type = override
                log.info(
                    f"이미지 {index + 1} 로컬 파일 사용",
                    f"Zendesk 다운로드를 건너뛰고 업로드한 파일로 OCR합니다: {filename}",
                )
            else:
                try:
                    binary, filename, content_type = await cls._download_image(
                        instance=instance,
                        brand_subdomain=brand.subdomain,
                        source_url=source_url,
                        index=index,
                        attachment_meta=attachment_meta,
                        known_subdomains=known_subdomains,
                    )
                except (ValueError, ZendeskClientError) as error:
                    log.error(f"이미지 {index + 1} 다운로드 실패", str(error))
                    continue

            preview_data_url = (
                f"data:{content_type};base64,{base64.b64encode(binary).decode('ascii')}"
            )
            image_previews.append(
                {
                    "index": index,
                    "filename": filename,
                    "preview_data_url": preview_data_url,
                }
            )

            log.info(
                f"이미지 {index + 1} OCR 분석",
                f"파일: {filename}\n크기: {max(1, len(binary) // 1024)}KB",
            )

            try:
                media_type = resolve_media_type(filename)
                result = image_bytes_to_article(
                    binary,
                    filename,
                    media_type,
                    provider=provider,  # type: ignore[arg-type]
                    api_key=api_key,
                    model=model_id,
                    api_secret=api_secret,
                    aws_region=aws_region,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    log=log,
                )
            except (RuntimeError, json.JSONDecodeError) as error:
                log.error(f"이미지 {index + 1} OCR 실패", str(error))
                continue

            ocr_results.append(result)
            log.success(
                f"이미지 {index + 1} OCR 완료",
                AiOcrLogCollector.format_json(
                    {
                        "title": result.get("title"),
                        "detected_product": result.get("detected_product"),
                        "html_body_length": len(str(result.get("html_body") or "")),
                    }
                ),
            )

        if not ocr_results:
            message = "모든 이미지 OCR에 실패했습니다."
            log.error("OCR 실패", message)
            raise AiOcrServiceError(message, log)

        merged = cls._merge_ocr_results(
            source_title=article.title,
            source_labels=article.label_names or [],
            ocr_results=ocr_results,
        )
        html_body = merged["html_body"]
        payload = {
            "source_article_id": article.id,
            "source_article_a_id": article.a_id,
            "source_article_title": article.title,
            "title": merged["title"],
            "html_body": html_body,
            "label_names": merged["label_names"],
            "detected_product": merged["detected_product"],
            "maintenance_cycle": merged["maintenance_cycle"],
            "body_preview_text": html_body_to_preview_text(html_body),
            "image_count": len(image_urls),
            "ocr_image_count": len(ocr_results),
            "image_previews": image_previews,
        }

        history_source_filename = (
            image_previews[0]["filename"] if image_previews else f"article-{article.a_id}.png"
        )
        history_row = await AiOcrService._save_analysis_history(
            session,
            source_filename=history_source_filename,
            title=payload["title"],
            html_body=html_body,
            label_names=payload["label_names"],
            detected_product=payload["detected_product"],
            maintenance_cycle=payload["maintenance_cycle"],
            body_preview_text=payload["body_preview_text"],
            ai_model=model_id,
        )
        await session.commit()

        log.success(
            "아티클 OCR 변환 완료",
            AiOcrLogCollector.format_json(
                {
                    "title": payload["title"],
                    "ocr_image_count": len(ocr_results),
                    "html_body_length": len(html_body),
                }
            ),
        )

        return {
            **payload,
            "history_id": history_row.id,
            "logs": log.to_list(),
        }
