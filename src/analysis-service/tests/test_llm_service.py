import pytest
from unittest.mock import MagicMock, patch

from app.models.analysis_result import AnalysisResult
from app.services.llm_service import LLMService


def _make_mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage.input_tokens = 100
    response.usage.output_tokens = 50
    return response


VALID_JSON = '{"components": ["API Gateway", "PostgreSQL"], "risks": ["SPOF"], "recommendations": ["Add replica"]}'


class TestLLMService:
    @patch("app.services.llm_service.anthropic.Anthropic")
    def test_analyze_images_returns_result_on_valid_response(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(VALID_JSON)

        service = LLMService()
        result = service.analyze_images(["base64imagedata=="], "image/png")

        assert result is not None
        assert isinstance(result, AnalysisResult)
        assert "API Gateway" in result.components
        assert "SPOF" in result.risks

    @patch("app.services.llm_service.anthropic.Anthropic")
    def test_analyze_images_retries_on_invalid_response(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Primeiras 2 respostas inválidas, 3ª válida
        mock_client.messages.create.side_effect = [
            _make_mock_response("resposta inválida"),
            _make_mock_response("ainda inválido"),
            _make_mock_response(VALID_JSON),
        ]

        service = LLMService()
        with patch("app.services.llm_service.time.sleep"):
            result = service.analyze_images(["img=="], "image/png")

        assert result is not None
        assert mock_client.messages.create.call_count == 3

    @patch("app.services.llm_service.anthropic.Anthropic")
    def test_analyze_images_returns_none_after_max_retries(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response("sempre inválido")

        service = LLMService()
        with patch("app.services.llm_service.time.sleep"):
            result = service.analyze_images(["img=="], "image/png")

        assert result is None
        assert mock_client.messages.create.call_count == 3  # MAX_RETRIES

    @patch("app.services.llm_service.anthropic.Anthropic")
    def test_analyze_multiple_images_builds_correct_content(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(VALID_JSON)

        service = LLMService()
        service.analyze_images(["page1==", "page2=="], "image/png")

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        content = messages[0]["content"]

        # 2 imagens + 2 labels de página + 1 instrução final = 5 itens
        assert len(content) == 5
        text_items = [c["text"] for c in content if c["type"] == "text"]
        assert any("Página 1" in t for t in text_items)
        assert any("Página 2" in t for t in text_items)
