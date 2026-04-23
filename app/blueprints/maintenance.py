import hashlib
import os
import shutil
from datetime import datetime, timedelta
from importlib import metadata

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import current_user, login_required
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import joinedload

from app import db
from app.authorization import maintenance_required
from app.maintenance_tools import (
    ACTIVE_SESSION_TOKEN_KEY,
    config_diagnostic_snapshot,
    count_active_sessions,
    get_scheduler_status,
    get_site_maintenance_payload,
    list_active_sessions,
    revoke_all_active_sessions,
    revoke_sessions_for_user,
    scheduler_status_with_datetimes,
    set_site_maintenance_mode,
)
from app.models import Log, PushSubscription
from app.scheduler import envoyer_rappels_quotidiens, scheduler
from app.utils import log_action


maintenance_bp = Blueprint("maintenance", __name__)

AUDIT_MODULES = {"maintenance", "security", "auth", "scheduler", "http"}


def _project_root():
    return os.path.abspath(os.path.join(current_app.root_path, os.pardir))


def _database_path():
    url = make_url(current_app.config["SQLALCHEMY_DATABASE_URI"])
    if url.drivername != "sqlite" or not url.database:
        return None
    return os.path.abspath(url.database)


def _current_migration():
    try:
        return db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        return None


def _migration_history():
    versions_dir = os.path.join(_project_root(), "migrations", "versions")
    history = []
    if not os.path.isdir(versions_dir):
        return history

    for filename in sorted(os.listdir(versions_dir)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue

        path = os.path.join(versions_dir, filename)
        revision = None
        down_revision = None
        title = filename
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith('"""') and title == filename:
                    candidate = stripped.strip('"').strip()
                    if candidate:
                        title = candidate
                elif stripped.startswith("revision ="):
                    revision = stripped.split("=", 1)[1].strip().strip("'\"")
                elif stripped.startswith("down_revision ="):
                    down_revision = stripped.split("=", 1)[1].strip().strip("'\"")
                if revision and down_revision is not None:
                    break

        history.append(
            {
                "filename": filename,
                "title": title,
                "revision": revision,
                "down_revision": down_revision,
            }
        )
    return list(reversed(history))


def _parse_date(value, *, end_of_day=False):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed + timedelta(days=1) if end_of_day else parsed


def _logs_query_with_filters(base_query=None):
    query = base_query or Log.query
    filters = {
        "level": (request.args.get("level") or "").strip().upper(),
        "module": (request.args.get("module") or "").strip(),
        "user_id": (request.args.get("user_id") or "").strip(),
        "ip": (request.args.get("ip") or "").strip(),
        "start_date": (request.args.get("start_date") or "").strip(),
        "end_date": (request.args.get("end_date") or "").strip(),
    }

    if filters["level"]:
        query = query.filter(Log.level == filters["level"])
    if filters["module"]:
        query = query.filter(Log.module.ilike(f"%{filters['module']}%"))
    if filters["user_id"].isdigit():
        query = query.filter(Log.utilisateur_id == int(filters["user_id"]))
    if filters["ip"]:
        query = query.filter(Log.ip_address.ilike(f"%{filters['ip']}%"))

    start_date = _parse_date(filters["start_date"])
    end_date = _parse_date(filters["end_date"], end_of_day=True)
    if start_date is not None:
        query = query.filter(Log.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(Log.timestamp < end_date)

    return query.order_by(Log.timestamp.desc(), Log.id.desc()), filters


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _list_backups():
    backup_dir = current_app.config["BACKUP_FOLDER"]
    os.makedirs(backup_dir, exist_ok=True)
    backups = []
    for entry in os.scandir(backup_dir):
        if not entry.is_file():
            continue
        stat = entry.stat()
        backups.append(
            {
                "name": entry.name,
                "path": entry.path,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
                "sha256": _sha256_file(entry.path),
            }
        )
    backups.sort(key=lambda item: item["modified_at"], reverse=True)
    return backups


def _apply_backup_retention():
    retention_count = max(1, int(current_app.config.get("BACKUP_RETENTION_COUNT", 10)))
    backups = _list_backups()
    deleted = []
    for backup in backups[retention_count:]:
        os.remove(backup["path"])
        deleted.append(backup["name"])
    return deleted


def _cache_zone_paths():
    return {
        "app": {
            "label": "Cache applicatif",
            "path": current_app.config.get("CACHE_DIR"),
        },
        "piper": {
            "label": "Cache audio Piper",
            "path": current_app.config.get("PIPER_CACHE_FOLDER"),
        },
    }


def _purge_directory_contents(path):
    if not path or not os.path.isdir(path):
        return 0

    removed = 0
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
        else:
            os.remove(entry_path)
        removed += 1
    return removed


def _disk_usage_snapshot():
    instance_dir = current_app.instance_path
    try:
        usage = shutil.disk_usage(instance_dir)
    except FileNotFoundError:
        return None
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
    }


def _latest_critical_error():
    return (
        Log.query.filter(Log.level.in_(["ERROR", "CRITICAL"]))
        .order_by(Log.timestamp.desc(), Log.id.desc())
        .first()
    )


def _recent_error_metrics():
    since = datetime.utcnow() - timedelta(hours=1)
    recent_errors = Log.query.filter(Log.timestamp >= since, Log.level.in_(["ERROR", "CRITICAL"])).count()
    http_500 = Log.query.filter(Log.timestamp >= since, Log.module == "http", Log.level == "ERROR").count()
    return {
        "since": since,
        "recent_errors": recent_errors,
        "http_500_count": http_500,
        "error_spike": recent_errors >= int(current_app.config.get("ERROR_SPIKE_THRESHOLD", 5)),
    }


def _backups_health_snapshot():
    backups = _list_backups()
    latest_backup = backups[0] if backups else None
    alert_hours = int(current_app.config.get("BACKUP_ALERT_HOURS", 48))
    is_stale = True
    if latest_backup is not None:
        is_stale = datetime.utcnow() - latest_backup["modified_at"] > timedelta(hours=alert_hours)
    return {
        "entries": backups,
        "latest": latest_backup,
        "alert_hours": alert_hours,
        "is_stale": is_stale,
        "retention_count": int(current_app.config.get("BACKUP_RETENTION_COUNT", 10)),
    }


def _maintenance_dashboard_context():
    db_path = _database_path()
    db_size = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0
    jobs = scheduler.get_jobs() if scheduler.running else []
    next_job = jobs[0].next_run_time if jobs else None
    started_at = current_app.config.get("STARTED_AT")
    uptime = datetime.utcnow() - started_at if started_at else None
    scheduler_status = scheduler_status_with_datetimes()
    backup_state = _backups_health_snapshot()
    error_metrics = _recent_error_metrics()

    return {
        "flask_version": metadata.version("flask"),
        "debug": bool(current_app.debug),
        "uptime": uptime,
        "db_path": db_path,
        "db_size": db_size,
        "table_count": len(inspect(db.engine).get_table_names()),
        "migration": _current_migration(),
        "scheduler_running": scheduler.running,
        "scheduler_next_run": next_job,
        "scheduler_status": scheduler_status,
        "active_push_subscriptions": PushSubscription.query.filter_by(active=True).count(),
        "recent_error_count": error_metrics["recent_errors"],
        "recent_http_500_count": error_metrics["http_500_count"],
        "error_spike": error_metrics["error_spike"],
        "version": current_app.config.get("VERSION", "1.0.0"),
        "maintenance_mode": get_site_maintenance_payload(),
        "active_sessions_count": count_active_sessions(),
        "latest_critical_error": _latest_critical_error(),
        "backups": backup_state,
    }


@maintenance_bp.route("/")
@login_required
@maintenance_required
def dashboard():
    return render_template("maintenance/dashboard.html", stats=_maintenance_dashboard_context())


@maintenance_bp.route("/logs")
@login_required
@maintenance_required
def logs():
    query, filters = _logs_query_with_filters()
    entries = query.limit(200).all()
    return render_template(
        "maintenance/logs.html",
        logs=entries,
        filters=filters,
        latest_critical_error=_latest_critical_error(),
    )


@maintenance_bp.route("/audit")
@login_required
@maintenance_required
def audit():
    query, filters = _logs_query_with_filters(Log.query.filter(Log.module.in_(AUDIT_MODULES)))
    entries = query.limit(200).all()
    return render_template("maintenance/audit.html", logs=entries, filters=filters)


@maintenance_bp.route("/migrations")
@login_required
@maintenance_required
def migrations():
    return render_template(
        "maintenance/migrations.html",
        current_revision=_current_migration(),
        migrations=_migration_history(),
    )


@maintenance_bp.route("/backups")
@login_required
@maintenance_required
def backups():
    return render_template("maintenance/backups.html", backup_state=_backups_health_snapshot())


@maintenance_bp.route("/diagnostic")
@login_required
@maintenance_required
def diagnostic():
    diagnostics = config_diagnostic_snapshot()
    diagnostics["disk_usage"] = _disk_usage_snapshot()
    return render_template("maintenance/diagnostic.html", diagnostics=diagnostics)


@maintenance_bp.route("/sessions")
@login_required
@maintenance_required
def active_sessions():
    return render_template(
        "maintenance/sessions.html",
        sessions=list_active_sessions(),
        active_sessions_count=count_active_sessions(),
    )


@maintenance_bp.route("/backup", methods=["POST"])
@login_required
@maintenance_required
def backup():
    db_path = _database_path()
    if not db_path or not os.path.exists(db_path):
        log_action(module="maintenance", action="Backup impossible", level="ERROR", user_id=current_user.id)
        return jsonify({"success": False, "message": "Base de donnees introuvable."}), 404

    os.makedirs(current_app.config["BACKUP_FOLDER"], exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"ecole_{timestamp}.db"
    destination = os.path.join(current_app.config["BACKUP_FOLDER"], filename)
    shutil.copy2(db_path, destination)
    deleted = _apply_backup_retention()
    size = os.path.getsize(destination)
    checksum = _sha256_file(destination)
    log_action(
        module="maintenance",
        action="Backup cree",
        level="INFO",
        user_id=current_user.id,
        details=f"filename={filename}; size={size}; deleted={','.join(deleted) or 'none'}",
    )
    return jsonify(
        {
            "success": True,
            "filename": filename,
            "size": size,
            "sha256": checksum,
            "deleted": deleted,
        }
    )


@maintenance_bp.route("/mode", methods=["POST"])
@login_required
@maintenance_required
def toggle_maintenance_mode():
    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled"))
    note = (payload.get("note") or "").strip() or None
    state = set_site_maintenance_mode(enabled, actor=current_user, note=note)
    log_action(
        module="maintenance",
        action="Mode maintenance active" if enabled else "Mode maintenance desactive",
        level="WARNING" if enabled else "INFO",
        user_id=current_user.id,
        details=f"note={note or '-'}",
    )
    return jsonify({"success": True, "maintenance_mode": state})


@maintenance_bp.route("/vider-cache", methods=["POST"])
@login_required
@maintenance_required
def vider_cache():
    payload = request.get_json(silent=True) or {}
    zone = (payload.get("zone") or "all").strip().lower()
    zones = _cache_zone_paths()

    if zone == "all":
        removed = {key: _purge_directory_contents(data["path"]) for key, data in zones.items()}
        total = sum(removed.values())
    elif zone in zones:
        removed = {zone: _purge_directory_contents(zones[zone]["path"])}
        total = removed[zone]
    else:
        return jsonify({"success": False, "message": "Zone de cache inconnue."}), 400

    log_action(
        module="maintenance",
        action="Cache purge",
        level="INFO",
        user_id=current_user.id,
        details=f"zone={zone}; removed={total}",
    )
    return jsonify({"success": True, "zone": zone, "removed": removed, "total_removed": total})


@maintenance_bp.route("/sessions/user/<int:user_id>/revoke", methods=["POST"])
@login_required
@maintenance_required
def revoke_user_sessions(user_id):
    revoked = revoke_sessions_for_user(user_id, reason="maintenance-revoke-user")
    db.session.commit()
    log_action(
        module="maintenance",
        action="Sessions utilisateur revoquees",
        level="WARNING",
        user_id=current_user.id,
        details=f"target_user_id={user_id}; revoked={revoked}",
    )
    return jsonify({"success": True, "revoked": revoked, "user_id": user_id})


@maintenance_bp.route("/sessions/revoke-all", methods=["POST"])
@login_required
@maintenance_required
def revoke_all_sessions():
    payload = request.get_json(silent=True) or {}
    include_current = bool(payload.get("include_current"))
    exclude_token = None if include_current else session.get(ACTIVE_SESSION_TOKEN_KEY)
    revoked = revoke_all_active_sessions(
        exclude_token=exclude_token,
        reason="maintenance-revoke-all",
    )
    db.session.commit()
    log_action(
        module="maintenance",
        action="Toutes les sessions revoquees" if include_current else "Sessions revoquees sauf courante",
        level="WARNING",
        user_id=current_user.id,
        details=f"revoked={revoked}",
    )
    return jsonify({"success": True, "revoked": revoked, "include_current": include_current})


@maintenance_bp.route("/push-subscriptions")
@login_required
@maintenance_required
def push_subscriptions():
    subscriptions = (
        PushSubscription.query.options(joinedload(PushSubscription.eleve))
        .order_by(PushSubscription.date_creation.desc())
        .all()
    )
    return render_template("maintenance/push_subscriptions.html", subscriptions=subscriptions)


@maintenance_bp.route("/push-subscriptions/<int:subscription_id>/desactiver", methods=["POST"])
@login_required
@maintenance_required
def desactiver_push_subscription(subscription_id):
    subscription = PushSubscription.query.filter_by(id=subscription_id).first_or_404()
    subscription.active = False
    db.session.commit()
    log_action(
        module="maintenance",
        action="Push subscription desactivee",
        level="INFO",
        user_id=current_user.id,
        details=f"subscription_id={subscription.id}; eleve_id={subscription.eleve_id}",
    )
    return jsonify({"success": True, "subscription_id": subscription.id})


@maintenance_bp.route("/envoyer-rappel", methods=["POST"])
@login_required
@maintenance_required
def envoyer_rappel():
    stats = envoyer_rappels_quotidiens(current_app._get_current_object())
    log_action(
        module="maintenance",
        action="Rappel manuel envoye",
        level="INFO",
        user_id=current_user.id,
        details=f"stats={stats}",
    )
    return jsonify(stats)


@maintenance_bp.route("/sante")
@login_required
@maintenance_required
def sante():
    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    scheduler_state = get_scheduler_status()
    return jsonify(
        {
            "status": "ok" if db_status == "ok" else "degraded",
            "db": db_status,
            "scheduler": "running" if scheduler.running else "stopped",
            "scheduler_state": scheduler_state,
            "maintenance_mode": get_site_maintenance_payload(),
            "version": current_app.config.get("VERSION", "1.0.0"),
        }
    )
