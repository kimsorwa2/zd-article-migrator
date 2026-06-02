"""ai_ocr_analysis_history label columns

Revision ID: 0015_ai_ocr_history_label
Revises: 0014_ai_ocr_provider_models
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015_ai_ocr_history_label"
down_revision: Union[str, None] = "0014_ai_ocr_provider_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_ocr_analysis_history", sa.Column("ai_model", sa.String(length=64), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("display_label", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_ocr_analysis_history", "display_label")
    op.drop_column("ai_ocr_analysis_history", "ai_model")
