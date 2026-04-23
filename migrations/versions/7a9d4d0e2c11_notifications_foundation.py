"""notifications foundation

Revision ID: 7a9d4d0e2c11
Revises: c8b3f4c1a2d9
Create Date: 2026-04-22 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a9d4d0e2c11"
down_revision = "c8b3f4c1a2d9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("lecon") as batch_op:
        batch_op.add_column(sa.Column("est_publie", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("date_publication", sa.DateTime(), nullable=True))

    op.execute("UPDATE lecon SET est_publie = 1 WHERE est_publie IS NULL")
    op.execute(
        "UPDATE lecon "
        "SET date_publication = COALESCE(date_creation, CURRENT_TIMESTAMP) "
        "WHERE est_publie = 1 AND date_publication IS NULL"
    )

    with op.batch_alter_table("lecon") as batch_op:
        batch_op.alter_column(
            "est_publie",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        )

    with op.batch_alter_table("xp_eleve") as batch_op:
        batch_op.alter_column(
            "derniere_activite",
            existing_type=sa.Date(),
            type_=sa.DateTime(),
            existing_nullable=True,
        )

    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("cta_url", sa.String(length=500), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("event_key", sa.String(length=200), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("pushed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "event_key", name="uq_notification_user_event_key"),
    )
    op.create_index("ix_notification_user_created_at", "notification", ["user_id", "created_at"], unique=False)
    op.create_index("ix_notification_user_is_read", "notification", ["user_id", "is_read"], unique=False)

    op.create_table(
        "notification_preference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("inbox_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", name="uq_notification_preference_user_type"),
    )

    op.create_table(
        "badge_definition",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "app_setting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "user_badge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("source_notification_id", sa.Integer(), nullable=True),
        sa.Column("date_earned", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["badge_id"], ["badge_definition.id"]),
        sa.ForeignKeyConstraint(["source_notification_id"], ["notification.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge_user_badge"),
    )
    op.create_index("ix_user_badge_user_date", "user_badge", ["user_id", "date_earned"], unique=False)


def downgrade():
    op.drop_index("ix_user_badge_user_date", table_name="user_badge")
    op.drop_table("user_badge")
    op.drop_table("app_setting")
    op.drop_table("badge_definition")
    op.drop_table("notification_preference")
    op.drop_index("ix_notification_user_is_read", table_name="notification")
    op.drop_index("ix_notification_user_created_at", table_name="notification")
    op.drop_table("notification")

    with op.batch_alter_table("xp_eleve") as batch_op:
        batch_op.alter_column(
            "derniere_activite",
            existing_type=sa.DateTime(),
            type_=sa.Date(),
            existing_nullable=True,
        )

    with op.batch_alter_table("lecon") as batch_op:
        batch_op.drop_column("date_publication")
        batch_op.drop_column("est_publie")
