from __future__ import annotations

import math
from datetime import datetime, timedelta

from flask import current_app, has_app_context, url_for
from werkzeug.routing import BuildError

from app import db
from app.models import (
    AppSetting,
    BadgeDefinition,
    Inscription,
    Notification,
    NotificationPreference,
    PasswordResetGrant,
    PushSubscription,
    SupportMessage,
    SupportThread,
    UserBadge,
    Utilisateur,
    XPEleve,
)
from app.notifications import envoyer_notification_push


NOTIFICATION_TYPES = (
    "lesson_published",
    "exercise_corrected",
    "badge_unlocked",
    "streak_at_risk",
)

NOTIFICATION_DEFAULTS = {
    "lesson_published": {
        "icon": "book",
        "push_enabled": True,
        "inbox_enabled": True,
        "label": "Nouvelle leçon",
    },
    "exercise_corrected": {
        "icon": "check-circle",
        "push_enabled": True,
        "inbox_enabled": True,
        "label": "Exercice corrigé",
    },
    "badge_unlocked": {
        "icon": "award",
        "push_enabled": False,
        "inbox_enabled": True,
        "label": "Badge débloqué",
    },
    "streak_at_risk": {
        "icon": "alarm",
        "push_enabled": True,
        "inbox_enabled": True,
        "label": "Série en danger",
    },
}

BADGE_RULE_TYPES = (
    "lessons_completed",
    "xp_total",
)

DEFAULT_BADGES = (
    {
        "slug": "first-steps",
        "name": "Premiers pas",
        "description": "Terminer votre première leçon.",
        "image_url": "/static/icons/icon-192.png",
        "rule_type": "lessons_completed",
        "threshold": 1,
    },
    {
        "slug": "expert-alphabet",
        "name": "Expert en alphabet",
        "description": "Atteindre 3 leçons terminées.",
        "image_url": "/static/icons/icon-192.png",
        "rule_type": "lessons_completed",
        "threshold": 3,
    },
)

DEFAULT_SETTINGS = {
    "streak_risk_hours": "48",
    "badge_history_days": "30",
}


def _get_target_app(app=None):
    if app is not None:
        return app
    if has_app_context():
        return current_app._get_current_object()
    return None


def _safe_url_for(endpoint, fallback, **values):
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return fallback


def ensure_notification_defaults():
    changed = False
    for key, value in DEFAULT_SETTINGS.items():
        setting = AppSetting.query.filter_by(key=key).first()
        if setting is None:
            db.session.add(AppSetting(key=key, value=value))
            changed = True

    for badge_data in DEFAULT_BADGES:
        badge = BadgeDefinition.query.filter_by(slug=badge_data["slug"]).first()
        if badge is None:
            db.session.add(BadgeDefinition(**badge_data))
            changed = True

    if changed:
        db.session.commit()


def get_app_setting(key, default=None):
    setting = AppSetting.query.filter_by(key=key).first()
    if setting is None:
        return default
    return setting.value


def get_app_setting_int(key, default):
    value = get_app_setting(key, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def set_app_setting(key, value):
    setting = AppSetting.query.filter_by(key=key).first()
    if setting is None:
        setting = AppSetting(key=key, value=str(value))
        db.session.add(setting)
    else:
        setting.value = str(value)
    db.session.commit()
    return setting


def get_notification_preferences(user_id):
    existing = {
        pref.type: pref
        for pref in NotificationPreference.query.filter_by(user_id=user_id).all()
    }
    items = []
    for notification_type in NOTIFICATION_TYPES:
        defaults = NOTIFICATION_DEFAULTS[notification_type]
        pref = existing.get(notification_type)
        items.append(
            {
                "type": notification_type,
                "label": defaults["label"],
                "inbox_enabled": pref.inbox_enabled if pref else defaults["inbox_enabled"],
                "push_enabled": pref.push_enabled if pref else defaults["push_enabled"],
            }
        )
    return items


def save_notification_preferences(user_id, submitted_types):
    for notification_type in NOTIFICATION_TYPES:
        pref = NotificationPreference.query.filter_by(user_id=user_id, type=notification_type).first()
        if pref is None:
            pref = NotificationPreference(user_id=user_id, type=notification_type)
            db.session.add(pref)
        pref.inbox_enabled = True
        pref.push_enabled = bool(submitted_types.get(f"{notification_type}:push"))
    db.session.commit()


def get_notification_delivery(user_id, notification_type):
    defaults = NOTIFICATION_DEFAULTS.get(
        notification_type,
        {
            "inbox_enabled": True,
            "push_enabled": False,
        },
    )
    pref = NotificationPreference.query.filter_by(user_id=user_id, type=notification_type).first()
    if pref is None:
        return {
            "inbox_enabled": defaults["inbox_enabled"],
            "push_enabled": defaults["push_enabled"],
        }
    return {
        "inbox_enabled": pref.inbox_enabled,
        "push_enabled": pref.push_enabled,
    }


def serialize_notification(notification):
    payload = notification.get_payload()
    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "cta_url": notification.cta_url,
        "icon": notification.icon or NOTIFICATION_DEFAULTS.get(notification.type, {}).get("icon", "bell"),
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "relative_time": relative_time_label(notification.created_at),
        "payload": payload,
        "open_url": _safe_url_for(
            "notifications.open_notification",
            f"/notifications/{notification.id}/go",
            notification_id=notification.id,
        ),
    }


