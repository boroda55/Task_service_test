import structlog
from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange
from app.core.config import settings

log = structlog.get_logger()

class TaskQueue:
    def __init__(self):
        self._conn: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def connect(self):
        self._conn = await connect_robust(settings.rabbitmq_url)
        self._channel = await self._conn.channel()
        self._exchange = await self._channel.declare_exchange(settings.TASKS_EXCHANGE, ExchangeType.DIRECT, durable=True)
        queue = await self._channel.declare_queue(settings.TASKS_QUEUE, durable=True)
        await queue.bind(self._exchange, routing_key=settings.TASKS_ROUTING_KEY)
        log.info("RabbitMQ connected")

    async def publish(self, task_id: int):
        if not self._exchange:
            raise RuntimeError("Queue not initialized")
        await self._exchange.publish(
            Message(body=str(task_id).encode(), delivery_mode=DeliveryMode.PERSISTENT),
            routing_key=settings.TASKS_ROUTING_KEY,
        )

    async def close(self):
        if self._conn and not self._conn.is_closed:
            await self._conn.close()

queue = TaskQueue()
