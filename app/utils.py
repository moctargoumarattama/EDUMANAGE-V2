import re
from urllib.parse import parse_qs, urlparse

from flask import current_app, has_request_context, request
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.audio import resolve_choice_audio_url, resolve_question_audio_url
from app.storage import build_asset_url


CEFR_LEVELS = ["A1", "A2"]
LEVEL_BADGES = {
    "A1": "badge-a1",
    "A2": "badge-a2",
}


def get_dashboard_stats():
    from app.models import Cours, Inscription, Lecon, Utilisateur

    return {
        "total_utilisateurs": Utilisateur.query.count(),
        "total_enseignants": Utilisateur.query.filter_by(role="enseignant").count(),
        "total_eleves": Utilisateur.query.filter_by(role="eleve").count(),
        "total_cours": Cours.query.count(),
        "total_lecons": Lecon.query.count(),
        "total_inscriptions": Inscription.query.filter_by(est_active=True).count(),
    }


def log_action(module, action, level="INFO", user_id=None, details=None):
    from app.models import Log

    try:
        ip_address = request.remote_addr if has_request_context() else None
        utilisateur_id = user_id
        if utilisateur_id is None and getattr(current_user, "is_authenticated", False):
            utilisateur_id = current_user.id

        log_entry = Log(
            level=(level or "INFO").upper(),
            module=module,
            action=action,
            details=details,
            utilisateur_id=utilisateur_id,
            ip_address=ip_address,
        )
        db.session.add(log_entry)
        db.session.commit()

        logger = current_app.logger
        message = f"[{module}] {action} - {details or ''}"
        if log_entry.level == "ERROR":
            logger.error(message)
        elif log_entry.level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    except Exception as exc:  # pragma: no cover - fallback log path
        try:
            current_app.logger.error("Erreur journalisation: %s", exc)
        except Exception:
            pass


def user_can_manage_course(cours, user=None):
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) == "admin":
        return True
    if getattr(user, "role", None) != "enseignant":
        return False
    return cours.enseignant_id == user.id


def is_student_enrolled(cours, eleve_id):
    from app.models import Inscription

    return (
        Inscription.query.filter_by(
            eleve_id=eleve_id,
            cours_id=cours.id,
            est_active=True,
        ).first()
        is not None
    )


def build_quiz_results(lecon, eleve_id):
    from app.models import ReponseEleve

    question_ids = [question.id for question in lecon.questions]
    if not question_ids:
        return None

    reponses = (
        ReponseEleve.query.filter(
            ReponseEleve.eleve_id == eleve_id,
            ReponseEleve.question_id.in_(question_ids),
        ).all()
    )
    if not reponses:
        return None

    reponses_by_question = {reponse.question_id: reponse for reponse in reponses}
    details = []
    nb_correct = 0
    nb_total = len(lecon.questions)

    for question in lecon.questions:
        reponse = reponses_by_question.get(question.id)
        if not reponse:
            continue

        bonne_reponse = next((choix for choix in question.choix if choix.est_correct), None)
        bonne_reponse_texte = question.bonne_reponse_texte or (bonne_reponse.texte if bonne_reponse else "")
        nb_correct += 1 if reponse.est_correct else 0
        details.append(
            {
                "question_id": question.id,
                "texte_question": question.texte,
                "choix_selectionne": reponse.reponse_saisie or (reponse.choix.texte if reponse.choix else ""),
                "est_correct": reponse.est_correct,
                "texte_bonne_reponse": bonne_reponse_texte,
                "type_exercice": question.type_exercice or "qcm",
            }
        )

    score = (nb_correct / nb_total) if nb_total else 0
    return {
        "score": round(score, 2),
        "score_percent": round(score * 100),
        "nb_correct": nb_correct,
        "nb_total": nb_total,
        "details": details,
    }


def get_ordered_lessons(cours, *, published_only=False):
    lessons = sorted(cours.lecons, key=lambda lesson: (lesson.ordre or 0, lesson.id))
    if published_only:
        lessons = [lesson for lesson in lessons if lesson.est_publie]
    return lessons


