import json
import secrets
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.orm import joinedload

from . import db
from .models import ActiveSession, SystemSetting


ACTIVE_SESSION_TOKEN_KEY = "active_session_token"
MAINTENANCE_MODE_KEY = "site_maintenance_mode"
SCHEDULER_STATUS_KEY = "scheduler_status"


def _utcnow():
    return datetime.utcnow()


def _serialize_datetime(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _deserialize_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def get_system_setting(key, default=None):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting is None:
        return default
    value = setting.get_value()
    return default if value is None else value


def set_system_setting(key, value):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting is None:
        setting = SystemSetting(key=key)
        db.session.add(setting)
    setting.set_value(value)
    return setting


def get_site_maintenance_payload():
    payload = get_system_setting(
        MAINTENANCE_MODE_KEY,
        default={"enabled": False, "updated_at": None, "updated_by": None, "note": None},
    )
    if not isinstance(payload, dict):
        payload = {"enabled": bool(payload)}
    payload.setdefault("enabled", False)
    payload.setdefault("updated_at", None)
    payload.setdefault("updated_by", None)
    payload.setdefault("note", None)
    return payload


def is_site_maintenance_enabled():
    return bool(get_site_maintenance_payload().get("enabled"))


def set_site_maintenance_mode(enabled, actor=None, note=None):
    payload = {
        "enabled": bool(enabled),
        "updated_at": _serialize_datetime(_utcnow()),
        "updated_by": getattr(actor, "id", None),
        "note": note or None,
    }
    set_system_setting(MAINTENANCE_MODE_KEY, payload)
    db.session.commit()
    return payload


def get_scheduler_status():
    payload = get_system_setting(
        SCHEDULER_STATUS_KEY,
        default={
            "job_id": "daily_push_reminders",
            "last_run_at": None,
            "last_success_at": None,
            "last_failure_at": None,
            "last_error": None,
            "last_result": None,
        },
    )
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("job_id", "daily_push_reminders")
    payload.setdefault("last_run_at", None)
    payload.setdefault("last_success_at", None)
    payload.setdefault("last_failure_at", None)
    payload.setdefault("last_error", None)
    payload.setdefault("last_result", None)
    return payload


def record_scheduler_run(*, success, result=None, error=None, job_id="daily_push_reminders"):
    payload = get_scheduler_status()
    now = _serialize_datetime(_utcnow())
    payload["job_id"] = job_id
    payload["last_run_at"] = now
    payload["last_result"] = result
    if success:
        payload["last_success_at"] = now
        payload["last_error"] = None
    else:
        payload["last_failure_at"] = now
        payload["last_error"] = error
    set_system_setting(SCHEDULER_STATUS_KEY, payload)
    db.session.commit()
    return payload


def create_active_session(user, *, ip_address=None, user_agent=None):
    session_record = ActiveSession(
        session_token=secrets.token_urlsafe(32),
        user_id=user.id,
        role_snapshot=user.role,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:500] or None,
        created_at=_utcnow(),
        last_seen_at=_utcnow(),
    )
    db.session.add(session_record)
    return session_record


def get_active_session_by_token(session_token):
    if not session_token:
        return None
    return ActiveSession.query.filter_by(session_token=session_token).first()


def touch_active_session(session_record, *, max_age_seconds=60):
    if session_record is None or session_record.revoked_at is not None:
        return False
    now = _utcnow()
    if session_record.last_seen_at and now - session_record.last_seen_at < timedelta(seconds=max_age_seconds):
        return False
    session_record.last_seen_at = now
    return True


def revoke_active_session_by_token(session_token, *, reason=None):
    session_record = get_active_session_by_token(session_token)
    if session_record is None or session_record.revoked_at is not None:
        return 0
    session_record.revoked_at = _utcnow()
    session_record.revoked_reason = reason or None
    return 1


def revoke_sessions_for_user(user_id, *, exclude_token=None, reason=None):
    query = ActiveSession.query.filter(
        ActiveSession.user_id == user_id,
        ActiveSession.revoked_at.is_(None),
    )
    if exclude_token:
        query = query.filter(ActiveSession.session_token != exclude_token)
    sessions = query.all()
    now = _utcnow()
    for session_record in sessions:
        session_record.revoked_at = now
        session_record.revoked_reason = reason or None
    return len(sessions)


def revoke_all_active_sessions(*, exclude_token=None, reason=None):
    query = ActiveSession.query.filter(ActiveSession.revoked_at.is_(None))
    if exclude_token:
        query = query.filter(ActiveSession.session_token != exclude_token)
    sessions = query.all()
    now = _utcnow()
    for session_record in sessions:
        session_record.revoked_at = now
        session_record.revoked_reason = reason or None
    return len(sessions)


def count_active_sessions():
    return ActiveSession.query.filter(ActiveSession.revoked_at.is_(None)).count()


def list_active_sessions():
    return (
        ActiveSession.query.options(joinedload(ActiveSession.user))
        .order_by(ActiveSession.last_seen_at.desc(), ActiveSession.id.desc())
        .all()
    )


def scheduler_status_with_datetimes():
    payload = get_scheduler_status()
    return {
        **payload,
        "last_run_at_dt": _deserialize_datetime(payload.get("last_run_at")),
        "last_success_at_dt": _deserialize_datetime(payload.get("last_success_at")),
        "last_failure_at_dt": _deserialize_datetime(payload.get("last_failure_at")),
    }


def config_diagnostic_snapshot():
    app = current_app._get_current_object()
    secret_key = app.config.get("SECRET_KEY")
    password_salt = app.config.get("SECURITY_PASSWORD_SALT")
    return {
        "debug": bool(app.debug),
        "testing": bool(app.testing),
        "session_cookie_secure": bool(app.config.get("SESSION_COOKIE_SECURE")),
        "session_cookie_samesite": app.config.get("SESSION_COOKIE_SAMESITE"),
        "preferred_url_scheme": app.config.get("PREFERRED_URL_SCHEME"),
        "secret_key_configured": bool(secret_key and secret_key != "dev-only-local-secret-key"),
        "password_salt_configured": bool(password_salt and password_salt != "dev-only-local-password-salt"),
        "database_uri": app.config.get("SQLALCHEMY_DATABASE_URI"),
        "log_file": app.config.get("LOG_FILE"),
        "backup_folder": app.config.get("BACKUP_FOLDER"),
        "cache_dir": app.config.get("CACHE_DIR"),
        "piper_cache_folder": app.config.get("PIPER_CACHE_FOLDER"),
        "media_root": app.config.get("MEDIA_ROOT"),
    }
