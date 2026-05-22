import asyncio
import logging
import sys

import aio_pika

from app.config import settings
from app.consumers.analysis_requested_consumer import AnalysisRequestedConsumer

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","service":"AnalysisService","message":"%(message)s"}',
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

RABBITMQ_CONNECT_RETRIES = 15
RABBITMQ_RETRY_DELAY = 5


async def main() -> None:
    logger.info("Analysis Service starting | provider=%s | log_level=%s",
                settings.llm_provider, settings.log_level)

    rabbitmq_url = (
        f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
        f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}/"
    )

    connection = await _connect_with_retry(rabbitmq_url)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        consumer = AnalysisRequestedConsumer()
        queue = await consumer.setup(channel)

        logger.info("Analysis Service ready | listening for messages on queue")
        await queue.consume(consumer.handle)

        await asyncio.Future()


async def _connect_with_retry(url: str) -> aio_pika.abc.AbstractRobustConnection:
    for attempt in range(1, RABBITMQ_CONNECT_RETRIES + 1):
        try:
            connection = await aio_pika.connect_robust(url)
            logger.info("Connected to RabbitMQ | host=%s | attempt=%d",
                        settings.rabbitmq_host, attempt)
            return connection
        except Exception as e:
            logger.warning(
                "RabbitMQ connection attempt %d/%d failed: %s | retrying in %ds",
                attempt, RABBITMQ_CONNECT_RETRIES, e, RABBITMQ_RETRY_DELAY
            )
            if attempt == RABBITMQ_CONNECT_RETRIES:
                logger.error("Failed to connect to RabbitMQ after %d attempts", RABBITMQ_CONNECT_RETRIES)
                raise
            await asyncio.sleep(RABBITMQ_RETRY_DELAY)


if __name__ == "__main__":
    asyncio.run(main())
