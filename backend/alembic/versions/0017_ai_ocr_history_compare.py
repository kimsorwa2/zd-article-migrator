"""ai_ocr_analysis_history compare / debug columns

Revision ID: 0017_ai_ocr_history_compare
Revises: 0016_ai_ocr_history_metrics
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_ai_ocr_history_compare"
down_revision: Union[str, None] = "0016_ai_ocr_history_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_ocr_analysis_history", sa.Column("raw_response_text", sa.Text(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("parse_error_message", sa.Text(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("used_system_prompt", sa.Text(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("used_user_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_ocr_analysis_history", "used_user_prompt")
    op.drop_column("ai_ocr_analysis_history", "used_system_prompt")
    op.drop_column("ai_ocr_analysis_history", "parse_error_message")
    op.drop_column("ai_ocr_analysis_history", "raw_response_text")