def get_progression_resume(cours, eleve_id, *, published_only=False):
    from app.models import ProgressionLecon

    lecon_ids = [lecon.id for lecon in get_ordered_lessons(cours, published_only=published_only)]
    total_lecons = len(lecon_ids)
    if not lecon_ids:
        return _empty_progression_resume(total_lecons=0)

    progressions = (
        ProgressionLecon.query.filter(
            ProgressionLecon.eleve_id == eleve_id,
            ProgressionLecon.lecon_id.in_(lecon_ids),
        ).all()
    )

    return _build_progression_resume(progressions, total_lecons)


def get_progression_resumes(cours, eleve_ids, *, published_only=False):
    from app.models import ProgressionLecon

    unique_eleve_ids = [eleve_id for eleve_id in dict.fromkeys(eleve_ids or ()) if eleve_id is not None]
    if not unique_eleve_ids:
        return {}

    lecon_ids = [lecon.id for lecon in get_ordered_lessons(cours, published_only=published_only)]
    total_lecons = len(lecon_ids)
    if not lecon_ids:
        return {eleve_id: _empty_progression_resume(total_lecons=0) for eleve_id in unique_eleve_ids}

    progressions = (
        ProgressionLecon.query.filter(
            ProgressionLecon.eleve_id.in_(unique_eleve_ids),
            ProgressionLecon.lecon_id.in_(lecon_ids),
        ).all()
    )

    progressions_by_eleve = {eleve_id: [] for eleve_id in unique_eleve_ids}
    for progression in progressions:
        progressions_by_eleve.setdefault(progression.eleve_id, []).append(progression)

    return {
        eleve_id: _build_progression_resume(progressions_by_eleve.get(eleve_id, []), total_lecons)
        for eleve_id in unique_eleve_ids
    }


def _empty_progression_resume(total_lecons):
    return {
        "lecons_vues": 0,
        "total_lecons": total_lecons,
        "pourcentage": 0,
        "score_moyen": None,
        "derniere_activite": None,
    }


def _build_progression_resume(progressions, total_lecons):
    lecons_vues = sum(1 for progression in progressions if progression.vue)
    scores = [progression.score_quiz for progression in progressions if progression.score_quiz is not None]
    dates = [progression.date_vue for progression in progressions if progression.date_vue]
    score_moyen = round((sum(scores) / len(scores)) * 100, 1) if scores else None

    return {
        "lecons_vues": lecons_vues,
        "total_lecons": total_lecons,
        "pourcentage": round((lecons_vues / total_lecons) * 100) if total_lecons else 0,
        "score_moyen": score_moyen,
        "derniere_activite": max(dates) if dates else None,
    }


def extract_youtube_video_id(video_url):
    if not video_url:
        return None

    parsed = urlparse(video_url)
    host = (parsed.netloc or "").lower()
    if "youtu.be" in host:
        video_id = parsed.path.strip("/").split("/")[0]
    elif "youtube.com" in host:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith("/embed/"):
            video_id = parsed.path.split("/embed/", 1)[1].split("/")[0]
        else:
            video_id = None
    else:
        return None

    return (video_id or "").strip() or None


def extract_youtube_embed(video_url):
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        return None
    return (
        f"https://www.youtube-nocookie.com/embed/{video_id}"
        "?rel=0&modestbranding=1&playsinline=1"
    )


def extract_youtube_watch_url(video_url):
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def build_static_media_url(path):
    return build_asset_url(path)


def text_is_arabic(value):
    if not value:
        return False
    return any("\u0600" <= char <= "\u06ff" for char in value)


def strip_arabic_diacritics(value):
    if not value:
        return ""
    return "".join(char for char in value if not ("\u064b" <= char <= "\u065f")).strip()


def normalize_arabic_answer(value):
    if not value:
        return ""
    return " ".join(strip_arabic_diacritics(value).split())


