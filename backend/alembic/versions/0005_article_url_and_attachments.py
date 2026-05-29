"""add article html_url and has_attachments

Revision ID: 0005_article_url_and_attachments
Revises: 0004_brand_help_center_flag
Create Date: 2026-05-29 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_article_url_and_attachments"
down_revision: Union[str, None] = "0004_brand_help_center_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("html_url", sa.String(length=1000), nullable=True))
    op.add_column(
        "articles",
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("articles", "has_attachments")
    op.drop_column("articles", "html_url")
