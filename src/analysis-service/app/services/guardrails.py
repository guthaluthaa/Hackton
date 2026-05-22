import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from app.models.analysis_result import AnalysisResult

logger = logging.getLogger(__name__)

GENERIC_TERMS = {
    "sistema", "system", "componente", "component", "serviço", "service",
    "coisa", "thing", "algo", "something", "item", "objeto", "object",
}

SECURITY_KEYWORDS = {
    "autenticação", "authentication", "autorização", "authorization",
    "criptografia", "encryption", "ssl", "tls", "https", "oauth",
    "jwt", "token", "firewall", "waf", "cors", "xss", "csrf",
    "injection", "injeção", "vulnerability", "vulnerabilidade",
}

SCALABILITY_KEYWORDS = {
    "escala", "scale", "horizontal", "vertical", "load balancer",
    "balanceador", "cache", "redis", "réplica", "replica", "shard",
    "partition", "partição", "cluster", "queue", "fila", "async",
    "throughput", "latência", "latency", "bottleneck", "gargalo",
}

ARCHITECTURE_KEYWORDS = {
    "api gateway", "gateway", "microservice", "microserviço", "monolito",
    "monolith", "serverless", "lambda", "container", "kubernetes", "k8s",
    "docker", "message broker", "event bus", "database", "banco de dados",
    "cdn", "load balancer", "proxy", "reverse proxy", "cache",
}

MIN_COMPONENT_LENGTH = 3
MIN_RISK_DESCRIPTION_LENGTH = 15
MIN_RECOMMENDATION_LENGTH = 15


