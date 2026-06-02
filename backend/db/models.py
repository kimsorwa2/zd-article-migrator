from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Instance(Base):
    __tablename__ = "instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subdomain: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    api_token: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("instance_id", "a_brand_id", name="uq_brands_instance_a_brand_id"),
        Index("ix_brands_instance_id", "instance_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=False)
    a_brand_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(255), nullable=False)
    has_help_center: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("instance_id", "a_id", name="uq_categories_instance_a_id"),
        Index("ix_categories_instance_brand", "instance_id", "brand_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    a_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str | None] = mapped_column(String(20), nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    a_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    a_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("instance_id", "a_id", name="uq_sections_instance_a_id"),
        Index("ix_sections_instance_category", "instance_id", "a_category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=False)
    a_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    a_category_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    a_parent_section_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str | None] = mapped_column(String(20), nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    a_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    a_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("instance_id", "a_id", name="uq_articles_instance_a_id"),
        Index("ix_articles_instance_section", "instance_id", "a_section_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=False)
    a_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    a_section_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str | None] = mapped_column(String(20), nullable=True)
    label_names: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    html_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    a_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    a_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiOcrConnection(Base):
    """
    AI Vision OCR 연동 프로필(동일 제공자라도 계정·키별로 여러 개 등록 가능).
    """

    __tablename__ = "ai_ocr_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Bedrock 단기 API 키는 1000자 이상일 수 있음
    api_key: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    api_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    aws_region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt_template_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ai_ocr_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AiOcrSetting(Base):
    """
    AI-OCR 전역 설정(단일 행 id=1). 활성 연동·프롬프트 및 레거시 제공자별 필드.
    """

    __tablename__ = "ai_ocr_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_provider: Mapped[str] = mapped_column(String(32), nullable=False, server_default="gemini")
    active_connection_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ai_ocr_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_prompt_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ai_ocr_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    gemini_account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gemini_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    gemini_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="gemini-2.5-pro")
    openai_account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    openai_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    openai_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="gpt-4o")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AiOcrPromptTemplate(Base):
    """
    저장된 OCR Vision 프롬프트 템플릿(여러 개 등록·선택).
    """

    __tablename__ = "ai_ocr_prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AiOcrAnalysisHistory(Base):
    """
    AI-OCR 분석 결과 이력(Gemini API 재호출 없이 미리보기 복원용).
    """

    __tablename__ = "ai_ocr_analysis_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    label_names: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    detected_product: Mapped[str] = mapped_column(String(255), nullable=False)
    maintenance_cycle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body_preview_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thinking_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parse_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    experiment_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class MigrationMapping(Base):
    __tablename__ = "migration_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_instance_id",
            "target_instance_id",
            "entity_type",
            "source_entity_id",
            name="uq_migration_mappings_source_target_entity",
        ),
        Index("ix_migration_mappings_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_instance_id: Mapped[int] = mapped_column(
        ForeignKey("instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_instance_id: Mapped[int] = mapped_column(
        ForeignKey("instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    migrated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
