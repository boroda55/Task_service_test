import asyncio
from datetime import datetime, timezone
import structlog
from aio_pika import IncomingMessage, connect_robust
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.models.task import Status, Task
from app.db.session import async_session, engine

setup_logging()
log = structlog.get_logger()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def _execute_task_logic(task_id: int) -> str:
    await asyncio.sleep(1)
    return "Успешно выполнено"

async def _process_task(task_id: int):
    async with async_session() as session:
        task = await session.get(Task, task_id)
        if not task:
            log.warning("Задача не найдена", task_id=task_id)
            return

        if task.status in (Status.IN_PROGRESS, Status.COMPLETED, Status.FAILED, Status.CANCELLED):
            log.info("Задача уже обрабатывается или завершена, пропуск", task_id=task_id, status=task.status.value)
            return

        try:
            task.status = Status.PENDING
            await session.commit()

            task.status = Status.IN_PROGRESS
            task.started_at = datetime.now(timezone.utc)
            await session.commit()

            result = await _execute_task_logic(task_id)

            task.status = Status.COMPLETED
            task.finished_at = datetime.now(timezone.utc)
            task.result = result
            await session.commit()
            log.info("Задача успешно обработана", task_id=task_id)

        except Exception as e:
            await session.rollback()
            task.status = Status.FAILED
            task.error = str(e)[:500]
            task.finished_at = datetime.now(timezone.utc)
            await session.commit()
            log.error("Задача завершена с ошибкой после повторных попыток", task_id=task_id, error=str(e))

async def handle_message(message: IncomingMessage):
    async with message.process(requeue=True):
        try:
            task_id = int(message.body.decode())
        except ValueError:
            log.error("Невалидный task_id в сообщении", body=message.body)
            return
        await _process_task(task_id)

async def main():
    conn = await connect_robust(settings.rabbitmq_url)
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=10)
    queue_obj = await channel.declare_queue(settings.TASKS_QUEUE, durable=True)

    log.info("Worker запущен (prefetch_count=10, retry enabled)")
    await queue_obj.consume(handle_message)

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await conn.close()
        await engine.dispose()
        log.info("Worker корректно остановлен")

if __name__ == "__main__":
    asyncio.run(main())
