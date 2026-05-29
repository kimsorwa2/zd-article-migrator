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
    source_entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    migrated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
