import json
import logging

import aio_pika

from app.publishers.event_publisher import EventPublisher
from app.services.llm_service import get_llm_service
from app.services.pdf_processor import image_to_base64, pdf_to_images
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Convenção MassTransit: exchange fanout por tipo de mensagem
EXCHANGE_NAME = "Shared.Events:AnalysisRequestedEvent"
QUEUE_NAME = "analysis-service"


class AnalysisRequestedConsumer:
    def __init__(self):
        self._storage = StorageService()
        self._llm = get_llm_service()
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def setup(self, channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractQueue:
        """Declara exchange, fila e faz o binding."""
        self._channel = channel
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange)
        logger.info(f"Fila '{QUEUE_NAME}' vinculada ao exchange '{EXCHANGE_NAME}'")
        return queue

    async def handle(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=True):
            try:
                envelope = json.loads(message.body.decode())
                # MassTransit envolve a mensagem em um envelope, campo "message"
                body = envelope.get("message", envelope)

                job_id = str(body["jobId"])
                file_path = body["filePath"]

                logger.info(f"AnalysisRequestedEvent recebido | job={job_id} | file={file_path}")

                publisher = EventPublisher(self._channel)
                await self._process(job_id, file_path, publisher)

            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"Mensagem malformada, descartando: {e}")
                # Não recoloca na fila — mensagem inválida
                raise aio_pika.exceptions.MessageProcessError("Mensagem malformada")

    async def _process(
        self, job_id: str, file_path: str, publisher: EventPublisher
    ) -> None:
        try:
            # 1. Baixa o arquivo do MinIO
            file_bytes, content_type = self._storage.download_file(file_path)

            # 2. Converte para imagem(ns) base64
            images_b64, media_type = self._prepare_images(file_bytes, content_type, file_path)

            # 3. Envia ao Claude com guardrails
            result = self._llm.analyze_images(images_b64, media_type)

            if result is None:
                await publisher.publish_failed(
                    job_id, "Análise LLM falhou após todas as tentativas"
                )
                return

            # 4. Publica sucesso
            await publisher.publish_completed(
                job_id=job_id,
                components=result.components,
                risks=result.risks,
                recommendations=result.recommendations,
            )

        except Exception as e:
            logger.error(f"Erro no processamento do job {job_id}: {e}", exc_info=True)
            await publisher.publish_failed(job_id, str(e)[:500])

    def _prepare_images(
        self, file_bytes: bytes, content_type: str, file_path: str
    ) -> tuple[list, str]:
        """Detecta o tipo do arquivo e retorna (list[base64], media_type)."""
        lower = file_path.lower()

        if "pdf" in content_type or lower.endswith(".pdf"):
            return pdf_to_images(file_bytes), "image/png"
        elif "png" in content_type or lower.endswith(".png"):
            return [image_to_base64(file_bytes)], "image/png"
        elif any(t in content_type for t in ("jpeg", "jpg")) or lower.endswith((".jpg", ".jpeg")):
            return [image_to_base64(file_bytes)], "image/jpeg"
        else:
            raise ValueError(f"Tipo de arquivo não suportado: {content_type} / {file_path}")
