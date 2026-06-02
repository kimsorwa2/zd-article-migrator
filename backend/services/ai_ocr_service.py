"""
AI-OCR: Google Gemini Vision 분석 및 Zendesk 아티클 생성 서비스.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AiOcrAnalysisHistory, AiOcrPromptTemplate, AiOcrSetting, Brand, Instance, Section
from services.ai_ocr_log import AiOcrLogCollector, AiOcrServiceError
from services.ai_model_options import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    normalize_model_for_save,
    resolve_gemini_model,
    resolve_openai_model,
)
from services.article_from_image import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    image_bytes_to_article,
    normalize_zendesk_html_body,
    resolve_media_type,
)
from services.zendesk_client import ZendeskClient, ZendeskClientError

SETTINGS_ROW_ID = 1
MAX_ANALYSIS_HISTORY = 50
MAX_PROMPT_TEMPLATES = 30
DEFAULT_PROMPT_NAME = "기본 매뉴얼 OCR"
PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "openai": "ChatGPT (OpenAI)",
}


class _HtmlTextExtractor(HTMLParser):
    """HTML 본문에서 텍스트만 추출한다."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def html_body_to_preview_text(html_body: str) -> str:
    """
    /**
     * html_body 태그를 제거하고 미리보기용 평문을 만든다.
     * @param {str} html_body HTML 본문
     * @returns {str} 읽기 쉬운 평문
     */
    """
    parser = _HtmlTextExtractor()
    parser.feed(html_body or "")
    parser.close()
    text = parser.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sanitize_history_model_segment(model_id: str) -> str:
    """라벨에 넣을 AI 모델 ID를 파일명 안전 문자로 정규화한다."""
    cleaned = re.sub(r"[^\w\-.]+", "_", model_id.strip()).strip("_")
    return cleaned or "unknown"


def _sanitize_history_image_name(source_filename: str) -> str:
    """
    /**
     * 이력 라벨용 이미지 파일명(확장자 제외)을 만든다.
     * @param {str} source_filename 업로드·다운로드된 원본 파일명
     */
    """
    stem = Path(source_filename).stem or source_filename
    safe = re.sub(r"[^\w\-가-힣]+", "_", stem).strip("_") or "image"
    return safe[:80]


