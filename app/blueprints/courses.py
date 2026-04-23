import os

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename

from app import db
from app.forms import CourseForm
from app.models import Cours, Inscription, Vocabulaire
from app.storage import delete_asset_file
from app.translation import resolve_vocab_popup_payload
from app.utils import CEFR_LEVELS, get_ordered_lessons, user_can_manage_course


courses_bp = Blueprint("courses", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_ROLES = {"admin", "enseignant", "eleve"}


def _ensure_learning_portal_access():
    if current_user.role not in ALLOWED_ROLES:
        abort(403)


def _ensure_teacher_or_admin():
    if current_user.role not in {"enseignant", "admin"}:
        abort(403)


def _save_course_image(cours, file_storage):
    if not file_storage or not file_storage.filename:
        return cours.image_url

    extension = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Le format d'image doit etre png, jpg, jpeg, gif ou webp.")

    safe_name = secure_filename(file_storage.filename)
    filename = f"cours_{cours.id}_{safe_name}"
    destination = os.path.join(current_app.config["COURSE_IMAGE_FOLDER"], filename)
    file_storage.save(destination)
    return f"uploads/courses/{filename}"


def _visible_courses_query():
    query = Cours.query.options(
        joinedload(Cours.enseignant_utilisateur),
        selectinload(Cours.lecons),
    )

    if current_user.role == "admin":
        return query

    if current_user.role == "enseignant":
        return query.filter(Cours.enseignant_id == current_user.id)

    return query.filter(Cours.est_publie.is_(True))
@courses_bp.route("/")
@login_required
def liste():
    _ensure_learning_portal_access()
    cours = _visible_courses_query().order_by(Cours.date_creation.desc(), Cours.id.desc()).all()
    enrollment_map = {}
    if current_user.role == "eleve":
        enrollment_map = {
            inscription.cours_id: inscription
            for inscription in Inscription.query.filter_by(
                eleve_id=current_user.id,
                est_active=True,
            ).all()
        }

    inscription_counts = dict(
        db.session.query(Inscription.cours_id, func.count(Inscription.id))
        .filter(Inscription.est_active.is_(True))
        .group_by(Inscription.cours_id)
        .all()
    )

    course_cards = []
    for cours_item in cours:
        is_enrolled = cours_item.id in enrollment_map
        lesson_count = len(get_ordered_lessons(cours_item, published_only=current_user.role == "eleve"))
        course_cards.append(
            {
                "cours": cours_item,
                "is_enrolled": is_enrolled,
                "progression": cours_item.get_progression_eleve(current_user.id) if is_enrolled else None,
                "can_manage": user_can_manage_course(cours_item),
                "inscriptions_count": inscription_counts.get(cours_item.id, 0),
                "lesson_count": lesson_count,
            }
        )

    if current_user.role == "eleve":
        course_cards.sort(
            key=lambda item: (
                not item["is_enrolled"],
                -(item["cours"].date_creation.timestamp() if item["cours"].date_creation else 0),
            )
        )
    else:
        course_cards.sort(
            key=lambda item: (
                not item["can_manage"],
                item["cours"].est_publie,
                -(item["cours"].date_creation.timestamp() if item["cours"].date_creation else 0),
            )
        )

    summary = {
        "courses": len(course_cards),
        "lessons": sum(
            len(get_ordered_lessons(item["cours"], published_only=current_user.role == "eleve"))
            for item in course_cards
        ),
    }

    return render_template(
        "courses/liste.html",
        cours_list=cours,
        course_cards=course_cards,
        niveaux=CEFR_LEVELS,
        summary=summary,
    )


@courses_bp.route("/<int:cours_id>")
@login_required
def detail(cours_id):
    _ensure_learning_portal_access()
    cours = (
        Cours.query.options(
            joinedload(Cours.enseignant_utilisateur),
            selectinload(Cours.lecons),
        )
        .filter_by(id=cours_id)
        .first_or_404()
    )

    can_manage = user_can_manage_course(cours)
    is_student = current_user.role == "eleve"

    if is_student and not cours.est_publie:
        abort(403)

    if current_user.role == "enseignant" and not can_manage and not cours.est_publie:
        abort(403)

    inscription = None
    progression = None
    progressions_map = {}
    can_open_lessons = current_user.role == "admin" or can_manage
    visible_lessons = get_ordered_lessons(cours, published_only=is_student)

    if is_student:
        inscription = Inscription.query.filter_by(
            eleve_id=current_user.id,
            cours_id=cours.id,
            est_active=True,
        ).first()
        can_open_lessons = inscription is not None
        if inscription:
            progression = cours.get_progression_eleve(current_user.id)
            for progression_item in current_user.progressions_lecons:
                if progression_item.lecon_id in [lecon.id for lecon in visible_lessons]:
                    progressions_map[progression_item.lecon_id] = progression_item
        else:
            progression = 0

    return render_template(
        "courses/detail.html",
        cours=cours,
        inscription=inscription,
        progression=progression,
        progressions_map=progressions_map,
        can_manage=can_manage,
        can_open_lessons=can_open_lessons,
        visible_lessons=visible_lessons,
    )


@courses_bp.route("/nouveau", methods=["GET", "POST"])
@login_required
def nouveau():
    _ensure_teacher_or_admin()
    form = CourseForm()

    if form.validate_on_submit():
        cours = Cours(
            nom=form.titre.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            niveau=form.niveau.data,
            est_publie=False,
            enseignant_id=current_user.id,
        )

        db.session.add(cours)
        db.session.flush()

        try:
            cours.image_url = _save_course_image(cours, form.image.data)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return render_template("courses/form.html", form=form, cours=None, is_edit=False)

        db.session.commit()
        flash(_("Cours cree avec succes. Il reste en brouillon jusqu'a publication."), "success")
        return redirect(url_for("courses.detail", cours_id=cours.id))

    return render_template("courses/form.html", form=form, cours=None, is_edit=False)


@courses_bp.route("/<int:cours_id>/modifier", methods=["GET", "POST"])
@login_required
def modifier(cours_id):
    _ensure_teacher_or_admin()
    cours = Cours.query.filter_by(id=cours_id).first_or_404()
    if not user_can_manage_course(cours):
        abort(403)

    form = CourseForm()
    if request.method == "GET":
        form.titre.data = cours.nom
        form.description.data = cours.description
        form.niveau.data = cours.niveau
        form.est_publie.data = cours.est_publie

    if form.validate_on_submit():
        cours.nom = form.titre.data.strip()
        cours.description = form.description.data.strip() if form.description.data else None
        cours.niveau = form.niveau.data
        cours.est_publie = form.est_publie.data

        if form.image.data and form.image.data.filename:
            try:
                new_image = _save_course_image(cours, form.image.data)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("courses/form.html", form=form, cours=cours, is_edit=True)

            delete_asset_file(cours.image_url, "uploads/courses/")
            cours.image_url = new_image

        db.session.commit()
        flash(_("Cours mis a jour avec succes."), "success")
        return redirect(url_for("courses.detail", cours_id=cours.id))

    return render_template("courses/form.html", form=form, cours=cours, is_edit=True)


@courses_bp.route("/<int:cours_id>/supprimer", methods=["POST"])
@login_required
def supprimer(cours_id):
    _ensure_teacher_or_admin()
    cours = Cours.query.filter_by(id=cours_id).first_or_404()
    if not user_can_manage_course(cours):
        abort(403)

    delete_asset_file(cours.image_url, "uploads/courses/")
    db.session.delete(cours)
    db.session.commit()
    flash(_("Cours supprime avec succes."), "success")
    return redirect(url_for("courses.liste"))


@courses_bp.route("/<int:cours_id>/inscrire", methods=["POST"])
@login_required
def inscrire(cours_id):
    if current_user.role != "eleve":
        abort(403)

    cours = Cours.query.filter_by(id=cours_id).first_or_404()
    if not cours.est_publie:
        abort(403)

    inscription = Inscription.query.filter_by(
        eleve_id=current_user.id,
        cours_id=cours.id,
    ).first()

    if inscription and inscription.est_active:
        flash(_("Vous etes deja inscrit a ce cours."), "info")
        return redirect(url_for("courses.detail", cours_id=cours.id))

    if inscription:
        inscription.est_active = True
    else:
        inscription = Inscription(eleve_id=current_user.id, cours_id=cours.id, est_active=True)
        db.session.add(inscription)

    db.session.commit()
    flash(_("Inscription au cours enregistree avec succes."), "success")
    return redirect(url_for("courses.detail", cours_id=cours.id))


@courses_bp.route("/api/vocabulaire/<path:mot_arabe>")
@login_required
def api_vocabulaire(mot_arabe):
    _ensure_learning_portal_access()
    payload = resolve_vocab_popup_payload((mot_arabe or "").strip())
    payload["traduction"] = payload["traduction"] or _("Non disponible")
    return jsonify(payload)
