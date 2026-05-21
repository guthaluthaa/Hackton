import logging
from typing import Protocol, List, Optional

from app.config import settings
from app.models.analysis_result import AnalysisResult

logger = logging.getLogger(__name__)


class LLMServiceProtocol(Protocol):
    def analyze_images(
        self, images_base64: List[str], media_type: str
    ) -> Optional[AnalysisResult]: ...


def get_llm_service() -> LLMServiceProtocol:
    """
    Factory: retorna o serviço LLM configurado via LLM_PROVIDER.
    Valores aceitos: "claude" (padrão) ou "openai".
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from app.services.openai_llm_service import OpenAILLMService
        return OpenAILLMService()

    if provider == "claude":
        from app.services.claude_llm_service import ClaudeLLMService
        return ClaudeLLMService()

    raise ValueError(
        f"LLM_PROVIDER inválido: '{provider}'. Use 'claude' ou 'openai'."
    )


# Mantém compatibilidade com código que importa LLMService diretamente
LLMService = get_llm_service
