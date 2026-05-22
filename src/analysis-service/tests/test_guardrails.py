import json

import pytest

from app.models.analysis_result import (
    AnalysisResult,
    ScalabilityAssessment,
    ScalabilityLevel,
    SecurityFinding,
    SeverityLevel,
)
from app.services.guardrails import _extract_json, validate_and_parse_llm_response


class TestExtractJson:
    def test_extracts_raw_json(self):
        text = '{"components": ["A"], "risks": ["B"], "recommendations": ["C"]}'
        result = _extract_json(text)
        assert result is not None
        assert '"components"' in result

    def test_extracts_from_markdown_json_block(self):
        text = 'Análise:\n```json\n{"components": ["A"], "risks": ["B"], "recommendations": ["C"]}\n```'
        result = _extract_json(text)
        assert result is not None
        assert result.startswith("{")

    def test_extracts_from_plain_markdown_block(self):
        text = '```\n{"components": ["A"], "risks": ["B"], "recommendations": ["C"]}\n```'
        result = _extract_json(text)
        assert result is not None

    def test_returns_none_for_no_json(self):
        result = _extract_json("Sem nenhum JSON aqui")
        assert result is None


class TestValidateAndParseLLMResponse:
    def _make_valid_response(self, **overrides):
        base = {
            "components": ["API Gateway", "PostgreSQL Database"],
            "risks": ["Single Point of Failure no API Gateway sem redundância configurada"],
            "recommendations": ["Adicionar load balancer com failover automático entre instâncias"],
        }
        base.update(overrides)
        return json.dumps(base)

    def test_valid_basic_response(self):
        raw = self._make_valid_response()
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert "API Gateway" in result.components
        assert len(result.risks) == 1
        assert len(result.recommendations) == 1

    def test_valid_response_with_security_findings(self):
        raw = self._make_valid_response(
            security_findings=[
                {
                    "category": "authentication",
                    "description": "API Gateway não possui autenticação entre microserviços internos",
                    "severity": "high",
                    "affected_component": "API Gateway",
                }
            ]
        )
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert result.security_findings is not None
        assert len(result.security_findings) == 1
        assert result.security_findings[0].severity == SeverityLevel.HIGH

    def test_valid_response_with_scalability_assessments(self):
        raw = self._make_valid_response(
            scalability_assessments=[
                {
                    "component": "PostgreSQL Database",
                    "current_pattern": "vertical",
                    "bottleneck_risk": "Banco de dados relacional sem réplicas de leitura configuradas",
                    "recommendation": "Implementar réplicas de leitura e connection pooling com PgBouncer",
                }
            ]
        )
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert result.scalability_assessments is not None
        assert len(result.scalability_assessments) == 1
        assert result.scalability_assessments[0].current_pattern == ScalabilityLevel.VERTICAL

    def test_valid_full_response(self):
        raw = self._make_valid_response(
            security_findings=[
                {
                    "category": "encryption",
                    "description": "Comunicação entre serviços sem TLS configurado no cluster",
                    "severity": "critical",
                    "affected_component": "API Gateway",
                }
            ],
            scalability_assessments=[
                {
                    "component": "API Gateway",
                    "current_pattern": "horizontal",
                    "bottleneck_risk": "Sem auto-scaling configurado para picos de tráfego",
                    "recommendation": "Configurar HPA no Kubernetes com métricas de CPU e latência",
                }
            ],
            architecture_type="microservices",
        )
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert result.architecture_type == "microservices"
        assert result.overall_risk_score is not None
        assert result.overall_risk_score > 0

    def test_risk_score_computed_from_critical_findings(self):
        raw = self._make_valid_response(
            security_findings=[
                {
                    "category": "authentication",
                    "description": "Autenticação completamente ausente nas APIs públicas do sistema",
                    "severity": "critical",
                    "affected_component": "API Gateway",
                }
            ]
        )
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert result.overall_risk_score == 10.0

    def test_valid_response_in_markdown(self):
        base = self._make_valid_response()
        raw = f"```json\n{base}\n```"
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert "API Gateway" in result.components

    def test_missing_recommendations_returns_none(self):
        raw = '{"components": ["API Gateway"], "risks": ["SPOF no gateway sem redundância"]}'
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_missing_risks_returns_none(self):
        raw = '{"components": ["API Gateway"], "recommendations": ["Adicionar failover automático"]}'
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_empty_components_list_returns_none(self):
        raw = '{"components": [], "risks": ["SPOF no database"], "recommendations": ["Adicionar réplicas"]}'
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_blank_strings_are_filtered(self):
        raw = self._make_valid_response(components=["API Gateway", "  ", ""])
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert "" not in result.components
        assert "  " not in result.components
        assert "API Gateway" in result.components

    def test_invalid_json_returns_none(self):
        result, _ = validate_and_parse_llm_response("isso nao e json")
        assert result is None

    def test_non_object_json_returns_none(self):
        result, _ = validate_and_parse_llm_response('["lista", "invalida"]')
        assert result is None

    def test_items_are_truncated_to_max_length(self):
        long_item = "x" * 600
        raw = json.dumps({
            "components": [long_item],
            "risks": ["Single Point of Failure no API Gateway sem load balancer"],
            "recommendations": ["Implementar load balancer com health checks automáticos"],
        })
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert len(result.components[0]) == 500

    def test_list_exceeding_max_items_is_truncated(self):
        items = [f"Microservice-{i}" for i in range(25)]
        raw = json.dumps({
            "components": items,
            "risks": ["Acoplamento excessivo entre microserviços via chamadas HTTP síncronas"],
            "recommendations": ["Implementar event-driven architecture com message broker"],
        })
        result, _ = validate_and_parse_llm_response(raw)
        assert result is not None
        assert len(result.components) == 20

    def test_generic_component_rejected_by_heuristics(self):
        raw = json.dumps({
            "components": ["sistema"],
            "risks": ["Single Point of Failure no gateway sem failover"],
            "recommendations": ["Adicionar redundância e load balancer"],
        })
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_non_technical_risk_rejected(self):
        raw = json.dumps({
            "components": ["API Gateway", "Redis Cache"],
            "risks": ["pode dar problema"],
            "recommendations": ["Implementar monitoramento com alertas de latência"],
        })
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_non_actionable_recommendation_rejected(self):
        raw = json.dumps({
            "components": ["API Gateway", "Database"],
            "risks": ["Single Point of Failure no banco de dados primário"],
            "recommendations": ["está ruim"],
        })
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_duplicate_components_rejected(self):
        raw = json.dumps({
            "components": ["API Gateway", "API Gateway"],
            "risks": ["Timeout excessivo nas chamadas ao database sem circuit breaker"],
            "recommendations": ["Implementar circuit breaker pattern com fallback"],
        })
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None

    def test_invalid_security_category_rejected(self):
        raw = self._make_valid_response(
            security_findings=[
                {
                    "category": "invalid_category_xyz",
                    "description": "Descrição de vulnerabilidade fictícia sem sentido técnico",
                    "severity": "high",
                    "affected_component": "API Gateway",
                }
            ]
        )
        result, _ = validate_and_parse_llm_response(raw)
        assert result is None


