"""ai_ocr multi provider settings

Revision ID: 0011_ai_ocr_providers
Revises: 0010_ai_ocr_history
Create Date: 2026-06-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_ai_ocr_providers"
down_revision: Union[str, None] = "0010_ai_ocr_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_ocr_settings",
        sa.Column("active_provider", sa.String(length=32), nullable=False, server_default="gemini"),
    )
    op.add_column("ai_ocr_settings", sa.Column("openai_account", sa.String(length=255), nullable=True))
    op.add_column("ai_ocr_settings", sa.Column("openai_api_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_ocr_settings", "openai_api_key")
    op.drop_column("ai_ocr_settings", "openai_account")
    op.drop_column("ai_ocr_settings", "active_provider")
