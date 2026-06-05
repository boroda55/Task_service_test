from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from app.api.v1.endpoints import health, tasks
from app.core.logging import setup_logging
from app.services.queue import queue

setup_logging()
log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await queue.connect()
    except Exception as e:
        log.warning("RabbitMQ недоступен", error=str(e))
    yield
    await queue.close()

app = FastAPI(title="Task Service", version="1.0.0", lifespan=lifespan)
app.include_router(tasks.router)
app.include_router(health.router)
