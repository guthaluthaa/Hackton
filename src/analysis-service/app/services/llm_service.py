import logging
from typing import Protocol, List, Optional

from app.config import settings
from app.models.analysis_result import AnalysisResult

logger = logging.getLogger(__name__)


class LLMServiceProtocol(Protocol):
    def analyze_images(
        self, images_base64: List[str], media_type: str
    ) -> Optional[AnalysisResult]: ...


def get_llm_service(provider: str = "", api_key: str = "") -> LLMServiceProtocol:
    """
    Factory: retorna o serviço LLM configurado.
    Se provider/api_key forem fornecidos (via request do usuário), usa-os.
    Caso contrário, faz fallback para as variáveis de ambiente.
    """
    effective_provider = (provider or settings.llm_provider).lower()

    if effective_provider == "openai":
        from app.services.openai_llm_service import OpenAILLMService
        return OpenAILLMService(api_key=api_key or settings.openai_api_key)

    if effective_provider == "claude":
        from app.services.claude_llm_service import ClaudeLLMService
        return ClaudeLLMService(api_key=api_key or settings.claude_api_key)

    raise ValueError(
        f"LLM_PROVIDER inválido: '{effective_provider}'. Use 'claude' ou 'openai'."
    )


# Mantém compatibilidade com código que importa LLMService diretamente
LLMService = get_llm_service
