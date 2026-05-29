"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-28 16:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subdomain", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("api_token", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("a_brand_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subdomain", sa.String(length=255), nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_id", "a_brand_id", name="uq_brands_instance_a_brand_id"),
    )
    op.create_index("ix_brands_instance_id", "brands", ["instance_id"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("a_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=20), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("a_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("a_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_id", "a_id", name="uq_categories_instance_a_id"),
    )
    op.create_index("ix_categories_instance_brand", "categories", ["instance_id", "brand_id"], unique=False)

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("a_id", sa.Integer(), nullable=False),
        sa.Column("a_category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=20), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("a_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("a_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_id", "a_id", name="uq_sections_instance_a_id"),
    )
    op.create_index("ix_sections_instance_category", "sections", ["instance_id", "a_category_id"], unique=False)

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("a_id", sa.Integer(), nullable=False),
        sa.Column("a_section_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("locale", sa.String(length=20), nullable=True),
        sa.Column("label_names", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("draft", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("a_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("a_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_id", "a_id", name="uq_articles_instance_a_id"),
    )
    op.create_index("ix_articles_instance_section", "articles", ["instance_id", "a_section_id"], unique=False)

    op.create_table(
        "migration_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_instance_id", sa.Integer(), nullable=False),
        sa.Column("target_instance_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("source_entity_id", sa.Integer(), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_instance_id",
            "target_instance_id",
            "entity_type",
            "source_entity_id",
            name="uq_migration_mappings_source_target_entity",
        ),
    )
    op.create_index("ix_migration_mappings_status", "migration_mappings", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_migration_mappings_status", table_name="migration_mappings")
    op.drop_table("migration_mappings")

    op.drop_index("ix_articles_instance_section", table_name="articles")
    op.drop_table("articles")

    op.drop_index("ix_sections_instance_category", table_name="sections")
    op.drop_table("sections")

    op.drop_index("ix_categories_instance_brand", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_brands_instance_id", table_name="brands")
    op.drop_table("brands")

    op.drop_table("instances")
