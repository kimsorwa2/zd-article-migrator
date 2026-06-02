"""ai_ocr_analysis_history preprocess columns

Revision ID: 0021_ai_ocr_preprocess_flag
Revises: 0020_ai_ocr_connection_prompt
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_ai_ocr_preprocess_flag"
down_revision: Union[str, None] = "0020_ai_ocr_connection_prompt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_ocr_analysis_history", sa.Column("preprocessed", sa.Boolean(), nullable=True))
    op.add_column(
        "ai_ocr_analysis_history",
        sa.Column("processed_image_size_kb", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_ocr_analysis_history", "processed_image_size_kb")
    op.drop_column("ai_ocr_analysis_history", "preprocessed")
