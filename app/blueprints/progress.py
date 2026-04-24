import json
import time

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, stream_with_context, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, selectinload

from app.models import Cours, Inscription, Lecon, ProgressionLecon, XPEleve
from app.utils import get_ordered_lessons, get_progression_resume, get_progression_resumes, user_can_manage_course


progress_bp = Blueprint("progress", __name__)


def _managed_courses_for_user(user):
    query = Cours.query.options(selectinload(Cours.lecons)).order_by(Cours.nom.asc())
    if user.role == "admin":
        return query.all()
    if user.role == "enseignant":
        return query.filter(Cours.enseignant_id == user.id).all()
    return []


def _managed_courses_for_snapshot(user_id, user_role):
    query = Cours.query.options(selectinload(Cours.lecons)).order_by(Cours.nom.asc())
    if user_role == "admin":
        return query.all()
    if user_role == "enseignant":
        return query.filter(Cours.enseignant_id == user_id).all()
    return []


def _course_stats_payload(cours):
    inscriptions = (
        Inscription.query.options(joinedload(Inscription.eleve))
        .filter_by(cours_id=cours.id, est_active=True)
        .all()
    )
    total_lecons = len(get_ordered_lessons(cours, published_only=True))
    resumes = get_progression_resumes(cours, [inscription.eleve_id for inscription in inscriptions], published_only=True)

    data = []
    for inscription in inscriptions:
        resume = resumes.get(
            inscription.eleve_id,
            {
                "lecons_vues": 0,
                "total_lecons": total_lecons,
                "pourcentage": 0,
                "score_moyen": None,
                "derniere_activite": None,
            },
        )
        data.append(
            {
                "eleve_id": inscription.eleve.id,
                "nom": inscription.eleve.nom,
                "prenom": inscription.eleve.prenom,
                "email": inscription.eleve.email,
                "pourcentage": resume["pourcentage"],
                "score_moyen": resume["score_moyen"],
                "lecons_vues": resume["lecons_vues"],
                "total_lecons": resume["total_lecons"],
                "derniere_activite": resume["derniere_activite"],
            }
        )

    total_eleves = len(data)
    moyenne_progression = round(sum(item["pourcentage"] for item in data) / total_eleves) if total_eleves else 0
    scored_items = [item["score_moyen"] for item in data if item["score_moyen"] is not None]
    moyenne_score = round(sum(scored_items) / len(scored_items), 1) if scored_items else None
    eleves_actifs = sum(1 for item in data if item["derniere_activite"])

    return {
        "eleves_data": data,
        "total_eleves": total_eleves,
        "moyenne_progression": moyenne_progression,
        "moyenne_score": moyenne_score,
        "eleves_actifs": eleves_actifs,
    }


@progress_bp.route("/moi")
@login_required
def dashboard_eleve():
    if current_user.role != "eleve":
        return redirect(url_for("main.dashboard"))

    inscriptions = (
        Inscription.query.options(joinedload(Inscription.cours).selectinload(Cours.lecons))
        .filter_by(eleve_id=current_user.id, est_active=True)
        .all()
    )

    xp = XPEleve.get_or_create(current_user.id)
    progression_data = []
    for inscription in inscriptions:
        cours = inscription.cours
        resume = get_progression_resume(cours, current_user.id, published_only=True)
        ordered_lessons = get_ordered_lessons(cours, published_only=True)
        lesson_ids = [lesson.id for lesson in ordered_lessons]
        progressions = (
            ProgressionLecon.query.filter(
                ProgressionLecon.eleve_id == current_user.id,
                ProgressionLecon.lecon_id.in_(lesson_ids),
            ).all()
            if lesson_ids
            else []
        )
        progressions_map = {progression.lecon_id: progression for progression in progressions}

        lecons_path = []
        previous_completed = True
        current_open_marked = False
        for index, lesson in enumerate(ordered_lessons):
            progression = progressions_map.get(lesson.id)
            est_terminee = bool(progression and progression.vue)
            est_debloquee = index == 0 or previous_completed
            est_courante = est_debloquee and not est_terminee and not current_open_marked
            if est_courante:
                current_open_marked = True

            lecons_path.append(
                {
                    "lecon": lesson,
                    "progression": progression,
                    "est_terminee": est_terminee,
                    "est_debloquee": est_debloquee,
                    "est_courante": est_courante,
                }
            )
            previous_completed = est_terminee

        progression_data.append(
            {
                "cours": cours,
                "lecons_vues": resume["lecons_vues"],
                "total_lecons": resume["total_lecons"],
                "pourcentage": resume["pourcentage"],
                "score_moyen": resume["score_moyen"],
                "derniere_activite": resume["derniere_activite"],
                "lecons_path": lecons_path,
            }
        )

    return render_template(
        "progression/dashboard_eleve.html",
        progression_data=progression_data,
        xp=xp,
    )


