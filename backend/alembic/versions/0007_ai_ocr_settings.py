"""ai_ocr_settings table

Revision ID: 0007_ai_ocr_settings
Revises: 0006_mapping_entity_bigint
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_ai_ocr_settings"
down_revision: Union[str, None] = "0006_mapping_entity_bigint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_ocr_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("openai_account", sa.String(length=255), nullable=True),
        sa.Column("openai_api_key", sa.String(length=512), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ai_ocr_settings")
