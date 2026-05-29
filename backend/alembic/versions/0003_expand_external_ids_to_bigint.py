"""expand external ids to bigint

Revision ID: 0003_external_ids_bigint
Revises: 0002_instance_name_nullable
Create Date: 2026-05-28 18:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_external_ids_bigint"
down_revision: Union[str, None] = "0002_instance_name_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("brands", "a_brand_id", existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)
    op.alter_column("categories", "a_id", existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)
    op.alter_column("sections", "a_id", existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)
    op.alter_column("sections", "a_category_id", existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)
    op.alter_column("articles", "a_id", existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)
    op.alter_column("articles", "a_section_id", existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)


def downgrade() -> None:
    op.alter_column("articles", "a_section_id", existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)
    op.alter_column("articles", "a_id", existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)
    op.alter_column("sections", "a_category_id", existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)
    op.alter_column("sections", "a_id", existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)
    op.alter_column("categories", "a_id", existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)
    op.alter_column("brands", "a_brand_id", existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)
