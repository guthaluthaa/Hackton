import asyncio
import logging
import sys

import aio_pika

from app.config import settings
from app.consumers.analysis_requested_consumer import AnalysisRequestedConsumer

# Logging estruturado (JSON-like) para consumo pelo Seq ou qualquer agregador
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

RABBITMQ_CONNECT_RETRIES = 15
RABBITMQ_RETRY_DELAY = 5


async def main() -> None:
    logger.info("Analysis Service iniciando...")

    rabbitmq_url = (
        f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}"
        f"@{settings.rabbitmq_host}:{settings.rabbitmq_port}/"
    )

    connection = await _connect_with_retry(rabbitmq_url)

    async with connection:
        channel = await connection.channel()
        # Processa 1 mensagem por vez para controlar carga de chamadas à API
        await channel.set_qos(prefetch_count=1)

        consumer = AnalysisRequestedConsumer()
        queue = await consumer.setup(channel)

        logger.info("Analysis Service pronto. Aguardando mensagens...")
        await queue.consume(consumer.handle)

        # Mantém o serviço rodando
        await asyncio.Future()


async def _connect_with_retry(url: str) -> aio_pika.abc.AbstractRobustConnection:
    for attempt in range(1, RABBITMQ_CONNECT_RETRIES + 1):
        try:
            connection = await aio_pika.connect_robust(url)
            logger.info("Conectado ao RabbitMQ")
            return connection
        except Exception as e:
            logger.warning(
                f"Tentativa {attempt}/{RABBITMQ_CONNECT_RETRIES} falhou: {e}. "
                f"Aguardando {RABBITMQ_RETRY_DELAY}s..."
            )
            if attempt == RABBITMQ_CONNECT_RETRIES:
                logger.error("Não foi possível conectar ao RabbitMQ após todas as tentativas")
                raise
            await asyncio.sleep(RABBITMQ_RETRY_DELAY)


if __name__ == "__main__":
    asyncio.run(main())
