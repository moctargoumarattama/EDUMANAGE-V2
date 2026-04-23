import json
import os
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename

from app import db
from app.forms import LessonForm
from app.models import Cours, Lecon, ProgressionLecon, Question, ReponseEleve, XPEleve
from app.notification_center import (
    award_badges_for_user,
    create_exercise_corrected_notification,
    dispatch_lesson_published_notifications,
    should_notify_lesson_publication,
)
from app.storage import delete_asset_file
from app.utils import (
    extract_youtube_embed,
    extract_youtube_watch_url,
    get_next_lesson_id,
    is_student_enrolled,
    normalize_arabic_answer,
    serialize_lesson_questions,
    speaking_matches_expected,
    user_can_manage_course,
)


lessons_bp = Blueprint("lessons", __name__)


def _ensure_teacher_or_admin():
    if current_user.role not in {"enseignant", "admin"}:
        abort(403)


def _save_pdf_upload(lecon, file_storage):
    if not file_storage or not file_storage.filename:
        return lecon.pdf_url

    filename = secure_filename(file_storage.filename)
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Le fichier doit etre un PDF.")

    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    final_name = f"lecon_{lecon.id}_{filename}"
    destination = os.path.join(current_app.config["UPLOAD_FOLDER"], final_name)
    file_storage.save(destination)
    return f"uploads/pdfs/{final_name}"


def _save_audio_upload(lecon, file_storage):
    if not file_storage or not file_storage.filename:
        return lecon.audio_url

    filename = secure_filename(file_storage.filename)
    os.makedirs(current_app.config["AUDIO_FOLDER"], exist_ok=True)
    final_name = f"lecon_{lecon.id}_{filename}"
    destination = os.path.join(current_app.config["AUDIO_FOLDER"], final_name)
    file_storage.save(destination)
    return f"uploads/audios/{final_name}"


def _get_lesson_with_content(lecon_id):
    return (
        Lecon.query.options(
            joinedload(Lecon.cours).joinedload(Cours.enseignant_utilisateur),
            joinedload(Lecon.cours).selectinload(Cours.lecons),
            selectinload(Lecon.questions).selectinload(Question.choix),
        )
        .filter_by(id=lecon_id)
        .first_or_404()
    )


def _ensure_student_can_access_lesson(lecon):
    cours = lecon.cours
    if current_user.role != "eleve":
        abort(403)
    if not cours.est_publie or not lecon.est_publie or not is_student_enrolled(cours, current_user.id):
        flash(_("Vous devez etre inscrit a ce cours pour ouvrir cette lecon."), "warning")
        return redirect(url_for("courses.detail", cours_id=cours.id))
    return None


def _mark_lesson_viewed(lecon):
    progression = ProgressionLecon.query.filter_by(
        eleve_id=current_user.id,
        lecon_id=lecon.id,
    ).first()
    if progression is None:
        progression = ProgressionLecon(
            eleve_id=current_user.id,
            lecon_id=lecon.id,
            vue=True,
            date_vue=datetime.utcnow(),
        )
        db.session.add(progression)
    else:
        progression.vue = True
        progression.date_vue = datetime.utcnow()
    db.session.commit()
    return progression


@lessons_bp.route("/<int:lecon_id>")
@login_required
def detail(lecon_id):
    lecon = _get_lesson_with_content(lecon_id)
    cours = lecon.cours
    can_manage = user_can_manage_course(cours)

    if current_user.role == "eleve":
        return redirect(url_for("lessons.start", lecon_id=lecon.id))

    if current_user.role not in {"enseignant", "admin"}:
        abort(403)
    if not can_manage and not cours.est_publie:
        abort(403)

    video_embed_url = extract_youtube_embed(lecon.video_url)
    video_autoplay_url = f"{video_embed_url}&autoplay=1" if video_embed_url else None
    video_watch_url = extract_youtube_watch_url(lecon.video_url)
    return render_template(
        "lecons/detail.html",
        lecon=lecon,
        cours=cours,
        progression=None,
        quiz_resultats=None,
        video_embed_url=video_embed_url,
        video_autoplay_url=video_autoplay_url,
        video_watch_url=video_watch_url,
        can_manage=can_manage,
        peut_repondre=False,
    )


@lessons_bp.route("/<int:lecon_id>/start")
@login_required
def start(lecon_id):
    lecon = _get_lesson_with_content(lecon_id)
    access_response = _ensure_student_can_access_lesson(lecon)
    if access_response is not None:
        return access_response

    _mark_lesson_viewed(lecon)
    questions_json = json.dumps(serialize_lesson_questions(lecon), ensure_ascii=False)
    xp = XPEleve.get_or_create(current_user.id)
    return render_template(
        "lecons/lesson_flow.html",
        lecon=lecon,
        cours=lecon.cours,
        questions_json=questions_json,
        current_xp=xp.points or 0,
    )


