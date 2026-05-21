import pytest

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
    def test_valid_response(self):
        raw = '{"components": ["API Gateway", "Database"], "risks": ["SPOF"], "recommendations": ["Add redundancy"]}'
        result = validate_and_parse_llm_response(raw)
        assert result is not None
        assert "API Gateway" in result.components
        assert "SPOF" in result.risks
        assert "Add redundancy" in result.recommendations

    def test_valid_response_in_markdown(self):
        raw = '```json\n{"components": ["Load Balancer"], "risks": ["Sem SSL"], "recommendations": ["Habilitar HTTPS"]}\n```'
        result = validate_and_parse_llm_response(raw)
        assert result is not None
        assert "Load Balancer" in result.components

    def test_missing_recommendations_returns_none(self):
        raw = '{"components": ["A"], "risks": ["B"]}'
        result = validate_and_parse_llm_response(raw)
        assert result is None

    def test_missing_risks_returns_none(self):
        raw = '{"components": ["A"], "recommendations": ["C"]}'
        result = validate_and_parse_llm_response(raw)
        assert result is None

    def test_empty_components_list_returns_none(self):
        raw = '{"components": [], "risks": ["B"], "recommendations": ["C"]}'
        result = validate_and_parse_llm_response(raw)
        assert result is None

    def test_blank_strings_are_filtered(self):
        raw = '{"components": ["API Gateway", "  ", ""], "risks": ["SPOF"], "recommendations": ["Fix it"]}'
        result = validate_and_parse_llm_response(raw)
        assert result is not None
        assert "" not in result.components
        assert "  " not in result.components
        assert "API Gateway" in result.components

    def test_invalid_json_returns_none(self):
        result = validate_and_parse_llm_response("isso nao e json")
        assert result is None

    def test_non_object_json_returns_none(self):
        result = validate_and_parse_llm_response('["lista", "invalida"]')
        assert result is None

    def test_items_are_truncated_to_max_length(self):
        long_item = "x" * 600
        raw = f'{{"components": ["{long_item}"], "risks": ["B"], "recommendations": ["C"]}}'
        result = validate_and_parse_llm_response(raw)
        assert result is not None
        assert len(result.components[0]) == 500

    def test_list_exceeding_max_items_is_truncated(self):
        items = [f"item{i}" for i in range(25)]
        import json
        raw = json.dumps({"components": items, "risks": ["B"], "recommendations": ["C"]})
        result = validate_and_parse_llm_response(raw)
        assert result is not None
        assert len(result.components) == 20
