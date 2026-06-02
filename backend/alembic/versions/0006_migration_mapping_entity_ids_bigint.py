"""migration_mappings entity id columns to bigint

Revision ID: 0006_mapping_entity_bigint
Revises: 0005_article_url_attachments
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_mapping_entity_bigint"
down_revision: Union[str, None] = "0005_article_url_and_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "migration_mappings",
        "source_entity_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "migration_mappings",
        "target_entity_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "migration_mappings",
        "target_entity_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "migration_mappings",
        "source_entity_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        nullable=False,
    )