def format_analysis_history_label(
    *,
    ai_model: str,
    image_name: str,
    created_at: datetime,
    sequence: int,
) -> str:
    """
    /**
     * 이력 셀렉트 옵션 라벨을 만든다.
     * @returns {str} 예: gemini-2.5-pro_CHICKEN25매뉴얼_2026-06-01_01
     */
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    date_part = created_at.astimezone(UTC).strftime("%Y-%m-%d")
    model_part = _sanitize_history_model_segment(ai_model)
    name_part = _sanitize_history_image_name(image_name)
    return f"{model_part}_{name_part}_{date_part}_{sequence:02d}"


def format_analysis_history_label_legacy(source_filename: str, created_at: datetime) -> str:
    """
    /**
     * 구 이력 행( display_label·ai_model 없음)용 폴백 라벨.
     */
    """
    stem = Path(source_filename).stem or source_filename
    safe_stem = re.sub(r"[^\w\-가-힣]+", "_", stem).strip("_") or "image"
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    timestamp = created_at.astimezone(UTC).strftime("%Y-%m-%d_%H-%M")
    return f"{safe_stem}_{timestamp}"


def resolve_history_row_label(row: AiOcrAnalysisHistory) -> str:
    """DB 행에서 UI 표시용 라벨을 반환한다."""
    if row.display_label and row.display_label.strip():
        return row.display_label.strip()
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if row.ai_model:
        return format_analysis_history_label(
            ai_model=row.ai_model,
            image_name=row.source_filename,
            created_at=created_at,
            sequence=row.id,
        )
    return format_analysis_history_label_legacy(row.source_filename, created_at)


def mask_api_key(api_key: str | None) -> str | None:
    """
    /**
     * API 키를 마스킹해 UI에 표시한다.
     * @param {str | None} api_key 저장된 Gemini API 키
     * @returns {str | None} 마스킹된 키
     */
    """
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"


class AiOcrService:
    """
    /**
     * AI-OCR 설정·분석·아티클 생성 비즈니스 로직.
     */
    """

    @classmethod
    def _provider_config(
        cls,
        account: str | None,
        api_key: str | None,
        *,
        model: str,
    ) -> dict:
        """
        /**
         * 제공자별 계정·키·모델 요약 dict를 만든다.
         */
        """
        return {
            "account": account,
            "has_api_key": bool(api_key),
            "api_key_masked": mask_api_key(api_key),
            "model": model,
        }

    @classmethod
    async def _ensure_settings_row(cls, session: AsyncSession) -> AiOcrSetting:
        """
        /**
         * 설정 단일 행(id=1)을 보장한다.
         */
        """
        row = await session.get(AiOcrSetting, SETTINGS_ROW_ID)
        if row is None:
            row = AiOcrSetting(
                id=SETTINGS_ROW_ID,
                active_provider="gemini",
                gemini_model=DEFAULT_GEMINI_MODEL,
                openai_model=DEFAULT_OPENAI_MODEL,
            )
            session.add(row)
            await session.flush()
        return row

    @classmethod
    async def _ensure_builtin_prompt(cls, session: AsyncSession) -> AiOcrPromptTemplate:
        """
        /**
         * 내장 기본 프롬프트 템플릿이 없으면 생성한다.
         */
        """
        existing = await session.scalar(
            select(AiOcrPromptTemplate).where(
                AiOcrPromptTemplate.is_builtin.is_(True),
                AiOcrPromptTemplate.name == DEFAULT_PROMPT_NAME,
            )
        )
        if existing is not None:
            return existing

        template = AiOcrPromptTemplate(
            name=DEFAULT_PROMPT_NAME,
            description="앱 기본 이미지→아티클 변환 프롬프트",
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            user_prompt=DEFAULT_USER_PROMPT,
            is_builtin=True,
        )
        session.add(template)
        await session.flush()
        return template

    @classmethod
    def _prompt_template_to_dict(cls, row: AiOcrPromptTemplate) -> dict:
        """
        /**
         * 프롬프트 템플릿 ORM을 API dict로 변환한다.
         */
        """
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "system_prompt": row.system_prompt,
            "user_prompt": row.user_prompt,
            "is_builtin": row.is_builtin,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    async def list_prompt_templates(cls, session: AsyncSession) -> list[dict]:
        """
        /**
         * 저장된 프롬프트 템플릿 목록을 반환한다.
         */
        """
        await cls._ensure_builtin_prompt(session)
        rows = await session.scalars(
            select(AiOcrPromptTemplate).order_by(
                AiOcrPromptTemplate.is_builtin.desc(),
                AiOcrPromptTemplate.updated_at.desc(),
            )
        )
        return [cls._prompt_template_to_dict(row) for row in rows]

    @classmethod
    async def create_prompt_template(
        cls,
        session: AsyncSession,
        *,
        name: str,
        description: str | None,
        system_prompt: str,
        user_prompt: str,
        set_active: bool = False,
    ) -> dict:
        """
        /**
         * 새 프롬프트 템플릿을 저장한다.
         */
        """
        await cls._ensure_builtin_prompt(session)
        count = await session.scalar(select(func.count()).select_from(AiOcrPromptTemplate))
        if count and count >= MAX_PROMPT_TEMPLATES:
            raise ValueError(f"프롬프트는 최대 {MAX_PROMPT_TEMPLATES}개까지 저장할 수 있습니다.")

        template = AiOcrPromptTemplate(
            name=name.strip(),
            description=description.strip() if description and description.strip() else None,
            system_prompt=system_prompt.strip(),
            user_prompt=user_prompt.strip(),
            is_builtin=False,
        )
        session.add(template)
        await session.flush()

        if set_active:
            settings = await cls._ensure_settings_row(session)
            settings.active_prompt_id = template.id

        await session.commit()
        await session.refresh(template)
        return cls._prompt_template_to_dict(template)

    @classmethod
    async def update_prompt_template(
        cls,
        session: AsyncSession,
        *,
        template_id: int,
        name: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
    ) -> dict:
        """
        /**
         * 프롬프트 템플릿을 수정한다.
         */
        """
        template = await session.get(AiOcrPromptTemplate, template_id)
        if template is None:
            raise ValueError("프롬프트를 찾을 수 없습니다.")

        if name is not None and name.strip():
            template.name = name.strip()
        if description is not None:
            template.description = description.strip() if description.strip() else None
        if system_prompt is not None and system_prompt.strip():
            template.system_prompt = system_prompt.strip()
        if user_prompt is not None and user_prompt.strip():
            template.user_prompt = user_prompt.strip()

        await session.commit()
        await session.refresh(template)
        return cls._prompt_template_to_dict(template)

    @classmethod
    async def delete_prompt_template(cls, session: AsyncSession, *, template_id: int) -> None:
        """
        /**
         * 프롬프트 템플릿을 삭제한다(내장 기본 템플릿은 삭제 불가).
         */
        """
        template = await session.get(AiOcrPromptTemplate, template_id)
        if template is None:
            raise ValueError("프롬프트를 찾을 수 없습니다.")
        if template.is_builtin:
            raise ValueError("기본 프롬프트는 삭제할 수 없습니다.")

        settings = await cls._ensure_settings_row(session)
        if settings.active_prompt_id == template_id:
            builtin = await cls._ensure_builtin_prompt(session)
            settings.active_prompt_id = builtin.id

        await session.delete(template)
        await session.commit()

    @classmethod
    async def get_settings(cls, session: AsyncSession) -> dict:
        """
        /**
         * AI-OCR 설정을 조회한다(키는 마스킹).
         * @returns {dict} 활성 제공자·제공자별 계정·키·프롬프트 목록
         */
        """
        await cls._ensure_builtin_prompt(session)
        templates = await cls.list_prompt_templates(session)
        row = await session.get(AiOcrSetting, SETTINGS_ROW_ID)

        active_prompt_id = row.active_prompt_id if row else None
        if active_prompt_id is None and templates:
            active_prompt_id = templates[0]["id"]
            if row is None:
                row = await cls._ensure_settings_row(session)
            row.active_prompt_id = active_prompt_id
            await session.commit()

        if row is None:
            return {
                "active_provider": "gemini",
                "active_prompt_id": active_prompt_id,
                "gemini": cls._provider_config(None, None, model=DEFAULT_GEMINI_MODEL),
                "openai": cls._provider_config(None, None, model=DEFAULT_OPENAI_MODEL),
                "prompt_templates": templates,
                "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
                "default_user_prompt": DEFAULT_USER_PROMPT,
            }

        active_provider = row.active_provider if row.active_provider in PROVIDER_LABELS else "gemini"
        return {
            "active_provider": active_provider,
            "active_prompt_id": active_prompt_id,
            "gemini": cls._provider_config(
                row.gemini_account,
                row.gemini_api_key,
                model=resolve_gemini_model(row.gemini_model),
            ),
            "openai": cls._provider_config(
                row.openai_account,
                row.openai_api_key,
                model=resolve_openai_model(row.openai_model),
            ),
            "prompt_templates": templates,
            "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
            "default_user_prompt": DEFAULT_USER_PROMPT,
        }

    @classmethod
    async def save_settings(
        cls,
        session: AsyncSession,
        *,
        active_provider: str | None,
        gemini_account: str | None,
        gemini_api_key: str | None,
        openai_account: str | None,
        openai_api_key: str | None,
        gemini_model: str | None = None,
        openai_model: str | None = None,
        active_prompt_id: int | None = None,
    ) -> dict:
        """
        /**
         * AI-OCR 설정을 저장한다. api_key가 None이면 해당 제공자 기존 키를 유지한다.
         * @returns {dict} 저장 후 설정 요약
         */
        """
        row = await cls._ensure_settings_row(session)

        if active_provider in PROVIDER_LABELS:
            row.active_provider = active_provider

        row.gemini_account = gemini_account.strip() if gemini_account and gemini_account.strip() else None
        if gemini_api_key is not None and gemini_api_key.strip():
            row.gemini_api_key = gemini_api_key.strip()

        row.openai_account = openai_account.strip() if openai_account and openai_account.strip() else None
        if openai_api_key is not None and openai_api_key.strip():
            row.openai_api_key = openai_api_key.strip()

        if gemini_model is not None:
            normalized = normalize_model_for_save("gemini", gemini_model)
            if normalized:
                row.gemini_model = normalized

        if openai_model is not None:
            normalized = normalize_model_for_save("openai", openai_model)
            if normalized:
                row.openai_model = normalized

        if active_prompt_id is not None:
            template = await session.get(AiOcrPromptTemplate, active_prompt_id)
            if template is None:
                raise ValueError("선택한 프롬프트를 찾을 수 없습니다.")
            row.active_prompt_id = active_prompt_id

        await session.commit()
        await session.refresh(row)
        return await cls.get_settings(session)

    @classmethod
    async def _get_resolved_prompts(cls, session: AsyncSession) -> tuple[str, str]:
        """
        /**
         * OCR 분석에 사용할 활성 프롬프트 템플릿의 system·user 프롬프트를 반환한다.
         */
        """
        await cls._ensure_builtin_prompt(session)
        row = await session.get(AiOcrSetting, SETTINGS_ROW_ID)
        template: AiOcrPromptTemplate | None = None

        if row and row.active_prompt_id:
            template = await session.get(AiOcrPromptTemplate, row.active_prompt_id)

        if template is None:
            template = await cls._ensure_builtin_prompt(session)
            if row is not None and row.active_prompt_id != template.id:
                row.active_prompt_id = template.id
                await session.commit()

        return template.system_prompt, template.user_prompt

    @classmethod
    async def _require_active_vision_config(cls, session: AsyncSession) -> tuple[str, str, str]:
        """
        /**
         * 활성 AI 제공자·API 키·모델 ID를 반환한다.
         * @returns {tuple[str, str, str]} (provider, api_key, model_id)
         */
        """
        row = await session.get(AiOcrSetting, SETTINGS_ROW_ID)
        if row is None:
            raise ValueError("AI 설정이 없습니다. 우측 상단 설정에서 제공자와 API 키를 저장하세요.")

        provider = row.active_provider if row.active_provider in PROVIDER_LABELS else "gemini"
        if provider == "openai":
            if not row.openai_api_key:
                raise ValueError(
                    "ChatGPT(OpenAI) API 키가 설정되지 않았습니다. 설정에서 OpenAI 키를 저장하거나 Gemini로 변경하세요."
                )
            return provider, row.openai_api_key, resolve_openai_model(row.openai_model)

        if not row.gemini_api_key:
            raise ValueError(
                "Gemini API 키가 설정되지 않았습니다. 설정에서 Gemini 키를 저장하거나 ChatGPT로 변경하세요."
            )
        return provider, row.gemini_api_key, resolve_gemini_model(row.gemini_model)

    @classmethod
    async def analyze_image(
        cls,
        session: AsyncSession,
        *,
        filename: str,
        content: bytes,
    ) -> dict:
        """
        /**
         * 이미지를 분석해 아티클 초안 JSON을 반환한다.
         * @returns {dict} OCR 결과 + body_preview_text
         */
        """
        log = AiOcrLogCollector()
        try:
            provider, api_key, model_id = await cls._require_active_vision_config(session)
        except ValueError as error:
            log.error("설정 오류", str(error))
            raise AiOcrServiceError(str(error), log) from error

        provider_label = PROVIDER_LABELS.get(provider, provider)
        log.info(
            "OCR 분석 시작",
            f"AI: {provider_label}\n모델: {model_id}\n파일: {filename}\n이미지 크기: {max(1, len(content) // 1024)}KB",
        )

        try:
            media_type = resolve_media_type(filename)
        except ValueError as error:
            log.error("파일 형식 오류", str(error))
            raise AiOcrServiceError(str(error), log) from error

        try:
            system_prompt, user_prompt = await cls._get_resolved_prompts(session)
            result = image_bytes_to_article(
                content,
                filename,
                media_type,
                provider=provider,  # type: ignore[arg-type]
                api_key=api_key,
                model=model_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                log=log,
            )
        except (RuntimeError, json.JSONDecodeError) as error:
            log.error("AI 응답 처리 실패", str(error))
            raise AiOcrServiceError(str(error), log) from error

        html_body = str(result.get("html_body") or "")
        maintenance = result.get("maintenance_cycle")
        log.success(
            "OCR 분석 완료",
            AiOcrLogCollector.format_json(
                {
                    "title": result.get("title"),
                    "detected_product": result.get("detected_product"),
                    "maintenance_cycle": maintenance,
                    "label_names": result.get("label_names"),
                    "html_body_length": len(html_body),
                }
            ),
        )

        payload = {
            "title": str(result.get("title") or "").strip(),
            "html_body": html_body,
            "label_names": [str(label) for label in (result.get("label_names") or [])],
            "detected_product": str(result.get("detected_product") or "unknown"),
            "maintenance_cycle": str(maintenance) if maintenance else None,
            "body_preview_text": html_body_to_preview_text(html_body),
        }
        history_row = await cls._save_analysis_history(
            session,
            source_filename=filename,
            ai_model=model_id,
            **payload,
        )
        await session.commit()

        return {
            **payload,
            "history_id": history_row.id,
            "logs": log.to_list(),
        }

    @classmethod
    async def list_analysis_history(cls, session: AsyncSession, *, limit: int = MAX_ANALYSIS_HISTORY) -> list[dict]:
        """
        /**
         * 저장된 OCR 분석 이력을 최신순으로 반환한다(미리보기 복원용 전체 payload 포함).
         * @returns {list[dict]} 이력 목록
         */
        """
        rows = await session.scalars(
            select(AiOcrAnalysisHistory)
            .order_by(AiOcrAnalysisHistory.created_at.desc())
            .limit(limit)
        )
        items: list[dict] = []
        for row in rows:
            created_at = row.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            items.append(
                {
                    "id": row.id,
                    "label": resolve_history_row_label(row),
                    "source_filename": row.source_filename,
                    "title": row.title,
                    "html_body": row.html_body,
                    "label_names": row.label_names or [],
                    "detected_product": row.detected_product,
                    "maintenance_cycle": row.maintenance_cycle,
                    "body_preview_text": row.body_preview_text,
                    "created_at": created_at,
                }
            )
        return items

    @classmethod
    async def _allocate_history_sequence(
        cls,
        session: AsyncSession,
        *,
        ai_model: str,
        image_name: str,
        created_at: datetime,
    ) -> int:
        """
        /**
         * 같은 날·같은 모델·같은 이미지 파일명 기준 다음 순번을 반환한다.
         */
        """
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        created_at_utc = created_at.astimezone(UTC)
        day_start = created_at_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        model_part = _sanitize_history_model_segment(ai_model)
        name_part = _sanitize_history_image_name(image_name)
        date_part = created_at_utc.strftime("%Y-%m-%d")
        label_prefix = f"{model_part}_{name_part}_{date_part}_"

        same_day_count = await session.scalar(
            select(func.count())
            .select_from(AiOcrAnalysisHistory)
            .where(
                AiOcrAnalysisHistory.created_at >= day_start,
                AiOcrAnalysisHistory.created_at < day_end,
                AiOcrAnalysisHistory.display_label.like(f"{label_prefix}%"),
            )
        )
        return int(same_day_count or 0) + 1

    @classmethod
    async def _save_analysis_history(
        cls,
        session: AsyncSession,
        *,
        source_filename: str,
        title: str,
        html_body: str,
        label_names: list[str],
        detected_product: str,
        maintenance_cycle: str | None,
        body_preview_text: str,
        ai_model: str,
    ) -> AiOcrAnalysisHistory:
        """
        /**
         * OCR 분석 결과를 DB에 저장하고 오래된 이력을 정리한다.
         * @returns {AiOcrAnalysisHistory} 저장된 행
         */
        """
        created_at = datetime.now(UTC)
        sequence = await cls._allocate_history_sequence(
            session,
            ai_model=ai_model,
            image_name=source_filename,
            created_at=created_at,
        )
        display_label = format_analysis_history_label(
            ai_model=ai_model,
            image_name=source_filename,
            created_at=created_at,
            sequence=sequence,
        )
        row = AiOcrAnalysisHistory(
            source_filename=source_filename,
            ai_model=_sanitize_history_model_segment(ai_model),
            display_label=display_label,
            title=title,
            html_body=html_body,
            label_names=label_names,
            detected_product=detected_product,
            maintenance_cycle=maintenance_cycle,
            body_preview_text=body_preview_text,
            created_at=created_at,
        )
        session.add(row)
        await session.flush()
        await cls._trim_analysis_history(session)
        return row

    @classmethod
    async def _trim_analysis_history(cls, session: AsyncSession) -> None:
        """
        /**
         * 최대 보관 개수를 초과하는 오래된 OCR 이력을 삭제한다.
         */
        """
        stale_ids = list(
            await session.scalars(
                select(AiOcrAnalysisHistory.id)
                .order_by(AiOcrAnalysisHistory.created_at.desc())
                .offset(MAX_ANALYSIS_HISTORY)
            )
        )
        if not stale_ids:
            return
        await session.execute(delete(AiOcrAnalysisHistory).where(AiOcrAnalysisHistory.id.in_(stale_ids)))

    @classmethod
    async def create_zendesk_article(
        cls,
        session: AsyncSession,
        *,
        instance_id: int,
        brand_id: int,
        section_a_id: int,
        title: str,
        html_body: str,
        label_names: list[str],
        locale: str = "ko",
        draft: bool = False,
    ) -> dict:
        """
        /**
         * Zendesk Help Center에 아티클을 생성한다.
         * @returns {dict} article_id, html_url
         */
        """
        log = AiOcrLogCollector()
        log.info("Zendesk 아티클 생성 시작", f"인스턴스 ID: {instance_id}\n섹션 A ID: {section_a_id}")

        html_body = normalize_zendesk_html_body(html_body)

        instance = await session.get(Instance, instance_id)
        if instance is None:
            log.error("인스턴스 없음", f"instance_id={instance_id}")
            raise AiOcrServiceError("인스턴스를 찾을 수 없습니다.", log)

        brand = await session.scalar(
            select(Brand).where(Brand.id == brand_id, Brand.instance_id == instance_id)
        )
        if brand is None:
            log.error("브랜드 없음", f"brand_id={brand_id}")
            raise AiOcrServiceError("브랜드를 찾을 수 없습니다.", log)
        if not brand.has_help_center:
            log.error("Help Center 없음", f"brand={brand.name}")
            raise AiOcrServiceError("선택한 브랜드에 Help Center가 없습니다.", log)

        section = await session.scalar(
            select(Section).where(
                Section.instance_id == instance_id,
                Section.a_id == section_a_id,
            )
        )
        if section is None:
            log.error("섹션 없음", f"section_a_id={section_a_id}")
            raise AiOcrServiceError(
                "섹션을 찾을 수 없습니다. 인스턴스 데이터 수집 후 다시 선택하세요.",
                log,
            )

        base_url = f"https://{brand.subdomain}.zendesk.com/api/v2/help_center"
        post_url = f"{base_url}/sections/{section_a_id}/articles.json"
        article_payload: dict[str, object] = {
            "title": title.strip(),
            "body": html_body,
            "locale": locale.replace("_", "-").lower(),
            "draft": draft,
            "label_names": label_names,
        }
        request_json = {"article": article_payload, "notify_subscribers": False}

        log.info(
            "Zendesk API 요청",
            "\n".join(
                [
                    f"POST {post_url}",
                    f"인증: {instance.email} / token: ****",
                    "",
                    "요청 본문(JSON):",
                    AiOcrLogCollector.format_json(request_json),
                ]
            ),
        )

        try:
            response = await ZendeskClient.post_json(
                url=post_url,
                email=instance.email,
                api_token=instance.api_token,
                json=request_json,
            )
        except ZendeskClientError as error:
            log.error("Zendesk 응답 오류", str(error))
            raise AiOcrServiceError(f"Zendesk 아티클 생성 실패: {error}", log) from error

        article = response.get("article", {})
        article_id = article.get("id")
        html_url = article.get("html_url")
        if article_id is None:
            log.error(
                "Zendesk 응답 형식 오류",
                AiOcrLogCollector.format_json(response),
            )
            raise AiOcrServiceError("Zendesk 응답에 article.id가 없습니다.", log)

        log.success(
            "Zendesk 아티클 생성 완료",
            AiOcrLogCollector.format_json(
                {
                    "article_id": article_id,
                    "html_url": html_url,
                    "section": section.name,
                }
            ),
        )

        return {
            "article_id": int(article_id),
            "html_url": html_url,
            "section_a_id": section_a_id,
            "section_name": section.name,
            "logs": log.to_list(),
        }
