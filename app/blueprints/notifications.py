import json
import secrets
import time
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.authorization import admin_required
from app.models import Notification, PasswordResetGrant, PushSubscription, SupportThread
from app.notification_center import (
    count_unread_notifications,
    create_support_message,
    ensure_notification_defaults,
    get_active_reset_grant,
    get_badge_history,
    get_latest_reset_request_message,
    get_notification_preferences,
    get_notifications_stream_payload,
    get_or_create_support_thread,
    get_app_setting_int,
    list_notifications_for_user,
    mark_all_notifications_read,
    mark_notification_read,
    notify_admins_about_support_thread,
    relative_time_label,
    save_notification_preferences,
    serialize_notification,
)
from app.utils import log_action


notifications_bp = Blueprint("notifications", __name__)

SUPPORT_GUEST_THREAD_ID = "support_guest_thread_id"
SUPPORT_GUEST_STUDENT_ID = "support_guest_student_id"


def _ensure_student():
    if current_user.role != "eleve":
        abort(403)


def _load_guest_support_thread():
    thread_id = session.get(SUPPORT_GUEST_THREAD_ID)
    student_id = session.get(SUPPORT_GUEST_STUDENT_ID)
    if not thread_id or not student_id:
        return None

    thread = SupportThread.query.filter_by(id=thread_id, student_id=student_id).first()
    if thread is None:
        session.pop(SUPPORT_GUEST_THREAD_ID, None)
        session.pop(SUPPORT_GUEST_STUDENT_ID, None)
    return thread


def _has_logged_in_session():
    return bool(session.get("_user_id"))


def _build_support_message_view(message, *, show_reset_links):
    payload = message.get_payload()
    reset_url = None
    reset_status = None
    if message.message_type == "reset_granted":
        grant_id = payload.get("grant_id")
        grant = PasswordResetGrant.query.filter_by(id=grant_id, thread_id=message.thread_id).first()
        if grant is not None:
            reset_status = {
                "expires_at": grant.expires_at.strftime("%d/%m/%Y %H:%M") if grant.expires_at else "",
                "used": grant.used_at is not None,
                "expired": grant.is_expired,
            }
            if show_reset_links:
                reset_url = url_for("main.reset_password_token", token=grant.token)

    if message.author_role == "admin":
        author_label = message.author_user.nom_complet if message.author_user else "Admin"
    elif message.author_role == "student":
        author_label = message.author_user.nom_complet if message.author_user else "Etudiant"
    else:
        author_label = "Systeme"

    return {
        "id": message.id,
        "author_role": message.author_role,
        "author_label": author_label,
        "message_type": message.message_type,
        "body": message.body,
        "payload": payload,
        "created_at": message.created_at,
        "created_label": message.created_at.strftime("%d/%m/%Y %H:%M") if message.created_at else "",
        "relative_time": relative_time_label(message.created_at),
        "reset_url": reset_url,
        "reset_status": reset_status,
    }


def _support_thread_summary(thread):
    latest_message = thread.latest_message
    pending_request = bool(
        thread.last_reset_requested_at
        and (
            thread.last_reset_granted_at is None
            or thread.last_reset_requested_at > thread.last_reset_granted_at
        )
    )
    active_grant = get_active_reset_grant(thread)
    return {
        "id": thread.id,
        "student_name": thread.student.nom_complet,
        "student_email": thread.student.email,
        "status": thread.status,
        "pending_request": pending_request,
        "has_active_grant": bool(active_grant and active_grant.is_active),
        "last_activity_label": relative_time_label(thread.last_activity_at),
        "last_activity_at": thread.last_activity_at,
        "last_message": latest_message.body if latest_message else "Aucun message pour le moment.",
        "open_url": url_for("notifications.admin_support_thread", thread_id=thread.id),
    }


def _render_support_thread_page(thread, *, viewer_mode):
    latest_reset_request = get_latest_reset_request_message(thread)
    latest_reset_payload = latest_reset_request.get_payload() if latest_reset_request else {}
    show_reset_links = viewer_mode in {"student", "guest"}
    serialized_messages = [
        _build_support_message_view(message, show_reset_links=show_reset_links)
        for message in thread.messages
    ]

    if viewer_mode == "admin":
        back_url = url_for("notifications.admin_support_threads")
        message_post_url = url_for("notifications.admin_support_message", thread_id=thread.id)
        grant_reset_url = url_for("notifications.grant_support_reset", thread_id=thread.id)
        page_title = f"Support {thread.student.nom_complet}"
    else:
        back_url = url_for("notifications.inbox") if current_user.is_authenticated else url_for("main.login")
        message_post_url = url_for("notifications.post_support_message")
        grant_reset_url = None
        page_title = "Espace support"

    return render_template(
        "notifications/support_thread.html",
        thread=thread,
        thread_summary=_support_thread_summary(thread),
        support_messages=serialized_messages,
        viewer_mode=viewer_mode,
        back_url=back_url,
        message_post_url=message_post_url,
        grant_reset_url=grant_reset_url,
        page_title=page_title,
        latest_reset_request=latest_reset_payload,
    )


