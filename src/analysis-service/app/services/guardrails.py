import json
import logging
from typing import Optional

from app.models.analysis_result import AnalysisResult
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def validate_and_parse_llm_response(raw_response: str) -> Optional[AnalysisResult]:
    """
    Guardrail de saída: valida e parseia a resposta do LLM.
    Retorna AnalysisResult se válido, None caso contrário.
    """
    json_str = _extract_json(raw_response)
    if not json_str:
        logger.warning("Não foi possível extrair JSON da resposta do LLM")
        return None

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON inválido na resposta do LLM: {e}")
        return None

    if not isinstance(data, dict):
        logger.warning("Resposta do LLM não é um objeto JSON")
        return None

    required_fields = ["components", "risks", "recommendations"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        logger.warning(f"Campos obrigatórios ausentes: {missing}")
        return None

    try:
        result = AnalysisResult(**data)
        logger.info(
            f"Validação OK: {len(result.components)} componentes, "
            f"{len(result.risks)} riscos, {len(result.recommendations)} recomendações"
        )
        return result
    except ValidationError as e:
        logger.warning(f"Validação Pydantic falhou: {e}")
        return None


def _extract_json(text: str) -> Optional[str]:
    """Extrai bloco JSON do texto, suportando blocos markdown."""
    # Tenta markdown ```json
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()

    # Tenta markdown genérico ```
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            candidate = text[start:end].strip()
            if candidate.startswith("{"):
                return candidate

    # Tenta JSON direto
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]

    return None
