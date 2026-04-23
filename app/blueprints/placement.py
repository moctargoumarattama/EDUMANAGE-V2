import json

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app import db
from app.authorization import admin_required, eleve_required
from app.models import PlacementChoix, PlacementQuestion, PlacementTest, ResultatPlacement
from app.utils import serialize_placement_questions, text_is_arabic


placement_bp = Blueprint("placement", __name__)
MAX_PLACEMENT_QUESTION_COUNT = 10
MIN_PLACEMENT_QUESTION_COUNT = 3


def _active_test():
    return (
        PlacementTest.query.options(selectinload(PlacementTest.questions).selectinload(PlacementQuestion.choix))
        .order_by(PlacementTest.id.asc())
        .first()
    )


def _get_or_create_test():
    test = _active_test()
    if test is None:
        test = PlacementTest()
        db.session.add(test)
        db.session.commit()
    return test


def _selected_questions(test):
    if test is None:
        return []
    return list(test.questions)[:MAX_PLACEMENT_QUESTION_COUNT]


def _test_is_ready(test):
    return len(_selected_questions(test)) >= MIN_PLACEMENT_QUESTION_COUNT


def placement_test_is_ready():
    return _test_is_ready(_active_test())


def _ensure_student():
    if current_user.role != "eleve":
        abort(403)


@placement_bp.route("/")
@login_required
@eleve_required
def intro():
    resultat = ResultatPlacement.query.filter_by(eleve_id=current_user.id).first()
    if resultat:
        flash(_("Vous avez deja passe le test de niveau."), "info")
        return redirect(url_for("courses.liste"))

    if session.get("langue") is None:
        return redirect(url_for("main.choix_langue"))

    test = _active_test()
    if not _test_is_ready(test):
        flash(_("Test non disponible pour le moment."), "warning")
        return redirect(url_for("courses.liste"))

    return render_template("placement/intro.html", test=test, question_count=len(_selected_questions(test)))


@placement_bp.route("/start")
@login_required
@eleve_required
def start():
    if ResultatPlacement.query.filter_by(eleve_id=current_user.id).first():
        flash(_("Vous avez deja passe le test de niveau."), "info")
        return redirect(url_for("courses.liste"))

    if session.get("langue") is None:
        return redirect(url_for("main.choix_langue"))

    test = _active_test()
    questions = _selected_questions(test)
    if len(questions) < MIN_PLACEMENT_QUESTION_COUNT:
        flash(_("Test non disponible pour le moment."), "warning")
        return redirect(url_for("courses.liste"))

    questions_json = json.dumps(serialize_placement_questions(test, questions=questions), ensure_ascii=False)
    return render_template("placement/test_flow.html", test=test, questions_json=questions_json)


@placement_bp.route("/complete", methods=["POST"])
@login_required
@eleve_required
def complete():
    if ResultatPlacement.query.filter_by(eleve_id=current_user.id).first():
        return jsonify({"error": "Test deja passe."}), 400

    test = _active_test()
    questions = _selected_questions(test)
    if len(questions) < MIN_PLACEMENT_QUESTION_COUNT:
        return jsonify({"error": "Test non disponible."}), 400

    payload = request.get_json(silent=True) or {}
    submitted_results = payload.get("resultats") or []
    submitted_by_question = {
        item.get("question_id"): item for item in submitted_results if item.get("question_id") is not None
    }

    nb_total = len(questions)
    if nb_total == 0:
        return jsonify({"error": "Aucune question disponible."}), 400

    nb_correct = 0
    for question in questions:
        submitted = submitted_by_question.get(question.id)
        if not submitted:
            continue

        choix_id = submitted.get("choix_id")
        try:
            choix_id = int(choix_id)
        except (TypeError, ValueError):
            continue

        choix = next((item for item in question.choix if item.id == choix_id), None)
        if choix and choix.est_correct:
            nb_correct += 1

    score = nb_correct / nb_total
    niveau_assigne = "A2" if score >= 0.6 else "A1"

    resultat = ResultatPlacement(
        eleve_id=current_user.id,
        niveau_assigne=niveau_assigne,
        score=score,
        a_passe=True,
    )
    current_user.niveau_depart = niveau_assigne
    db.session.add(resultat)
    db.session.commit()

    message = (
        _("Excellent ! Vous commencez au niveau A2.")
        if niveau_assigne == "A2"
        else _("Vous commencez au niveau A1 pour consolider les bases.")
    )
    return jsonify(
        {
            "niveau": niveau_assigne,
            "score": round(score, 2),
            "message": message,
        }
    )


@placement_bp.route("/admin/questions")
@login_required
@admin_required
def admin_questions():
    test = _get_or_create_test()
    return render_template("placement/admin_questions.html", test=test, text_is_arabic=text_is_arabic)


@placement_bp.route("/admin/nouvelle-question", methods=["POST"])
@login_required
@admin_required
def nouvelle_question():
    test = _get_or_create_test()

    texte = (request.form.get("texte") or "").strip()
    type_question = (request.form.get("type_question") or "qcm").strip()
    image_url = (request.form.get("image_url") or "").strip() or None
    audio_url = (request.form.get("audio_url") or "").strip() or None
    ordre = request.form.get("ordre", type=int) or 0
    correct_index = request.form.get("correct_index")

    choice_texts = [
        (request.form.get(f"choix_texte_{index}") or "").strip()
        for index in range(1, 5)
    ]
    choice_images = [
        (request.form.get(f"choix_image_{index}") or "").strip() or None
        for index in range(1, 5)
    ]

    if not texte:
        flash(_("Le texte de la question est obligatoire."), "danger")
        return redirect(url_for("placement.admin_questions"))

    if correct_index not in {"1", "2", "3", "4"}:
        flash(_("Vous devez designer exactement une bonne reponse."), "danger")
        return redirect(url_for("placement.admin_questions"))

    if sum(1 for value in choice_texts if value) < 2:
        flash(_("Ajoutez au moins deux choix pour la question."), "danger")
        return redirect(url_for("placement.admin_questions"))

    question = PlacementQuestion(
        test_id=test.id,
        texte=texte,
        type_question=type_question,
        image_url=image_url,
        audio_url=audio_url,
        ordre=ordre,
    )
    db.session.add(question)
    db.session.flush()

    for index, texte_choix in enumerate(choice_texts, start=1):
        if not texte_choix:
            continue
        db.session.add(
            PlacementChoix(
                question_id=question.id,
                texte=texte_choix,
                image_url=choice_images[index - 1],
                est_correct=str(index) == correct_index,
            )
        )

    db.session.commit()
    flash(_("Question de placement ajoutee avec succes."), "success")
    return redirect(url_for("placement.admin_questions"))


@placement_bp.route("/admin/supprimer-question/<int:question_id>", methods=["POST"])
@login_required
@admin_required
def supprimer_question(question_id):
    question = PlacementQuestion.query.filter_by(id=question_id).first_or_404()
    db.session.delete(question)
    db.session.commit()
    flash(_("Question supprimee."), "success")
    return redirect(url_for("placement.admin_questions"))