@progress_bp.route("/mes-eleves")
@login_required
def dashboard_enseignant():
    if current_user.role not in {"enseignant", "admin"}:
        abort(403)

    cours_list = _managed_courses_for_user(current_user)
    cours_data = []
    for cours in cours_list:
        stats = _course_stats_payload(cours)
        latest_activity = None
        if stats["eleves_data"]:
            latest_activity = max(
                (item["derniere_activite"] for item in stats["eleves_data"] if item["derniere_activite"]),
                default=None,
            )

        cours_data.append(
            {
                "cours": cours,
                "total_eleves": stats["total_eleves"],
                "moyenne_progression": stats["moyenne_progression"],
                "moyenne_score": stats["moyenne_score"],
                "eleves_actifs": stats["eleves_actifs"],
                "latest_activity": latest_activity,
            }
        )

    return render_template("progression/dashboard_enseignant.html", cours_data=cours_data)


@progress_bp.route("/api/cours/<int:cours_id>")
@login_required
def api_cours(cours_id):
    cours = Cours.query.options(selectinload(Cours.lecons)).filter_by(id=cours_id).first_or_404()
    if not user_can_manage_course(cours):
        abort(403)
    stats = _course_stats_payload(cours)

    return render_template(
        "progression/cours_stats.html",
        cours=cours,
        **stats,
    )


@progress_bp.route("/api/cours/<int:cours_id>/json")
@login_required
def api_cours_json(cours_id):
    if request.args.get("raw") != "1":
        return redirect(url_for("progress.api_cours", cours_id=cours_id))

    cours = Cours.query.options(selectinload(Cours.lecons)).filter_by(id=cours_id).first_or_404()
    if not user_can_manage_course(cours):
        abort(403)
    stats = _course_stats_payload(cours)

    serialized = []
    for item in stats["eleves_data"]:
        serialized.append(
            {
                "eleve_id": item["eleve_id"],
                "nom": item["nom"],
                "prenom": item["prenom"],
                "email": item["email"],
                "pourcentage": item["pourcentage"],
                "score_moyen": item["score_moyen"],
                "lecons_vues": item["lecons_vues"],
                "total_lecons": item["total_lecons"],
                "derniere_activite": item["derniere_activite"].isoformat() if item["derniere_activite"] else None,
            }
        )

    if request.args.get("download") == "1":
        return jsonify(serialized)

    pretty_json = json.dumps(serialized, ensure_ascii=False, indent=2)
    return render_template(
        "progression/cours_json.html",
        cours=cours,
        pretty_json=pretty_json,
        **stats,
    )


@progress_bp.route("/stream")
@login_required
def stream_progression():
    if current_user.role not in {"admin", "enseignant", "eleve"}:
        abort(403)

    user_id = current_user.id
    user_role = current_user.role

    def generate():
        while True:
            if user_role in {"enseignant", "admin"}:
                cours_ids = [cours.id for cours in _managed_courses_for_snapshot(user_id, user_role)]
                if cours_ids:
                    recents = (
                        ProgressionLecon.query.join(Lecon)
                        .filter(Lecon.cours_id.in_(cours_ids))
                        .order_by(ProgressionLecon.date_vue.desc())
                        .limit(20)
                        .all()
                    )
                else:
                    recents = []

                data = [
                    {
                        "eleve_id": progression.eleve_id,
                        "lecon_id": progression.lecon_id,
                        "score": progression.pourcentage_score,
                        "date": progression.date_vue.isoformat() if progression.date_vue else None,
                    }
                    for progression in recents
                    if progression.date_vue
                ]
            else:
                xp = XPEleve.get_or_create(user_id)
                data = {
                    "points": xp.points or 0,
                    "streak": xp.streak_jours or 0,
                    "total_lecons_terminees": xp.total_lecons_terminees or 0,
                }

            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(10)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
