"""rename ai_ocr openai columns to gemini

Revision ID: 0009_ai_ocr_gemini
Revises: 0008_section_parent_id
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0009_ai_ocr_gemini"
down_revision: Union[str, None] = "0008_section_parent_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("ai_ocr_settings", "openai_account", new_column_name="gemini_account")
    op.alter_column("ai_ocr_settings", "openai_api_key", new_column_name="gemini_api_key")


def downgrade() -> None:
    op.alter_column("ai_ocr_settings", "gemini_account", new_column_name="openai_account")
    op.alter_column("ai_ocr_settings", "gemini_api_key", new_column_name="openai_api_key")