@lessons_bp.route("/<int:lecon_id>/complete", methods=["POST"])
@login_required
def complete(lecon_id):
    lecon = _get_lesson_with_content(lecon_id)
    access_response = _ensure_student_can_access_lesson(lecon)
    if access_response is not None:
        return jsonify({"error": "Acces refuse a cette lecon."}), 403

    payload = request.get_json(silent=True) or {}
    submitted_results = payload.get("resultats") or []
    submitted_by_question = {
        item.get("question_id"): item for item in submitted_results if item.get("question_id") is not None
    }

    if len(submitted_by_question) < len(lecon.questions):
        return jsonify({"error": "Toutes les questions doivent etre completees."}), 400

    progression = ProgressionLecon.query.filter_by(
        eleve_id=current_user.id,
        lecon_id=lecon.id,
    ).first()
    if progression is None:
        progression = ProgressionLecon(
            eleve_id=current_user.id,
            lecon_id=lecon.id,
            vue=True,
            date_vue=datetime.utcnow(),
        )
        db.session.add(progression)
        db.session.flush()

    was_completed = progression.score_quiz is not None
    nb_correct = 0
    nb_total = len(lecon.questions)

    for question in lecon.questions:
        submitted = submitted_by_question.get(question.id)
        if not submitted:
            return jsonify({"error": _("Une question est manquante dans la reponse.")}), 400

        choix = None
        choix_id = submitted.get("choix_id")
        reponse_saisie = (submitted.get("reponse_saisie") or "").strip()
        est_correct = False

        question_type = question.type_exercice or "qcm"

        if question_type == "dictee":
            bonne_reponse = (question.bonne_reponse_texte or "").strip()
            if not bonne_reponse:
                return jsonify({"error": _("La dictee n'est pas configuree correctement.")}), 400
            if not reponse_saisie:
                return jsonify({"error": _("Toutes les questions doivent etre completees.")}), 400
            est_correct = normalize_arabic_answer(reponse_saisie) == normalize_arabic_answer(bonne_reponse)
        elif question_type == "speaking":
            bonne_reponse = (question.bonne_reponse_texte or "").strip()
            if not bonne_reponse:
                return jsonify({"error": _("La question orale n'est pas configuree correctement.")}), 400
            if not reponse_saisie or reponse_saisie == "skipped":
                est_correct = False
            else:
                est_correct = speaking_matches_expected(reponse_saisie, bonne_reponse)
        else:
            try:
                choix_id = int(choix_id)
            except (TypeError, ValueError):
                return jsonify({"error": _("Un choix selectionne est invalide.")}), 400

            choix = next((item for item in question.choix if item.id == choix_id), None)
            if choix is None:
                return jsonify({"error": _("Le choix selectionne ne correspond pas a la question.")}), 400
            est_correct = bool(choix.est_correct)

        reponse = ReponseEleve.query.filter_by(
            eleve_id=current_user.id,
            question_id=question.id,
        ).first()
        if reponse is None:
            reponse = ReponseEleve(
                eleve_id=current_user.id,
                question_id=question.id,
                choix_id=choix.id if choix else None,
                reponse_saisie=reponse_saisie or None,
                est_correct=est_correct,
                date_reponse=datetime.utcnow(),
            )
            db.session.add(reponse)
        else:
            reponse.choix_id = choix.id if choix else None
            reponse.reponse_saisie = reponse_saisie or None
            reponse.est_correct = est_correct
            reponse.date_reponse = datetime.utcnow()

        if est_correct:
            nb_correct += 1

    score = (nb_correct / nb_total) if nb_total else 0
    progression.vue = True
    progression.date_vue = datetime.utcnow()
    progression.score_quiz = score
    db.session.commit()

    xp = XPEleve.get_or_create(current_user.id)
    xp_gagne = 0
    if not was_completed:
        xp_gagne = (lecon.points_recompense or 10) + (nb_correct * 5)
        xp.total_lecons_terminees = (xp.total_lecons_terminees or 0) + 1
        db.session.commit()
        xp.ajouter_points(xp_gagne)

    target_app = current_app._get_current_object()
    create_exercise_corrected_notification(
        current_user.id,
        lecon,
        score_percent=round(score * 100),
        nb_correct=nb_correct,
        nb_total=nb_total,
        app=target_app,
    )
    award_badges_for_user(current_user.id, app=target_app)

    return jsonify(
        {
            "xp_gagne": xp_gagne,
            "total_xp": xp.points or 0,
            "streak": xp.streak_jours or 0,
            "total_lecons_terminees": xp.total_lecons_terminees or 0,
            "next_lecon_id": get_next_lesson_id(lecon.cours, lecon.id, published_only=True),
            "score": round(score, 2),
            "nb_correct": nb_correct,
            "nb_total": nb_total,
        }
    )