@notifications_bp.route("/vapid-public-key")
@login_required
def vapid_public_key():
    return jsonify({"publicKey": current_app.config.get("VAPID_PUBLIC_KEY", "")})


@notifications_bp.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    _ensure_student()

    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    keys = payload.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return jsonify({"success": False, "error": "Subscription invalide."}), 400

    subscription = PushSubscription.query.filter_by(
        eleve_id=current_user.id,
        endpoint=endpoint,
    ).first()

    if subscription is None:
        subscription = PushSubscription(
            eleve_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            active=True,
        )
        db.session.add(subscription)
    else:
        subscription.p256dh = p256dh
        subscription.auth = auth
        subscription.active = True

    db.session.commit()
    return jsonify({"success": True})


@notifications_bp.route("/unsubscribe", methods=["POST"])
@login_required
def unsubscribe():
    _ensure_student()

    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    query = PushSubscription.query.filter_by(eleve_id=current_user.id, active=True)
    if endpoint:
        query = query.filter_by(endpoint=endpoint)

    subscriptions = query.all()
    for subscription in subscriptions:
        subscription.active = False

    db.session.commit()
    return jsonify({"success": True, "updated": len(subscriptions)})


@notifications_bp.route("/inbox")
@login_required
def inbox():
    ensure_notification_defaults()
    notifications = list_notifications_for_user(current_user.id, limit=50)
    unread_count = count_unread_notifications(current_user.id)
    badge_days = get_app_setting_int("badge_history_days", 30)
    badge_history = get_badge_history(current_user.id, days=badge_days) if current_user.role == "eleve" else []
    preferences = get_notification_preferences(current_user.id) if current_user.role == "eleve" else []
    support_threads = []
    if current_user.role == "admin":
        support_threads = (
            SupportThread.query.order_by(SupportThread.last_activity_at.desc(), SupportThread.id.desc())
            .limit(12)
            .all()
        )

    return render_template(
        "notifications/inbox.html",
        notifications=notifications,
        serialized_notifications=[serialize_notification(item) for item in notifications],
        unread_count=unread_count,
        badge_history=badge_history,
        badge_history_days=badge_days,
        notification_preferences=preferences,
        notification_stream_payload=get_notifications_stream_payload(current_user.id, limit=10),
        support_thread_summaries=[_support_thread_summary(thread) for thread in support_threads],
        support_thread_count=SupportThread.query.count() if current_user.role == "admin" else 0,
    )


@notifications_bp.route("/support")
def support_thread_guest():
    if not _has_logged_in_session():
        thread = _load_guest_support_thread()
        if thread is None:
            flash("Aucune demande recente a afficher. Recommencez depuis Mot de passe oublie.", "warning")
            return redirect(url_for("main.request_reset_password"))
        return _render_support_thread_page(thread, viewer_mode="guest")

    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("notifications.admin_support_threads"))
        if current_user.role != "eleve":
            abort(403)
        thread = get_or_create_support_thread(current_user)
        return _render_support_thread_page(thread, viewer_mode="student")
    abort(403)


@notifications_bp.route("/support/message", methods=["POST"])
def post_support_message():
    body = (request.form.get("message") or "").strip()
    if not body:
        flash("Ajoutez un message avant d envoyer.", "warning")
        return redirect(url_for("notifications.support_thread_guest"))

    if _has_logged_in_session() and current_user.is_authenticated:
        if current_user.role != "eleve":
            abort(403)
        thread = get_or_create_support_thread(current_user)
        author_user = current_user
    else:
        thread = _load_guest_support_thread()
        if thread is None:
            flash("Votre session d aide a expire. Recommencez la demande.", "warning")
            return redirect(url_for("main.request_reset_password"))
        author_user = thread.student

    message = create_support_message(
        thread,
        body=body,
        author_user=author_user,
        author_role="student",
        message_type="message",
    )
    notify_admins_about_support_thread(
        thread,
        title="Nouveau message support",
        message=f"{thread.student.nom_complet} a repondu dans le support.",
        event_key=f"support-message:{message.id}",
        payload={"message_id": message.id},
        app=current_app._get_current_object(),
    )
    flash("Message envoye.", "success")
    return redirect(url_for("notifications.support_thread_guest"))


