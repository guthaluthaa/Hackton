import json
import logging
import time

import aio_pika

from app.publishers.event_publisher import EventPublisher
from app.services.llm_service import get_llm_service
from app.services.pdf_processor import image_to_base64, pdf_to_images
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "Shared.Events:AnalysisRequestedEvent"
QUEUE_NAME = "analysis-service"


class AnalysisRequestedConsumer:
    def __init__(self):
        self._storage = StorageService()
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def setup(self, channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractQueue:
        self._channel = channel
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange)
        logger.info("Queue '%s' bound to exchange '%s'", QUEUE_NAME, EXCHANGE_NAME)
        return queue

    async def handle(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=True):
            try:
                envelope = json.loads(message.body.decode())
                body = envelope.get("message", envelope)

                job_id = str(body["jobId"])
                file_path = body["filePath"]
                llm_provider = body.get("llmProvider", "")
                llm_api_key = body.get("llmApiKey", "")

                logger.info(
                    "========== NOVA ANÁLISE RECEBIDA ==========\n"
                    "  Job ID:    %s\n"
                    "  Arquivo:   %s\n"
                    "  Provedor:  %s\n"
                    "============================================",
                    job_id, file_path, llm_provider or "(env default)",
                )

                publisher = EventPublisher(self._channel)
                await self._process(job_id, file_path, llm_provider, llm_api_key, publisher)

            except (KeyError, json.JSONDecodeError) as e:
                logger.error("[PIPELINE ERROR] Malformed message: %s", e)
                raise aio_pika.exceptions.MessageProcessError("Malformed message")

    async def _process(
        self, job_id: str, file_path: str, llm_provider: str, llm_api_key: str, publisher: EventPublisher
    ) -> None:
        total_start = time.perf_counter()
        try:
            # Step 0: Initialize LLM with user-provided or fallback credentials
            effective_provider = (llm_provider or "env-default").lower()
            logger.info(
                "[STEP 0/5] Initializing LLM | job_id=%s | provider=%s | key_provided=%s",
                job_id, effective_provider, bool(llm_api_key),
            )
            llm = get_llm_service(provider=llm_provider, api_key=llm_api_key)

            # Step 1: Download
            logger.info("[STEP 1/5] Downloading file from storage | job_id=%s", job_id)
            download_start = time.perf_counter()
            file_bytes, content_type = self._storage.download_file(file_path)
            download_ms = (time.perf_counter() - download_start) * 1000
            logger.info(
                "[STEP 1/5] Download complete | job_id=%s | size=%d bytes | "
                "content_type=%s | elapsed=%.0fms",
                job_id, len(file_bytes), content_type, download_ms,
            )

            # Step 2: Image conversion
            logger.info("[STEP 2/5] Converting file to images | job_id=%s", job_id)
            convert_start = time.perf_counter()
            images_b64, media_type = self._prepare_images(file_bytes, content_type, file_path)
            convert_ms = (time.perf_counter() - convert_start) * 1000
            logger.info(
                "[STEP 2/5] Conversion complete | job_id=%s | pages=%d | "
                "media_type=%s | elapsed=%.0fms",
                job_id, len(images_b64), media_type, convert_ms,
            )

            # Step 3: LLM analysis
            logger.info(
                "[IA INÍCIO] Enviando diagrama para análise com IA | job_id=%s | provider=%s | imagens=%d",
                job_id, effective_provider, len(images_b64),
            )
            llm_start = time.perf_counter()
            result = llm.analyze_images(images_b64, media_type)
            llm_ms = (time.perf_counter() - llm_start) * 1000
            if result is not None:
                logger.info(
                    "[IA CONCLUÍDA] Análise da IA finalizada com sucesso | job_id=%s | tempo=%.0fms",
                    job_id, llm_ms,
                )
            else:
                llm_error = getattr(llm, "last_rejection_reason", "") or "Resposta inválida ou vazia"
                logger.error(
                    "[IA ERRO] A IA retornou uma resposta inválida | job_id=%s | tempo=%.0fms | erro=%s",
                    job_id, llm_ms, llm_error,
                )

            if result is None:
                failure_reason = getattr(llm, "last_rejection_reason", "") or "Não foi possível gerar uma análise válida para o diagrama fornecido"
                await publisher.publish_failed(job_id, failure_reason)
                total_ms = (time.perf_counter() - total_start) * 1000
                logger.warning(
                    "========== ANÁLISE FALHOU ==========\n"
                    "  Job ID:  %s\n"
                    "  Motivo:  %s\n"
                    "  Tempo:   %.0fms\n"
                    "====================================",
                    job_id, failure_reason, total_ms,
                )
                return

            # Step 4: Post-validation logging (heuristics + semantic already applied in guardrails)
            logger.info(
                "[STEP 4/5] Validation passed | job_id=%s | "
                "components=%d | risks=%d | recommendations=%d | "
                "security_findings=%d | scalability_assessments=%d | "
                "architecture_type=%s | risk_score=%s",
                job_id,
                len(result.components),
                len(result.risks),
                len(result.recommendations),
                len(result.security_findings or []),
                len(result.scalability_assessments or []),
                result.architecture_type,
                result.overall_risk_score,
            )

            # Step 5: Publish result
            logger.info("[STEP 5/5] Publishing AnalysisCompletedEvent | job_id=%s", job_id)
            await publisher.publish_completed_from_result(job_id, result)

            total_ms = (time.perf_counter() - total_start) * 1000
            logger.info(
                "========== ANÁLISE CONCLUÍDA COM SUCESSO ==========\n"
                "  Job ID:          %s\n"
                "  Componentes:     %d identificados\n"
                "  Riscos:          %d encontrados\n"
                "  Recomendações:   %d geradas\n"
                "  Segurança:       %d findings\n"
                "  Escalabilidade:  %d avaliações\n"
                "  Arquitetura:     %s\n"
                "  Risk Score:      %s/10\n"
                "  Tempo total:     %.0fms (download=%.0fms | conversão=%.0fms | IA=%.0fms)\n"
                "====================================================",
                job_id,
                len(result.components),
                len(result.risks),
                len(result.recommendations),
                len(result.security_findings or []),
                len(result.scalability_assessments or []),
                result.architecture_type,
                result.overall_risk_score,
                total_ms, download_ms, convert_ms, llm_ms,
            )

        except Exception as e:
            total_ms = (time.perf_counter() - total_start) * 1000
            logger.error(
                "[PIPELINE ERROR] job_id=%s | total_elapsed=%.0fms | error=%s",
                job_id, total_ms, e, exc_info=True,
            )
            await publisher.publish_failed(job_id, str(e)[:500])

    def _prepare_images(
        self, file_bytes: bytes, content_type: str, file_path: str
    ) -> tuple[list, str]:
        lower = file_path.lower()

        if "pdf" in content_type or lower.endswith(".pdf"):
            return pdf_to_images(file_bytes), "image/png"
        elif "png" in content_type or lower.endswith(".png"):
            return [image_to_base64(file_bytes)], "image/png"
        elif any(t in content_type for t in ("jpeg", "jpg")) or lower.endswith((".jpg", ".jpeg")):
            return [image_to_base64(file_bytes)], "image/jpeg"
        else:
            raise ValueError(f"Unsupported file type: {content_type} / {file_path}")
