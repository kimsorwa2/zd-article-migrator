"""ai_ocr_analysis_history metrics columns

Revision ID: 0016_ai_ocr_history_metrics
Revises: 0015_ai_ocr_history_label
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_ai_ocr_history_metrics"
down_revision: Union[str, None] = "0015_ai_ocr_history_label"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_ocr_analysis_history", sa.Column("prompt_template_id", sa.Integer(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("image_size_kb", sa.Integer(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("thinking_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("finish_reason", sa.String(length=32), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("parse_success", sa.Boolean(), nullable=True))
    op.add_column("ai_ocr_analysis_history", sa.Column("experiment_tag", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_ocr_analysis_history", "experiment_tag")
    op.drop_column("ai_ocr_analysis_history", "parse_success")
    op.drop_column("ai_ocr_analysis_history", "finish_reason")
    op.drop_column("ai_ocr_analysis_history", "thinking_tokens")
    op.drop_column("ai_ocr_analysis_history", "output_tokens")
    op.drop_column("ai_ocr_analysis_history", "input_tokens")
    op.drop_column("ai_ocr_analysis_history", "latency_ms")
    op.drop_column("ai_ocr_analysis_history", "image_size_kb")
    op.drop_column("ai_ocr_analysis_history", "prompt_template_id")
