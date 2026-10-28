from celery import Celery

from research_quest_api.settings import Settings, get_settings


def create_celery_app(settings: Settings | None = None) -> Celery:
    resolved_settings = settings or get_settings()
    app = Celery(
        "research_quest",
        broker=resolved_settings.celery_broker_url,
    )
    app.conf.update(
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
        enable_utc=True,
        result_backend=None,
        task_acks_late=True,
        task_default_queue="research_quest.tasks",
        task_reject_on_worker_lost=True,
        task_serializer="json",
        timezone="UTC",
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = create_celery_app()
