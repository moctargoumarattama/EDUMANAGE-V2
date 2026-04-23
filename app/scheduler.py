import os

from apscheduler.schedulers.background import BackgroundScheduler

from app import db
from app.maintenance_tools import record_scheduler_run
from app.notification_center import process_streak_risk_notifications
from app.utils import log_action


scheduler = BackgroundScheduler()


def envoyer_rappels_quotidiens(app):
    with app.app_context():
        try:
            stats = process_streak_risk_notifications(app)
            record_scheduler_run(success=True, result=stats)
            log_action(module="scheduler", action="Rappels quotidiens executes", level="INFO", details=str(stats))
            return stats
        except Exception as exc:
            db.session.rollback()
            record_scheduler_run(success=False, error=str(exc))
            log_action(module="scheduler", action="Echec rappels quotidiens", level="ERROR", details=str(exc))
            raise


def init_scheduler(app):
    should_start = not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if not should_start:
        return

    if scheduler.get_job("daily_push_reminders") is None:
        scheduler.add_job(
            envoyer_rappels_quotidiens,
            "cron",
            id="daily_push_reminders",
            hour=18,
            minute=0,
            args=[app],
            replace_existing=True,
        )

    if not scheduler.running:
        scheduler.start()