def relative_time_label(value):
    if not value:
        return ""

    delta = datetime.utcnow() - value
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return "à l'instant"

    minutes = seconds // 60
    if minutes < 60:
        return f"il y a {minutes} min"

    hours = minutes // 60
    if hours < 24:
        return f"il y a {hours} h"

    days = hours // 24
    return f"il y a {days} j"


def count_unread_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def list_notifications_for_user(user_id, limit=20, unread_only=False):
    query = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc(), Notification.id.desc())
    if unread_only:
        query = query.filter_by(is_read=False)
    return query.limit(limit).all() if limit else query.all()


def mark_notification_read(user_id, notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first_or_404()
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
    return notification


def mark_all_notifications_read(user_id):
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    now = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
    db.session.commit()
    return len(notifications)


def _send_push_if_enabled(notification, app=None):
    delivery = get_notification_delivery(notification.user_id, notification.type)
    if not delivery["push_enabled"]:
        return False

    target_app = _get_target_app(app)
    if target_app is None:
        return False

    subscriptions = PushSubscription.query.filter_by(eleve_id=notification.user_id, active=True).all()
    if not subscriptions:
        return False

    payload = {
        "title": notification.title,
        "body": notification.message,
        "url": notification.cta_url or "/notifications/inbox",
    }
    pushed = False
    for subscription in subscriptions:
        if envoyer_notification_push(subscription, payload, app=target_app):
            pushed = True
        else:
            subscription.active = False
    if pushed:
        notification.pushed_at = datetime.utcnow()
    db.session.commit()
    return pushed


def create_notification(
    user_id,
    notification_type,
    title,
    message,
    *,
    cta_url=None,
    icon=None,
    event_key=None,
    payload=None,
    app=None,
):
    existing = None
    if event_key:
        existing = Notification.query.filter_by(user_id=user_id, event_key=event_key).first()
    if existing is not None:
        return existing, False

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        cta_url=cta_url,
        icon=icon or NOTIFICATION_DEFAULTS.get(notification_type, {}).get("icon", "bell"),
        event_key=event_key,
    )
    notification.set_payload(payload)
    db.session.add(notification)
    db.session.commit()

    _send_push_if_enabled(notification, app=app)
    return notification, True


def dispatch_lesson_published_notifications(lecon, app=None):
    created = 0
    if not lecon.est_publie or not lecon.cours or not lecon.cours.est_publie:
        return 0

    active_inscriptions = Inscription.query.filter_by(cours_id=lecon.cours_id, est_active=True).all()
    for inscription in active_inscriptions:
        _, was_created = create_notification(
            inscription.eleve_id,
            "lesson_published",
            "Nouvelle leçon",
            f'"{lecon.titre}" a été publiée',
            cta_url=_safe_url_for("lessons.start", f"/lecons/{lecon.id}/start", lecon_id=lecon.id),
            event_key=f"lesson-published:{lecon.id}",
            payload={"lesson_id": lecon.id, "course_id": lecon.cours_id},
            app=app,
        )
        created += 1 if was_created else 0
    return created


def create_exercise_corrected_notification(user_id, lecon, *, score_percent, nb_correct, nb_total, app=None):
    return create_notification(
        user_id,
        "exercise_corrected",
        "Exercice corrigé",
        f'Vous avez obtenu {nb_correct}/{nb_total} à "{lecon.cours.nom}"',
        cta_url=_safe_url_for("progress.dashboard_eleve", "/progression/moi"),
        event_key=f"exercise-corrected:{user_id}:{lecon.id}",
        payload={
            "lesson_id": lecon.id,
            "course_id": lecon.cours_id,
            "score_percent": score_percent,
            "nb_correct": nb_correct,
            "nb_total": nb_total,
        },
        app=app,
    )[0]


def _badge_matches(badge, xp):
    if badge.rule_type == "lessons_completed":
        return (xp.total_lecons_terminees or 0) >= badge.threshold
    if badge.rule_type == "xp_total":
        return (xp.points or 0) >= badge.threshold
    return False


