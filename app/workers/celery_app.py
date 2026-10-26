import os
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "workflow_pro_worker",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
    include=["app.workers.notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=False,
    task_publish_retry=False,
    broker_connection_timeout=1.0,
    broker_transport_options={
        "socket_timeout": 1.0,
        "socket_connect_timeout": 1.0,
        "max_connections": 1,
    },
    # Periodic beat schedule for approaching deadlines check (every 1 hour)
    beat_schedule={
        "check-approaching-deadlines-hourly": {
            "task": "app.workers.notifications.check_approaching_deadlines",
            "schedule": 3600.0,  # every 1 hour
        },
    },
)
