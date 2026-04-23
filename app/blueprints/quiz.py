from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.models import Choix, Lecon, ProgressionLecon, Question, ReponseEleve
from app.utils import (
    build_quiz_results,
    is_student_enrolled,
    normalize_arabic_answer,
    speaking_matches_expected,
    user_can_manage_course,
)


quiz_bp = Blueprint("quiz", __name__)


def _ensure_teacher_or_admin():
    if current_user.role not in {"enseignant", "admin"}:
        abort(403)


@quiz_bp.route("/lecon/<int:lecon_id>/nouvelle-question", methods=["GET", "POST"])
@login_required
def nouvelle_question(lecon_id):
    _ensure_teacher_or_admin()
    lecon = (
        Lecon.query.options(joinedload(Lecon.cours), selectinload(Lecon.questions))
        .filter_by(id=lecon_id)
        .first_or_404()
    )
    if not user_can_manage_course(lecon.cours):
        abort(403)

    if request.method == "POST":
        texte = (request.form.get("texte") or "").strip()
        type_exercice = (request.form.get("type_exercice") or "qcm").strip() or "qcm"
        audio_url = (request.form.get("audio_url") or "").strip() or None
        bonne_reponse_texte = (request.form.get("bonne_reponse_texte") or "").strip() or None
        choix_textes = [(request.form.get(f"choix_{index}_texte") or "").strip() for index in range(1, 5)]
        choix_corrects = [index for index in range(1, 5) if request.form.get(f"choix_{index}_correct")]

        is_free_response = type_exercice in {"dictee", "speaking"}

        if not texte:
            flash(_("Le texte de la question est obligatoire."), "danger")
        elif type_exercice == "dictee" and not audio_url:
            flash(_("L'URL audio est obligatoire pour une dictee."), "danger")
        elif is_free_response and not bonne_reponse_texte:
            flash(_("La bonne reponse texte est obligatoire pour cet exercice."), "danger")
        elif not is_free_response and any(not texte_choix for texte_choix in choix_textes):
            flash(_("Les quatre choix doivent etre renseignes."), "danger")
        elif not is_free_response and len(choix_corrects) != 1:
            flash(_("Vous devez marquer exactement une bonne reponse."), "danger")
        else:
            question = Question(
                lecon_id=lecon.id,
                texte=texte,
                ordre=(max([question.ordre or 0 for question in lecon.questions], default=-1) + 1),
                type_exercice=type_exercice,
                audio_url=audio_url,
                bonne_reponse_texte=bonne_reponse_texte,
            )
            db.session.add(question)
            db.session.flush()

            if not is_free_response:
                for index, texte_choix in enumerate(choix_textes, start=1):
                    db.session.add(
                        Choix(
                            question_id=question.id,
                            texte=texte_choix,
                            est_correct=(index == choix_corrects[0]),
                        )
                    )

            db.session.commit()
            flash(_("Question ajoutee avec succes."), "success")
            return redirect(url_for("lessons.detail", lecon_id=lecon.id))

    return render_template("quiz/form_question.html", lecon=lecon)


@quiz_bp.route("/lecon/<int:lecon_id>/repondre", methods=["POST"])
@login_required
def repondre(lecon_id):
    if current_user.role != "eleve":
        abort(403)

    lecon = (
        Lecon.query.options(
            joinedload(Lecon.cours),
            selectinload(Lecon.questions).selectinload(Question.choix),
        )
        .filter_by(id=lecon_id)
        .first_or_404()
    )

    if not lecon.cours.est_publie or not is_student_enrolled(lecon.cours, current_user.id):
        return jsonify({"error": "Inscription requise pour repondre au quiz."}), 403

    if not lecon.questions:
        return jsonify({"error": "Cette lecon ne contient pas encore de quiz."}), 400

    payload = request.get_json(silent=True) or request.form
    resultats_existants = build_quiz_results(lecon, current_user.id)
    if resultats_existants and len(resultats_existants["details"]) == len(lecon.questions):
        return jsonify(resultats_existants)

    nb_correct = 0
    nb_total = len(lecon.questions)

    for question in lecon.questions:
        choix = None
        choix_id = None
        reponse_saisie = None
        est_correct = False

        question_type = question.type_exercice or "qcm"

        if question_type == "dictee":
            reponse_saisie = (payload.get(f"question_{question.id}_texte") or payload.get(f"question_{question.id}") or "").strip()
            if not reponse_saisie:
                return jsonify({"error": _("Veuillez repondre a toutes les questions.")}), 400
            bonne_reponse = (question.bonne_reponse_texte or "").strip()
            est_correct = normalize_arabic_answer(reponse_saisie) == normalize_arabic_answer(bonne_reponse)
        elif question_type == "speaking":
            reponse_saisie = (payload.get(f"question_{question.id}_texte") or payload.get(f"question_{question.id}") or "").strip()
            if not reponse_saisie:
                return jsonify({"error": _("Veuillez repondre a toutes les questions.")}), 400
            bonne_reponse = (question.bonne_reponse_texte or "").strip()
            est_correct = speaking_matches_expected(reponse_saisie, bonne_reponse)
        else:
            choix_brut = payload.get(f"question_{question.id}")
            if not choix_brut:
                return jsonify({"error": _("Veuillez repondre a toutes les questions.")}), 400

            try:
                choix_id = int(choix_brut)
            except (TypeError, ValueError):
                return jsonify({"error": _("Une reponse du quiz est invalide.")}), 400

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
            score_quiz=score,
        )
        db.session.add(progression)
    else:
        progression.vue = True
        progression.date_vue = datetime.utcnow()
        progression.score_quiz = score

    db.session.commit()
    return jsonify(build_quiz_results(lecon, current_user.id))
