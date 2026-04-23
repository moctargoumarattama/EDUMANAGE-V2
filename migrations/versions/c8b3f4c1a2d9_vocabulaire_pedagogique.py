"""vocabulaire pedagogique

Revision ID: c8b3f4c1a2d9
Revises: 4cae61fd7fae
Create Date: 2026-04-17 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8b3f4c1a2d9"
down_revision = "4cae61fd7fae"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vocabulaire", sa.Column("niveau_cefr", sa.String(length=5), nullable=True))
    op.add_column("vocabulaire", sa.Column("theme", sa.String(length=100), nullable=True))
    op.add_column(
        "vocabulaire",
        sa.Column("est_pedagogique", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade():
    with op.batch_alter_table("vocabulaire") as batch_op:
        batch_op.drop_column("est_pedagogique")
        batch_op.drop_column("theme")
        batch_op.drop_column("niveau_cefr")