def award_badges_for_user(user_id, app=None):
    xp = XPEleve.get_or_create(user_id)
    awarded = []
    badges = (
        BadgeDefinition.query.filter(BadgeDefinition.is_active.is_(True), BadgeDefinition.rule_type.in_(BADGE_RULE_TYPES))
        .order_by(BadgeDefinition.id.asc())
        .all()
    )
    for badge in badges:
        already_earned = UserBadge.query.filter_by(user_id=user_id, badge_id=badge.id).first()
        if already_earned or not _badge_matches(badge, xp):
            continue

        notification, _ = create_notification(
            user_id,
            "badge_unlocked",
            "Badge débloqué",
            badge.name,
            cta_url=_safe_url_for("notifications.badges", "/notifications/badges"),
            event_key=f"badge-unlocked:{user_id}:{badge.id}",
            payload={"badge_id": badge.id, "badge_slug": badge.slug},
            app=app,
        )
        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge.id,
            source_notification_id=notification.id,
        )
        db.session.add(user_badge)
        db.session.commit()
        awarded.append(user_badge)
    return awarded


def get_badge_history(user_id, days=None):
    query = (
        UserBadge.query.filter_by(user_id=user_id)
        .join(BadgeDefinition, BadgeDefinition.id == UserBadge.badge_id)
        .order_by(UserBadge.date_earned.desc(), UserBadge.id.desc())
    )
    if days:
        query = query.filter(UserBadge.date_earned >= datetime.utcnow() - timedelta(days=days))
    return query.all()


def process_streak_risk_notifications(app):
    threshold_hours = max(get_app_setting_int("streak_risk_hours", 48), 1)
    cutoff = datetime.utcnow() - timedelta(hours=threshold_hours)
    candidates = XPEleve.query.filter(
        XPEleve.derniere_activite.isnot(None),
        XPEleve.derniere_activite <= cutoff,
    ).all()

    created = 0
    for xp in candidates:
        _, was_created = create_notification(
            xp.eleve_id,
            "streak_at_risk",
            "Série en danger",
            "Revenez aujourd'hui pour protéger votre série.",
            cta_url=_safe_url_for("progress.dashboard_eleve", "/progression/moi"),
            event_key=f"streak-risk:{xp.eleve_id}:{datetime.utcnow().date().isoformat()}",
            payload={"threshold_hours": threshold_hours},
            app=app,
        )
        created += 1 if was_created else 0

    return {
        "cibles": len(candidates),
        "envoyes": created,
        "push_sent": Notification.query.filter(
            Notification.type == "streak_at_risk",
            Notification.created_at >= datetime.utcnow() - timedelta(minutes=5),
            Notification.pushed_at.isnot(None),
        ).count(),
        "threshold_hours": threshold_hours,
    }


def get_notifications_stream_payload(user_id, limit=5):
    notifications = list_notifications_for_user(user_id, limit=limit)
    return {
        "unread_count": count_unread_notifications(user_id),
        "items": [serialize_notification(notification) for notification in notifications],
    }


def should_notify_lesson_publication(previous_is_published, lecon):
    return lecon.est_publie and (not previous_is_published)


def get_or_create_support_thread(student):
    thread = SupportThread.query.filter_by(student_id=student.id).first()
    if thread is None:
        thread = SupportThread(student_id=student.id)
        db.session.add(thread)
        db.session.commit()
    return thread


def create_support_message(
    thread,
    *,
    body,
    author_user=None,
    author_role,
    message_type="message",
    payload=None,
):
    message = SupportMessage(
        thread_id=thread.id,
        author_user_id=getattr(author_user, "id", None),
        author_role=author_role,
        message_type=message_type,
        body=body,
    )
    message.set_payload(payload)
    db.session.add(message)

    now = datetime.utcnow()
    thread.last_activity_at = now
    if message_type == "reset_requested":
        thread.last_reset_requested_at = now
    if message_type == "reset_granted":
        thread.last_reset_granted_at = now

    db.session.commit()
    return message


def get_latest_reset_request_message(thread):
    return (
        SupportMessage.query.filter_by(thread_id=thread.id, message_type="reset_requested")
        .order_by(SupportMessage.created_at.desc(), SupportMessage.id.desc())
        .first()
    )


def get_active_reset_grant(thread):
    return (
        PasswordResetGrant.query.filter_by(thread_id=thread.id, used_at=None)
        .order_by(PasswordResetGrant.created_at.desc(), PasswordResetGrant.id.desc())
        .first()
    )


def notify_admins_about_support_thread(thread, *, title, message, event_key, payload=None, app=None):
    if not isinstance(thread, SupportThread):
        raise TypeError("thread must be a SupportThread instance")

    admins = Utilisateur.query.filter_by(role="admin", statut="actif").all()
    created = 0
    target_url = _safe_url_for(
        "notifications.admin_support_thread",
        f"/notifications/support/{thread.id}",
        thread_id=thread.id,
    )
    base_payload = {"thread_id": thread.id, "student_id": thread.student_id}
    if payload:
        base_payload.update(payload)

    for admin in admins:
        _, was_created = create_notification(
            admin.id,
            "support_request",
            title,
            message,
            cta_url=target_url,
            icon="chat-left-text",
            event_key=f"{event_key}:admin:{admin.id}",
            payload=base_payload,
            app=app,
        )
        created += 1 if was_created else 0
    return created