def validate_and_parse_llm_response(raw_response: str) -> tuple[Optional[AnalysisResult], str]:
    """Returns (result, rejection_reason). If result is not None, rejection_reason is empty."""
    logger.info("[GUARDRAIL] Starting LLM response validation")

    json_str = _extract_json(raw_response)
    if not json_str:
        reason = "Resposta do modelo não contém JSON válido — possível resposta truncada ou formato inesperado"
        logger.warning("[GUARDRAIL] JSON extraction failed — no valid JSON found in response")
        return None, reason
    logger.debug("[GUARDRAIL] JSON extracted successfully (%d chars)", len(json_str))

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        reason = f"JSON malformado na resposta do modelo: {e}"
        logger.warning("[GUARDRAIL] JSON parse failed: %s", e)
        return None, reason

    if not isinstance(data, dict):
        reason = "Resposta do modelo não é um objeto JSON válido"
        logger.warning("[GUARDRAIL] Response is not a JSON object")
        return None, reason

    required_fields = ["components", "risks", "recommendations"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        reason = f"Campos obrigatórios ausentes na resposta: {', '.join(missing)}"
        logger.warning("[GUARDRAIL] Missing required fields: %s", missing)
        return None, reason
    logger.debug("[GUARDRAIL] Required fields present")

    try:
        result = AnalysisResult(**data)
        logger.info("[GUARDRAIL] Pydantic validation passed")
    except ValidationError as e:
        reason = f"Estrutura da resposta inválida: {str(e)[:200]}"
        logger.warning("[GUARDRAIL] Pydantic validation failed: %s", e)
        return None, reason

    logger.info("[GUARDRAIL] Running heuristic checks")
    heuristic_issues = _apply_heuristics(result)
    if heuristic_issues:
        for issue in heuristic_issues:
            logger.warning("[GUARDRAIL][HEURISTIC] %s", issue)
        logger.warning("[GUARDRAIL] Rejected — %d heuristic violations", len(heuristic_issues))
        reason = f"Qualidade insuficiente na análise: {'; '.join(heuristic_issues[:3])}"
        return None, reason
    logger.info("[GUARDRAIL] Heuristic checks passed")

    logger.info("[GUARDRAIL] Running semantic adherence checks")
    semantic_issues = _check_semantic_adherence(result)
    if semantic_issues:
        for issue in semantic_issues:
            logger.warning("[GUARDRAIL][SEMANTIC] %s", issue)
        logger.info("[GUARDRAIL] Semantic warnings: %d (non-blocking)", len(semantic_issues))
    else:
        logger.info("[GUARDRAIL] Semantic adherence checks passed — full coverage")

    logger.info(
        "[GUARDRAIL] Validation complete | components=%d | risks=%d | "
        "recommendations=%d | security_findings=%d | "
        "scalability_assessments=%d | architecture_type=%s | risk_score=%s",
        len(result.components),
        len(result.risks),
        len(result.recommendations),
        len(result.security_findings or []),
        len(result.scalability_assessments or []),
        result.architecture_type,
        result.overall_risk_score,
    )
    return result, ""


def _apply_heuristics(result: AnalysisResult) -> list[str]:
    issues = []

    for comp in result.components:
        if len(comp) < MIN_COMPONENT_LENGTH:
            issues.append(f"Componente muito curto: '{comp}'")
        if comp.lower().strip() in GENERIC_TERMS:
            issues.append(f"Componente genérico demais: '{comp}'")

    for risk in result.risks:
        if len(risk) < MIN_RISK_DESCRIPTION_LENGTH:
            issues.append(f"Risco com descrição insuficiente: '{risk}'")
        if not _contains_technical_term(risk):
            issues.append(f"Risco não parece técnico: '{risk}'")

    for rec in result.recommendations:
        if len(rec) < MIN_RECOMMENDATION_LENGTH:
            issues.append(f"Recomendação muito curta: '{rec}'")
        if not _is_actionable(rec):
            issues.append(f"Recomendação não parece acionável: '{rec}'")

    if _has_duplicates(result.components):
        issues.append("Componentes duplicados detectados")

    if _has_duplicates(result.risks):
        issues.append("Riscos duplicados detectados")

    if result.security_findings:
        generic_affected = {"todos", "all", "sistema", "system", "geral", "global"}
        affected = {f.affected_component.lower() for f in result.security_findings}
        components_lower = {c.lower() for c in result.components}
        orphans = affected - components_lower
        orphans = {a for a in orphans if not any(g in a for g in generic_affected)}
        if orphans and len(orphans) == len(affected):
            issues.append(
                f"Nenhum componente de security_findings corresponde aos components listados"
            )

    return issues


def _check_semantic_adherence(result: AnalysisResult) -> list[str]:
    warnings = []

    has_security_context = any(
        any(kw in risk.lower() for kw in SECURITY_KEYWORDS)
        for risk in result.risks
    )
    if not has_security_context and not result.security_findings:
        warnings.append(
            "Análise não contém avaliação de segurança — "
            "considere verificar autenticação, criptografia e controle de acesso"
        )

    has_scalability_context = any(
        any(kw in rec.lower() for kw in SCALABILITY_KEYWORDS)
        for rec in result.recommendations
    )
    if not has_scalability_context and not result.scalability_assessments:
        warnings.append(
            "Análise não contém avaliação de escalabilidade — "
            "considere verificar gargalos e padrões de escala"
        )

    if result.security_findings:
        severities = [f.severity.value for f in result.security_findings]
        if "critical" in severities:
            critical_addressed = any(
                any(kw in rec.lower() for kw in ["urgente", "imediato", "critical", "crítico"])
                for rec in result.recommendations
            )
            if not critical_addressed:
                warnings.append(
                    "Findings críticos encontrados mas recomendações não refletem urgência"
                )

    if result.scalability_assessments:
        for assessment in result.scalability_assessments:
            comp_lower = assessment.component.lower()
            found = any(comp_lower in c.lower() or c.lower() in comp_lower for c in result.components)
            if not found:
                warnings.append(
                    f"Avaliação de escalabilidade para '{assessment.component}' "
                    f"não corresponde a nenhum componente listado"
                )

    return warnings


def _contains_technical_term(text: str) -> bool:
    technical_patterns = [
        r"\b(api|http|tcp|udp|ssl|tls|dns|sql|grpc|rest)\b",
        r"\b(single point|spof|bottleneck|gargalo|latência|latency)\b",
        r"\b(availability|disponibilidade|failover|redundância|redundancia)\b",
        r"\b(autenticação|authentication|autorização|authorization)\b",
        r"\b(database|banco|cache|queue|fila|broker|kafka|rabbitmq|redis)\b",
        r"\b(timeout|retry|retries|circuit.?breaker|rate.?limit|backoff)\b",
        r"\b(resili[eê]ncia|resilience|resiliency|redundância)\b",
        r"\b(vulnerabilidade|vulnerability|exposure|exposição)\b",
        r"\b(acoplamento|coupling|coesão|cohesion|dependência|dependency)\b",
        r"\b(criptograf|encrypt|decrypt|cifra|tls|https)\b",
        r"\b(serviços?|microserviço|microservice|gateway|proxy)\b",
        r"\b(replicação|replication|partição|partition|shard)\b",
        r"\b(observabilidade|monitoring|monitoramento|logging|tracing)\b",
        r"\b(escalabilidade|scalability|throughput|concorrência)\b",
        r"\b(firewall|waf|cors|xss|csrf|injection|injeção)\b",
        r"\b(cluster|container|kubernetes|docker|pod)\b",
        r"\b(indisponibilidade|downtime|outage|interrupção)\b",
        r"\b(falha|failure|crash|erro|error|exception)\b",
        r"\b(ponto.*(falha|failure)|point.*(failure|falha))\b",
        r"\b(backup|disaster.?recovery|dr|rpo|rto)\b",
        r"\b(load.?balancer|balanceamento|cdn|edge)\b",
        r"\b(deploy|ci.?cd|pipeline|rollback|canary|blue.?green)\b",
        r"\b(postgres|mysql|mongo|dynamo|cosmos)\b",
        r"\b(token|jwt|oauth|iam|rbac|abac|saml)\b",
        r"\b(dados|data|payload|request|response)\b",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in technical_patterns)


def _is_actionable(text: str) -> bool:
    actionable_patterns = [
        r"\b(adicionar|implementar|configurar|habilitar|desabilitar|aplicar)\b",
        r"\b(add|implement|configure|enable|disable|deploy|apply)\b",
        r"\b(migrar|separar|isolar|mover|refatorar|substituir)\b",
        r"\b(migrate|separate|isolate|move|refactor|replace)\b",
        r"\b(utilizar|usar|adotar|introduzir|criar|remover)\b",
        r"\b(use|adopt|introduce|create|remove|monitor)\b",
        r"\b(escalar|replicar|distribuir|particionar)\b",
        r"\b(garantir|assegurar|verificar|validar|revisar)\b",
        r"\b(ensure|verify|validate|review|audit|enforce)\b",
        r"\b(ajustar|otimizar|melhorar|atualizar|definir)\b",
        r"\b(adjust|optimize|improve|update|define|set.?up)\b",
        r"\b(considerar|avaliar|planejar|estabelecer)\b",
        r"\b(modificar|alterar|trocar|redesenhar|reestruturar|reduzir)\b",
        r"\b(modify|change|swap|redesign|restructure|reduce|increase)\b",
        r"\b(proteger|restringir|limitar|encapsular|centralizar)\b",
        r"\b(protect|restrict|limit|encapsulate|centralize|decouple)\b",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in actionable_patterns)


def _has_duplicates(items: list[str]) -> bool:
    normalized = [item.lower().strip() for item in items]
    return len(normalized) != len(set(normalized))


def _extract_json(text: str) -> Optional[str]:
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()

    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            candidate = text[start:end].strip()
            if candidate.startswith("{"):
                return candidate

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]

    return None