@notifications_bp.route("/support/admin")
@login_required
@admin_required
def admin_support_threads():
    threads = SupportThread.query.order_by(SupportThread.last_activity_at.desc(), SupportThread.id.desc()).all()
    return render_template(
        "notifications/admin_support_threads.html",
        support_threads=[_support_thread_summary(thread) for thread in threads],
    )


@notifications_bp.route("/support/<int:thread_id>")
@login_required
@admin_required
def admin_support_thread(thread_id):
    thread = SupportThread.query.filter_by(id=thread_id).first_or_404()
    return _render_support_thread_page(thread, viewer_mode="admin")


@notifications_bp.route("/support/<int:thread_id>/message", methods=["POST"])
@login_required
@admin_required
def admin_support_message(thread_id):
    thread = SupportThread.query.filter_by(id=thread_id).first_or_404()
    body = (request.form.get("message") or "").strip()
    if not body:
        flash("Ajoutez un message avant d envoyer.", "warning")
        return redirect(url_for("notifications.admin_support_thread", thread_id=thread.id))

    create_support_message(
        thread,
        body=body,
        author_user=current_user,
        author_role="admin",
        message_type="message",
    )
    flash("Reponse envoyee.", "success")
    return redirect(url_for("notifications.admin_support_thread", thread_id=thread.id))


@notifications_bp.route("/support/<int:thread_id>/grant-reset", methods=["POST"])
@login_required
@admin_required
def grant_support_reset(thread_id):
    thread = SupportThread.query.filter_by(id=thread_id).first_or_404()
    latest_reset_request = get_latest_reset_request_message(thread)
    request_payload = latest_reset_request.get_payload() if latest_reset_request else {}

    grant = PasswordResetGrant(
        thread_id=thread.id,
        student_id=thread.student_id,
        granted_by_admin_id=current_user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        request_ip=request_payload.get("request_ip"),
        request_user_agent=request_payload.get("request_user_agent"),
    )
    db.session.add(grant)
    db.session.commit()

    create_support_message(
        thread,
        body="Lien de reinitialisation accorde pour 30 minutes.",
        author_role="system",
        message_type="reset_granted",
        payload={"grant_id": grant.id},
    )
    log_action(
        module="security",
        action="Lien reset accorde",
        level="WARNING",
        user_id=current_user.id,
        details=f"thread_id={thread.id}; student_id={thread.student_id}; grant_id={grant.id}",
    )
    flash("Lien accorde pour 30 minutes.", "success")
    return redirect(url_for("notifications.admin_support_thread", thread_id=thread.id))


@notifications_bp.route("/badges")
@login_required
def badges():
    return redirect(url_for("notifications.inbox", _anchor="badges"))


@notifications_bp.route("/preferences", methods=["POST"])
@login_required
def preferences():
    _ensure_student()
    ensure_notification_defaults()
    save_notification_preferences(current_user.id, request.form)
    flash("Preferences de notification mises a jour.", "success")
    return redirect(url_for("notifications.inbox", _anchor="preferences"))


@notifications_bp.route("/api/list")
@login_required
def api_list():
    limit = request.args.get("limit", default=20, type=int) or 20
    payload = get_notifications_stream_payload(current_user.id, limit=max(1, min(limit, 50)))
    return jsonify(payload)


@notifications_bp.route("/<int:notification_id>/go")
@login_required
def open_notification(notification_id):
    notification = mark_notification_read(current_user.id, notification_id)
    target = notification.cta_url or url_for("notifications.inbox")
    return redirect(target)


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def read_notification(notification_id):
    notification = mark_notification_read(current_user.id, notification_id)
    return jsonify(
        {
            "success": True,
            "notification": serialize_notification(notification),
            "unread_count": count_unread_notifications(current_user.id),
        }
    )


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def read_all():
    updated = mark_all_notifications_read(current_user.id)
    return jsonify(
        {
            "success": True,
            "updated": updated,
            "unread_count": count_unread_notifications(current_user.id),
        }
    )


@notifications_bp.route("/stream")
@login_required
def stream():
    if current_user.role != "eleve":
        abort(403)

    user_id = current_user.id

    def generate():
        while True:
            payload = get_notifications_stream_payload(user_id, limit=10)
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(15)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
