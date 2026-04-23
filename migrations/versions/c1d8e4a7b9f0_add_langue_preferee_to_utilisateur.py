"""add_langue_preferee_to_utilisateur

Revision ID: c1d8e4a7b9f0
Revises: 7a9d4d0e2c11
Create Date: 2026-04-23 00:48:30.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d8e4a7b9f0"
down_revision = "7a9d4d0e2c11"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("utilisateur", schema=None) as batch_op:
        batch_op.add_column(sa.Column("langue_preferee", sa.String(length=5), nullable=True))


def downgrade():
    with op.batch_alter_table("utilisateur", schema=None) as batch_op:
        batch_op.drop_column("langue_preferee")
