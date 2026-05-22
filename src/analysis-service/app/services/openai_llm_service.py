import logging
import time
from typing import List, Optional

import openai

from app.config import settings
from app.models.analysis_result import AnalysisResult
from app.services.guardrails import validate_and_parse_llm_response
from app.services.llm_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


class OpenAILLMService:
    def __init__(self, api_key: str = ""):
        key = api_key or settings.openai_api_key
        self._client = openai.OpenAI(api_key=key)
        self._model = settings.openai_model
        self.last_rejection_reason: str = ""
        logger.info(f"OpenAILLMService iniciado com modelo {self._model}")

    def analyze_images(
        self, images_base64: List[str], media_type: str = "image/png"
    ) -> Optional[AnalysisResult]:
        self.last_rejection_reason = ""
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"[OpenAI] Tentativa {attempt}/{MAX_RETRIES}")
            try:
                result = self._call(images_base64, media_type)
                if result is not None:
                    return result
                logger.warning(f"[OpenAI] Tentativa {attempt}: resposta inválida")
            except openai.RateLimitError:
                self.last_rejection_reason = "Limite de requisições da API atingido — tente novamente em alguns minutos"
                logger.warning(f"[OpenAI] Rate limit na tentativa {attempt}")
                time.sleep(RETRY_DELAY_SECONDS * attempt * 2)
            except openai.BadRequestError as e:
                self.last_rejection_reason = f"Requisição inválida para o modelo: {str(e)[:150]}"
                logger.error(f"[OpenAI] Bad request tentativa {attempt}: {e}")
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)
            except openai.APIStatusError as e:
                self.last_rejection_reason = f"Erro na API do provedor LLM: {e.status_code}"
                logger.error(f"[OpenAI] Erro API tentativa {attempt}: {e.status_code} - {e.message}")
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)
            except Exception as e:
                self.last_rejection_reason = f"Erro inesperado durante análise: {str(e)[:150]}"
                logger.error(f"[OpenAI] Erro inesperado tentativa {attempt}: {e}", exc_info=True)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

        logger.error("[OpenAI] Todas as tentativas falharam")
        return None

    def _call(self, images_base64: List[str], media_type: str) -> Optional[AnalysisResult]:
        user_content = []

        for i, img_b64 in enumerate(images_base64):
            if len(images_base64) > 1:
                user_content.append({"type": "text", "text": f"Página {i + 1} do diagrama:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{img_b64}", "detail": "high"},
            })

        user_content.append({
            "type": "text",
            "text": "Analise o diagrama de arquitetura acima e retorne o JSON estruturado conforme as regras.",
        })

        start = time.time()
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        raw_text = response.choices[0].message.content
        usage = response.usage
        logger.info(
            f"[OpenAI] {time.time() - start:.2f}s | "
            f"in={usage.prompt_tokens} out={usage.completion_tokens}"
        )

        result, reason = validate_and_parse_llm_response(raw_text)
        if result is None:
            self.last_rejection_reason = reason
            logger.error(
                "[OpenAI] Resposta do LLM rejeitada pelos guardrails\n"
                "  Motivo: %s\n"
                "  Resposta bruta (primeiros 500 chars): %s",
                reason, raw_text[:500],
            )
        return result