@lessons_bp.route("/cours/<int:cours_id>/nouvelle", methods=["GET", "POST"])
@login_required
def nouvelle(cours_id):
    _ensure_teacher_or_admin()
    cours = Cours.query.filter_by(id=cours_id).first_or_404()
    if not user_can_manage_course(cours):
        abort(403)

    form = LessonForm()
    if form.validate_on_submit():
        lecon = Lecon(
            cours_id=cours.id,
            titre=form.titre.data.strip(),
            ordre=form.ordre.data,
            contenu_texte=form.contenu_texte.data.strip() if form.contenu_texte.data else None,
            video_url=form.video_url.data.strip() if form.video_url.data else None,
            duree_minutes=form.duree_minutes.data,
            est_publie=bool(form.est_publie.data),
            date_publication=datetime.utcnow() if form.est_publie.data else None,
        )
        db.session.add(lecon)
        db.session.flush()

        try:
            lecon.pdf_url = _save_pdf_upload(lecon, form.pdf.data)
            lecon.audio_url = _save_audio_upload(lecon, form.audio.data)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return render_template("lecons/form.html", form=form, cours=cours, lecon=None, is_edit=False)

        db.session.commit()
        if lecon.est_publie:
            dispatch_lesson_published_notifications(lecon, app=current_app._get_current_object())
        flash(_("Lecon creee avec succes."), "success")
        return redirect(url_for("lessons.detail", lecon_id=lecon.id))

    return render_template("lecons/form.html", form=form, cours=cours, lecon=None, is_edit=False)


@lessons_bp.route("/<int:lecon_id>/modifier", methods=["GET", "POST"])
@login_required
def modifier(lecon_id):
    _ensure_teacher_or_admin()
    lecon = Lecon.query.filter_by(id=lecon_id).first_or_404()
    if not user_can_manage_course(lecon.cours):
        abort(403)

    form = LessonForm()
    if request.method == "GET":
        form.titre.data = lecon.titre
        form.ordre.data = lecon.ordre
        form.contenu_texte.data = lecon.contenu_texte
        form.video_url.data = lecon.video_url
        form.duree_minutes.data = lecon.duree_minutes
        form.est_publie.data = lecon.est_publie

    if form.validate_on_submit():
        previous_is_published = bool(lecon.est_publie)
        lecon.titre = form.titre.data.strip()
        lecon.ordre = form.ordre.data
        lecon.contenu_texte = form.contenu_texte.data.strip() if form.contenu_texte.data else None
        lecon.video_url = form.video_url.data.strip() if form.video_url.data else None
        lecon.duree_minutes = form.duree_minutes.data
        lecon.est_publie = bool(form.est_publie.data)
        if lecon.est_publie and not lecon.date_publication:
            lecon.date_publication = datetime.utcnow()
        elif not lecon.est_publie:
            lecon.date_publication = None

        if form.pdf.data and form.pdf.data.filename:
            try:
                new_pdf = _save_pdf_upload(lecon, form.pdf.data)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("lecons/form.html", form=form, cours=lecon.cours, lecon=lecon, is_edit=True)

            delete_asset_file(lecon.pdf_url, "uploads/pdfs/")
            lecon.pdf_url = new_pdf

        if form.audio.data and form.audio.data.filename:
            try:
                new_audio = _save_audio_upload(lecon, form.audio.data)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("lecons/form.html", form=form, cours=lecon.cours, lecon=lecon, is_edit=True)

            delete_asset_file(lecon.audio_url, "uploads/audios/")
            lecon.audio_url = new_audio

        db.session.commit()
        if should_notify_lesson_publication(previous_is_published, lecon):
            dispatch_lesson_published_notifications(lecon, app=current_app._get_current_object())
        flash(_("Lecon mise a jour avec succes."), "success")
        return redirect(url_for("lessons.detail", lecon_id=lecon.id))

    return render_template("lecons/form.html", form=form, cours=lecon.cours, lecon=lecon, is_edit=True)


@lessons_bp.route("/<int:lecon_id>/supprimer", methods=["POST"])
@login_required
def supprimer(lecon_id):
    _ensure_teacher_or_admin()
    lecon = Lecon.query.filter_by(id=lecon_id).first_or_404()
    if not user_can_manage_course(lecon.cours):
        abort(403)

    cours_id = lecon.cours_id
    delete_asset_file(lecon.pdf_url, "uploads/pdfs/")
    delete_asset_file(lecon.audio_url, "uploads/audios/")
    db.session.delete(lecon)
    db.session.commit()
    flash(_("Lecon supprimee avec succes."), "success")
    return redirect(url_for("courses.detail", cours_id=cours_id))
