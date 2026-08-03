"""Celery worker application configuration."""

from __future__ import annotations

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "text_to_sql_workers",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.celery.task_always_eager,
    worker_concurrency=settings.celery.worker_concurrency,
)
