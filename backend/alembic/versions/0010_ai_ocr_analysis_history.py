"""ai_ocr_analysis_history table

Revision ID: 0010_ai_ocr_history
Revises: 0009_ai_ocr_gemini
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_ai_ocr_history"
down_revision: Union[str, None] = "0009_ai_ocr_gemini"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_ocr_analysis_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_filename", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("label_names", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("detected_product", sa.String(length=255), nullable=False),
        sa.Column("maintenance_cycle", sa.String(length=100), nullable=True),
        sa.Column("body_preview_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_ocr_analysis_history_created_at",
        "ai_ocr_analysis_history",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_ocr_analysis_history_created_at", table_name="ai_ocr_analysis_history")
    op.drop_table("ai_ocr_analysis_history")