class TestSecurityFindingModel:
    def test_valid_finding(self):
        f = SecurityFinding(
            category="authentication",
            description="API sem autenticação OAuth2 configurada entre serviços",
            severity=SeverityLevel.HIGH,
            affected_component="API Gateway",
        )
        assert f.category == "authentication"
        assert f.severity == SeverityLevel.HIGH

    def test_category_normalization(self):
        f = SecurityFinding(
            category="Single Point of Failure",
            description="Componente único sem réplica ou failover configurado",
            severity=SeverityLevel.CRITICAL,
            affected_component="Database Primary",
        )
        assert f.category == "single_point_of_failure"

    def test_invalid_category_raises(self):
        with pytest.raises(Exception):
            SecurityFinding(
                category="xyz_invalid",
                description="Descrição válida com mais de dez caracteres aqui",
                severity=SeverityLevel.LOW,
                affected_component="Component",
            )


class TestScalabilityAssessmentModel:
    def test_valid_assessment(self):
        a = ScalabilityAssessment(
            component="PostgreSQL Primary",
            current_pattern=ScalabilityLevel.VERTICAL,
            bottleneck_risk="Sem réplicas de leitura configuradas para distribuir queries",
            recommendation="Implementar read replicas com PgBouncer para connection pooling",
        )
        assert a.current_pattern == ScalabilityLevel.VERTICAL

    def test_empty_bottleneck_risk_raises(self):
        with pytest.raises(Exception):
            ScalabilityAssessment(
                component="Redis",
                current_pattern=ScalabilityLevel.HORIZONTAL,
                bottleneck_risk="",
                recommendation="Adicionar cluster Redis com sharding automático",
            )


class TestAnalysisResultRiskScore:
    def test_auto_computes_risk_score(self):
        result = AnalysisResult(
            components=["API Gateway", "Database"],
            risks=["Single Point of Failure no database sem réplica configurada"],
            recommendations=["Implementar read replicas e failover automático"],
            security_findings=[
                SecurityFinding(
                    category="encryption",
                    description="Comunicação interna sem TLS entre microserviços no cluster",
                    severity=SeverityLevel.MEDIUM,
                    affected_component="API Gateway",
                )
            ],
        )
        assert result.overall_risk_score == 5.0

    def test_no_findings_no_score(self):
        result = AnalysisResult(
            components=["API Gateway"],
            risks=["Timeout alto nas chamadas ao banco de dados sem circuit breaker"],
            recommendations=["Adicionar circuit breaker com fallback e retry configurado"],
        )
        assert result.overall_risk_score is None
