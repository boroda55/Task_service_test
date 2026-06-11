import asyncio
from datetime import datetime, timezone
import structlog
from aio_pika import IncomingMessage, connect_robust

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.models.task import Status
from app.db.session import async_session, engine
from app.repositories.task_repository import TaskRepository

setup_logging()
log = structlog.get_logger()


async def _process_task(session, repo: TaskRepository, task_id: int):
    """
    Обрабатывает задачу, используя слой репозитория для работы с БД.
    Это обеспечивает единую архитектуру и упрощает тестирование.
    """
    task = await repo.get_by_id(task_id)

    if not task:
        log.warning("Задача не найдена в БД", task_id=task_id)
        return

    if task.status in (Status.IN_PROGRESS, Status.COMPLETED, Status.FAILED, Status.CANCELLED):
        log.info("Задача уже обрабатывается или завершена, пропуск", task_id=task_id, status=task.status.value)
        return

    try:
        task.status = Status.PENDING
        await repo.update(task)
        await session.commit()

        task.status = Status.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc)
        await repo.update(task)
        await session.commit()

        await asyncio.sleep(1)
        task.result = "Успешно выполнено"

        task.status = Status.COMPLETED
        task.finished_at = datetime.now(timezone.utc)
        await repo.update(task)
        await session.commit()

        log.info("Задача успешно обработана", task_id=task_id)

    except Exception as e:
        await session.rollback()
        task.status = Status.FAILED
        task.error = str(e)[:500]
        task.finished_at = datetime.now(timezone.utc)
        await repo.update(task)
        await session.commit()

        log.error("Задача завершена с ошибкой", task_id=task_id, error=str(e))


async def handle_message(message: IncomingMessage):
    """
    Обработчик сообщений из RabbitMQ.
    Использует requeue=False для предотвращения бесконечного цикла (Poison Pill).
    """
    try:
        task_id = int(message.body.decode())
    except ValueError:
        log.error("Невалидный формат task_id в сообщении", body=message.body)
        await message.reject(requeue=False)
        return

    async with message.process(requeue=False):
        async with async_session() as session:
            repo = TaskRepository(session)
            await _process_task(session, repo, task_id)


async def main():
    conn = await connect_robust(settings.rabbitmq_url)
    channel = await conn.channel()


    await channel.set_qos(prefetch_count=10)

    queue_obj = await channel.declare_queue(settings.TASKS_QUEUE, durable=True)

    log.info("Worker запущен (prefetch_count=10, requeue=False для предотвращения бесконечных циклов)")
    await queue_obj.consume(handle_message)

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await conn.close()
        await engine.dispose()
        log.info("Worker остановлен")


if __name__ == "__main__":
    asyncio.run(main())