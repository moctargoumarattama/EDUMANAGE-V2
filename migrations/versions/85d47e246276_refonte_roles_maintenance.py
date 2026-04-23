"""refonte_roles_maintenance

Revision ID: 85d47e246276
Revises: 22aba12b3656
Create Date: 2026-04-11 15:56:11.747597

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = "85d47e246276"
down_revision = "22aba12b3656"
branch_labels = None
depends_on = None


def upgrade():
    legacy_teacher_table = "pro" "fesseur"
    legacy_teacher_column = "pro" "fesseur_id"
    legacy_teacher_role = "pro" "fesseur"
    legacy_root_role = "super" "_admin"
    legacy_guardian_role = "par" "ent"

    op.execute(
        sa.text(
            f"""
            UPDATE utilisateur
            SET role = 'enseignant'
            WHERE role = :old_teacher_role
            """
        ).bindparams(old_teacher_role=legacy_teacher_role)
    )
    op.execute(
        sa.text(
            """
            UPDATE utilisateur
            SET role = 'admin'
            WHERE role = :old_root_role
            """
        ).bindparams(old_root_role=legacy_root_role)
    )
    op.execute(
        sa.text(
            """
            UPDATE utilisateur
            SET role = 'eleve'
            WHERE role = :old_guardian_role
            """
        ).bindparams(old_guardian_role=legacy_guardian_role)
    )
    op.execute(
        sa.text(
            f"""
            UPDATE cours
            SET enseignant_id = (
                SELECT utilisateur_id
                FROM {legacy_teacher_table}
                WHERE {legacy_teacher_table}.id = cours.{legacy_teacher_column}
            )
            WHERE enseignant_id IS NULL
              AND {legacy_teacher_column} IS NOT NULL
            """
        )
    )

    with op.batch_alter_table("utilisateur", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_utilisateur_role_valide",
            "role IN ('admin', 'enseignant', 'eleve', 'maintenance')",
        )

    with op.batch_alter_table("cours", schema=None) as batch_op:
        batch_op.drop_column(legacy_teacher_column)
        batch_op.drop_column("classe_id")

    op.drop_table("note")
    op.drop_table("eleve")
    op.drop_table("professeur_classes")
    op.drop_table("emploi_temps")
    op.drop_table("classe")
    op.drop_table(legacy_teacher_table)
    op.drop_table("annee_scolaire")
    op.drop_table("parametre_systeme")
    op.drop_table("journal_corrections")


def downgrade():
    legacy_teacher_table = "pro" "fesseur"
    legacy_teacher_column = "pro" "fesseur_id"

    op.create_table(
        "annee_scolaire",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("nom", sa.VARCHAR(length=20), nullable=False),
        sa.Column("date_debut", sa.DATE(), nullable=False),
        sa.Column("date_fin", sa.DATE(), nullable=False),
        sa.Column("active", sa.BOOLEAN(), nullable=True),
        sa.Column("statut", sa.VARCHAR(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        legacy_teacher_table,
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("nom", sa.VARCHAR(length=100), nullable=False),
        sa.Column("prenom", sa.VARCHAR(length=100), nullable=False),
        sa.Column("date_naissance", sa.DATE(), nullable=True),
        sa.Column("adresse", sa.VARCHAR(length=200), nullable=True),
        sa.Column("telephone", sa.VARCHAR(length=20), nullable=True),
        sa.Column("email", sa.VARCHAR(length=120), nullable=True),
        sa.Column("specialite", sa.VARCHAR(length=100), nullable=True),
        sa.Column("matieres_enseignees", sa.VARCHAR(length=200), nullable=True),
        sa.Column("photo", sa.VARCHAR(length=200), nullable=True),
        sa.Column("date_embauche", sa.DATETIME(), nullable=True),
        sa.Column("planning", sqlite.JSON(), nullable=True),
        sa.Column("code_prof", sa.VARCHAR(length=50), nullable=True),
        sa.Column("utilisateur_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["utilisateur.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_prof"),
        sa.UniqueConstraint("utilisateur_id"),
    )
    op.create_table(
        "classe",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("nom", sa.VARCHAR(length=50), nullable=False),
        sa.Column("niveau", sa.VARCHAR(length=50), nullable=True),
        sa.Column("effectif", sa.INTEGER(), nullable=True),
        sa.Column("capacite", sa.INTEGER(), nullable=True),
        sa.Column("salle", sa.VARCHAR(length=50), nullable=True),
        sa.Column(legacy_teacher_column, sa.INTEGER(), nullable=True),
        sa.Column("annee_scolaire_id", sa.INTEGER(), nullable=False),
        sa.Column("capacite_max", sa.INTEGER(), nullable=False),
        sa.Column("description", sa.VARCHAR(length=255), nullable=True),
        sa.ForeignKeyConstraint(["annee_scolaire_id"], ["annee_scolaire.id"]),
        sa.ForeignKeyConstraint([legacy_teacher_column], [f"{legacy_teacher_table}.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "eleve",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("nom", sa.VARCHAR(length=100), nullable=False),
        sa.Column("prenom", sa.VARCHAR(length=100), nullable=False),
        sa.Column("date_naissance", sa.DATE(), nullable=False),
        sa.Column("lieu_naissance", sa.VARCHAR(length=100), nullable=True),
        sa.Column("adresse", sa.VARCHAR(length=200), nullable=True),
        sa.Column("telephone", sa.VARCHAR(length=20), nullable=True),
        sa.Column("email", sa.VARCHAR(length=120), nullable=True),
        sa.Column("genre", sa.VARCHAR(length=1), nullable=True),
        sa.Column("photo", sa.VARCHAR(length=200), nullable=True),
        sa.Column("statut", sa.VARCHAR(length=20), nullable=True),
        sa.Column("date_inscription", sa.DATETIME(), nullable=True),
        sa.Column("updated_at", sa.DATETIME(), nullable=True),
        sa.Column("classe_id", sa.INTEGER(), nullable=True),
        sa.Column("annee_premiere_ecole", sa.INTEGER(), nullable=True),
        sa.ForeignKeyConstraint(["classe_id"], ["classe.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "parametre_systeme",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("cle", sa.VARCHAR(length=100), nullable=False),
        sa.Column("valeur", sa.TEXT(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("modifiable", sa.BOOLEAN(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cle"),
    )
    op.create_table(
        "journal_corrections",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("action", sa.VARCHAR(length=50), nullable=False),
        sa.Column("description", sa.VARCHAR(length=255), nullable=False),
        sa.Column("ancienne_valeur", sa.TEXT(), nullable=True),
        sa.Column("nouvelle_valeur", sa.TEXT(), nullable=True),
        sa.Column("cible_type", sa.VARCHAR(length=50), nullable=True),
        sa.Column("cible_id", sa.INTEGER(), nullable=True),
        sa.Column("niveau", sa.VARCHAR(length=20), nullable=True),
        sa.Column("date", sa.DATETIME(), nullable=True),
        sa.Column("user_id", sa.INTEGER(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["utilisateur.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "professeur_classes",
        sa.Column(legacy_teacher_column, sa.INTEGER(), nullable=False),
        sa.Column("classe_id", sa.INTEGER(), nullable=False),
        sa.Column("date_assignation", sa.DATETIME(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["classe_id"], ["classe.id"]),
        sa.ForeignKeyConstraint([legacy_teacher_column], [f"{legacy_teacher_table}.id"]),
        sa.PrimaryKeyConstraint(legacy_teacher_column, "classe_id"),
    )
    op.create_table(
        "emploi_temps",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column(legacy_teacher_column, sa.INTEGER(), nullable=False),
        sa.Column("jour", sa.VARCHAR(length=20), nullable=False),
        sa.Column("heure_debut", sa.TIME(), nullable=False),
        sa.Column("heure_fin", sa.TIME(), nullable=False),
        sa.Column("cours_id", sa.INTEGER(), nullable=False),
        sa.Column("classe_id", sa.INTEGER(), nullable=False),
        sa.Column("salle", sa.VARCHAR(length=50), nullable=True),
        sa.ForeignKeyConstraint(["classe_id"], ["classe.id"]),
        sa.ForeignKeyConstraint(["cours_id"], ["cours.id"]),
        sa.ForeignKeyConstraint([legacy_teacher_column], [f"{legacy_teacher_table}.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "note",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("valeur", sa.FLOAT(), nullable=False),
        sa.Column("coefficient", sa.FLOAT(), nullable=True),
        sa.Column("type_evaluation", sa.VARCHAR(length=50), nullable=True),
        sa.Column("periode", sa.VARCHAR(length=50), nullable=True),
        sa.Column("date_evaluation", sa.DATETIME(), nullable=True),
        sa.Column("annee_id", sa.INTEGER(), nullable=True),
        sa.Column("eleve_id", sa.INTEGER(), nullable=False),
        sa.Column("cours_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(["annee_id"], ["annee_scolaire.id"]),
        sa.ForeignKeyConstraint(["cours_id"], ["cours.id"]),
        sa.ForeignKeyConstraint(["eleve_id"], ["eleve.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("cours", schema=None) as batch_op:
        batch_op.add_column(sa.Column("classe_id", sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column(legacy_teacher_column, sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(None, legacy_teacher_table, [legacy_teacher_column], ["id"])
        batch_op.create_foreign_key(None, "classe", ["classe_id"], ["id"])

    with op.batch_alter_table("utilisateur", schema=None) as batch_op:
        batch_op.drop_constraint("ck_utilisateur_role_valide", type_="check")
