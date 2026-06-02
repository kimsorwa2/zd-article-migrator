"""sections parent_section_id column

Revision ID: 0008_section_parent_id
Revises: 0007_ai_ocr_settings
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_section_parent_id"
down_revision: Union[str, None] = "0007_ai_ocr_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sections", sa.Column("a_parent_section_id", sa.BigInteger(), nullable=True))
    op.create_index(
        "ix_sections_instance_parent",
        "sections",
        ["instance_id", "a_parent_section_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sections_instance_parent", table_name="sections")
    op.drop_column("sections", "a_parent_section_id")
