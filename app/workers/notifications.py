import logging
from datetime import datetime, timezone
from typing import Optional
from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email_notification(to_email: str, subject: str, message: str) -> bool:
    """Send an email notification via SMTP or simulated log."""
    logger.info(f"📧 [Email Notification] To: {to_email} | Subject: {subject}")
    logger.info(f"Content: {message}")
    # If SMTP is configured, real email can be sent here:
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = settings.EMAILS_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send real SMTP email: {e}")
            return False
    return True


@celery_app.task(name="app.workers.notifications.send_task_assigned_email_task")
def send_task_assigned_email_task(
    task_id: int,
    task_title: str,
    assignee_id: int,
    assigner_name: str,
) -> str:
    """Celery background task to send an assignment notification."""
    from app.db.session import SessionLocal
    from app.repositories.user_repository import UserRepository

    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        assignee = user_repo.get_by_id(assignee_id)
        if not assignee:
            return f"User {assignee_id} not found"

        subject = f"WorkFlow Pro: You have been assigned to '{task_title}'"
        body = (
            f"Hello {assignee.full_name or assignee.email},\n\n"
            f"{assigner_name} has assigned you to task #{task_id}: '{task_title}'.\n"
            f"Please log in to your WorkFlow Pro dashboard to review details and track your progress.\n\n"
            f"— The WorkFlow Pro Team"
        )
        send_email_notification(assignee.email, subject, body)
        return f"Assignment email sent to {assignee.email}"
    finally:
        db.close()


@celery_app.task(name="app.workers.notifications.check_approaching_deadlines")
def check_approaching_deadlines() -> str:
    """Periodic Celery beat task to remind users about approaching task deadlines within 24 hours."""
    from app.db.session import SessionLocal
    from app.repositories.task_repository import TaskRepository

    db = SessionLocal()
    try:
        task_repo = TaskRepository(db)
        urgent_tasks = task_repo.get_approaching_deadline_tasks(within_hours=24)
        reminders_sent = 0

        for task in urgent_tasks:
            if task.assignee:
                subject = f"⏰ WorkFlow Pro Deadline Reminder: '{task.title}' is due soon!"
                due_str = task.due_date.strftime("%Y-%m-%d %H:%M UTC") if task.due_date else "soon"
                body = (
                    f"Hello {task.assignee.full_name or task.assignee.email},\n\n"
                    f"This is a friendly reminder that task #{task.id} '{task.title}' is due on {due_str}.\n"
                    f"Status: {task.status.value.upper()} | Priority: {task.priority.value.upper()}\n\n"
                    f"— The WorkFlow Pro Team"
                )
                send_email_notification(task.assignee.email, subject, body)
                reminders_sent += 1

        return f"Successfully sent {reminders_sent} deadline reminders"
    finally:
        db.close()


def dispatch_task_assignment_notification(
    task_id: int,
    task_title: str,
    assignee_id: int,
    assigner_name: str,
) -> None:
    """Dispatches assignment notification to Celery or executes synchronously if broker is offline."""
    import os
    if os.environ.get("TESTING") == "true" or settings.ENVIRONMENT.lower() == "testing":
        logger.info(f"[Test Mode] Skipping Celery broker notification for task #{task_id}")
        return

    try:
        send_task_assigned_email_task.apply_async(
            kwargs={
                "task_id": task_id,
                "task_title": task_title,
                "assignee_id": assignee_id,
                "assigner_name": assigner_name,
            },
            retry=False,
            timeout=1,
        )
    except Exception as e:
        # Fallback to local synchronous or log execution so development is never blocked
        logger.info(f"Celery broker unavailable ({e}); running notification locally.")
        try:
            send_task_assigned_email_task(
                task_id=task_id,
                task_title=task_title,
                assignee_id=assignee_id,
                assigner_name=assigner_name,
            )
        except Exception as inner_e:
            logger.warning(f"Local notification error: {inner_e}")
