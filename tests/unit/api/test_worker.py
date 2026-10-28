from research_quest_api.settings import Settings
from research_quest_api.worker import create_celery_app


def test_celery_app_uses_rabbitmq_and_safe_serializers() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://test:test@localhost/test",
        celery_broker_url="amqp://worker:secret@rabbitmq:5672//",
    )

    app = create_celery_app(settings)

    assert app.conf.broker_url == settings.celery_broker_url
    assert app.conf.task_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert app.conf.result_backend is None
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1
