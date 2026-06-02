"""ai_ocr_settings provider model columns

Revision ID: 0014_ai_ocr_provider_models
Revises: 0013_ai_ocr_prompt_templates
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_ai_ocr_provider_models"
down_revision: Union[str, None] = "0013_ai_ocr_prompt_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_ocr_settings",
        sa.Column("gemini_model", sa.String(length=64), nullable=False, server_default="gemini-2.5-pro"),
    )
    op.add_column(
        "ai_ocr_settings",
        sa.Column("openai_model", sa.String(length=64), nullable=False, server_default="gpt-4o"),
    )


def downgrade() -> None:
    op.drop_column("ai_ocr_settings", "openai_model")
    op.drop_column("ai_ocr_settings", "gemini_model")