def normalize_arabic_compact(value):
    return normalize_arabic_answer(value).replace(" ", "")


def normalize_arabic_lookup(value):
    if not value:
        return ""
    value = strip_arabic_diacritics(value).replace("\u0640", "")
    value = re.sub(r"[^\u0600-\u06FF0-9\s]", " ", value)
    return " ".join(value.split()).strip()


def speaking_matches_expected(transcript, expected):
    normalized_transcript = normalize_arabic_compact(transcript)
    normalized_expected = normalize_arabic_compact(expected)
    if not normalized_transcript or not normalized_expected:
        return False
    return (
        normalized_transcript == normalized_expected
        or normalized_expected in normalized_transcript
        or normalized_transcript in normalized_expected
    )


def serialize_lesson_questions(lecon):
    serialized = []
    for question in lecon.questions:
        correct_choice = next((choix for choix in question.choix if choix.est_correct), None)
        incorrect_choice = next((choix for choix in question.choix if not choix.est_correct), None)
        ordre_words = []
        raw_order_answer = question.bonne_reponse_texte or (correct_choice.texte if correct_choice else "")
        if raw_order_answer:
            ordre_words = [word for word in raw_order_answer.split() if word]

        if question.type_exercice == "dictee":
            correction = question.bonne_reponse_texte or ""
        elif correct_choice and correct_choice.texte:
            correction = f"Bonne réponse : {correct_choice.texte}"
        else:
            correction = ""

        serialized.append(
            {
                "id": question.id,
                "texte": question.texte,
                "type_exercice": question.type_exercice or "qcm",
                "is_arabic": text_is_arabic(question.texte),
                "audio_url": resolve_question_audio_url(question, lecon=lecon, correct_choice=correct_choice),
                "correct_choice_id": correct_choice.id if correct_choice else None,
                "incorrect_choice_id": incorrect_choice.id if incorrect_choice else None,
                "correction": correction,
                "bonne_reponse_ordre": ordre_words,
                "bonne_reponse_texte": question.bonne_reponse_texte,
                "choix": [
                    {
                        "id": choix.id,
                        "texte": choix.texte,
                        "est_correct": bool(choix.est_correct),
                        "audio_url": resolve_choice_audio_url(choix),
                        "is_arabic": text_is_arabic(choix.texte),
                    }
                    for choix in question.choix
                ],
            }
        )
    return serialized


def serialize_placement_questions(test, questions=None):
    serialized = []
    question_items = questions if questions is not None else test.questions
    for question in question_items:
        correct_choice = next((choix for choix in question.choix if choix.est_correct), None)
        incorrect_choice = next((choix for choix in question.choix if not choix.est_correct), None)
        ordre_words = []
        if correct_choice and correct_choice.texte:
            ordre_words = [word for word in correct_choice.texte.split() if word]

        serialized.append(
            {
                "id": question.id,
                "texte": question.texte,
                "type_exercice": question.type_question or "qcm",
                "is_arabic": text_is_arabic(question.texte),
                "audio_url": build_static_media_url(question.audio_url),
                "image_url": build_static_media_url(question.image_url),
                "correct_choice_id": correct_choice.id if correct_choice else None,
                "incorrect_choice_id": incorrect_choice.id if incorrect_choice else None,
                "bonne_reponse_ordre": ordre_words,
                "choix": [
                    {
                        "id": choix.id,
                        "texte": choix.texte,
                        "image_url": build_static_media_url(choix.image_url),
                        "est_correct": bool(choix.est_correct),
                        "is_arabic": text_is_arabic(choix.texte),
                    }
                    for choix in question.choix
                ],
            }
        )
    return serialized


def get_next_lesson_id(cours, current_lesson_id, *, published_only=False):
    ordered_lessons = get_ordered_lessons(cours, published_only=published_only)
    for index, lesson in enumerate(ordered_lessons):
        if lesson.id == current_lesson_id and index + 1 < len(ordered_lessons):
            return ordered_lessons[index + 1].id
    return None
