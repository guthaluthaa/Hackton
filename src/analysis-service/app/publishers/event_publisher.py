import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import aio_pika

from app.models.analysis_result import AnalysisResult

logger = logging.getLogger(__name__)

EXCHANGE_COMPLETED = "Shared.Events:AnalysisCompletedEvent"
EXCHANGE_FAILED = "Shared.Events:AnalysisFailedEvent"


class EventPublisher:
    def __init__(self, channel: aio_pika.abc.AbstractChannel):
        self._channel = channel

    async def publish_completed_from_result(
        self, job_id: str, result: AnalysisResult
    ) -> None:
        body = {
            "jobId": job_id,
            "status": "ANALYZED",
            "components": result.components,
            "risks": result.risks,
            "recommendations": result.recommendations,
            "securityFindings": [
                {
                    "category": f.category,
                    "description": f.description,
                    "severity": f.severity.value,
                    "affectedComponent": f.affected_component,
                }
                for f in (result.security_findings or [])
            ],
            "scalabilityAssessments": [
                {
                    "component": a.component,
                    "currentPattern": a.current_pattern.value,
                    "bottleneckRisk": a.bottleneck_risk,
                    "recommendation": a.recommendation,
                }
                for a in (result.scalability_assessments or [])
            ],
            "architectureType": result.architecture_type,
            "overallRiskScore": result.overall_risk_score,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(EXCHANGE_COMPLETED, body, "Shared.Events:AnalysisCompletedEvent")
        logger.info(
            f"AnalysisCompletedEvent publicado para job {job_id} | "
            f"components={len(result.components)} risks={len(result.risks)} "
            f"recommendations={len(result.recommendations)} "
            f"security_findings={len(result.security_findings or [])} "
            f"scalability={len(result.scalability_assessments or [])} "
            f"risk_score={result.overall_risk_score}"
        )

    async def publish_completed(
        self,
        job_id: str,
        components: List[str],
        risks: List[str],
        recommendations: List[str],
    ) -> None:
        body = {
            "jobId": job_id,
            "status": "ANALYZED",
            "components": components,
            "risks": risks,
            "recommendations": recommendations,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(EXCHANGE_COMPLETED, body, "Shared.Events:AnalysisCompletedEvent")
        logger.info(
            f"AnalysisCompletedEvent publicado para job {job_id} | "
            f"components={len(components)} risks={len(risks)} recommendations={len(recommendations)}"
        )

    async def publish_failed(self, job_id: str, reason: str) -> None:
        body = {
            "jobId": job_id,
            "reason": reason[:1000],
            "failedAt": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(EXCHANGE_FAILED, body, "Shared.Events:AnalysisFailedEvent")
        logger.warning(f"AnalysisFailedEvent publicado para job {job_id}: {reason[:200]}")

    async def _publish(
        self, exchange_name: str, body: dict, message_type: str
    ) -> None:
        """Publica mensagem no formato envelope do MassTransit."""
        envelope = {
            "messageId": str(uuid.uuid4()),
            "conversationId": str(uuid.uuid4()),
            "sourceAddress": "rabbitmq://rabbitmq/analysis-service",
            "messageType": [f"urn:message:{message_type}"],
            "message": body,
            "headers": {},
            "sentTime": datetime.now(timezone.utc).isoformat(),
            "host": {
                "machineName": "analysis-service",
                "processName": "analysis-service",
                "processId": 1,
                "assembly": "analysis-service",
                "assemblyVersion": "1.0.0",
                "frameworkVersion": "python-3.12",
                "massTransitVersion": "python-client",
                "operatingSystemVersion": "linux",
            },
        }

        exchange = await self._channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(envelope).encode(),
                content_type="application/vnd.masstransit+json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="",
        )
