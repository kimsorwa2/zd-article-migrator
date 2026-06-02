"""ai_ocr custom prompts

Revision ID: 0012_ai_ocr_prompts
Revises: 0011_ai_ocr_providers
Create Date: 2026-06-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_ai_ocr_prompts"
down_revision: Union[str, None] = "0011_ai_ocr_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_ocr_settings", sa.Column("system_prompt", sa.Text(), nullable=True))
    op.add_column("ai_ocr_settings", sa.Column("user_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_ocr_settings", "user_prompt")
    op.drop_column("ai_ocr_settings", "system_prompt")
