"""Targeted tests for the LLM advisory layer.

These tests verify the optional LLM integration works correctly:
- Without LLM_API_KEY: returns grounded explanations from decision records
- With LLM_API_KEY set (but no actual API call): returns fallback explanations
"""
import os
import pytest
from httpx import AsyncClient

from app.services.llm_advisor import LLMLayer, LLMExplanationRequest, LLMExplanationResponse


class TestLLMLayer:
    """Tests for the LLMLayer service class."""

    def test_layer_disabled_when_no_key(self):
        """LLMLayer should be disabled when LLM_API_KEY is not set."""
        # Ensure key is not set
        os.environ.pop("LLM_API_KEY", None)

        layer = LLMLayer()
        assert layer.key_set is False
        assert layer.enabled is False

    def test_layer_enabled_when_key_set(self):
        """LLMLayer should be enabled when LLM_API_KEY is set."""
        os.environ["LLM_API_KEY"] = "sk-test-key-12345"

        layer = LLMLayer()
        assert layer.key_set is True
        assert layer.enabled is True

    def test_build_grounded_explanation(self):
        """Grounded explanation should include decision data and references."""
        os.environ.pop("LLM_API_KEY", None)

        layer = LLMLayer()
        decision_data = {
            "id": "dec-abc123",
            "question": "Which database to use?",
            "answer": "PostgreSQL for production",
            "normalized_requirement": "Use PostgreSQL in production, SQLite in dev",
        }
        grounded = ["decision:dec-abc123", "requirement:Use PostgreSQL in production, SQLite in dev"]

        response = layer.explain(
            LLMExplanationRequest(decision_id="dec-abc123"),
            decision_data,
        )

        assert isinstance(response, LLMExplanationResponse)
        assert response.decision_id == "dec-abc123"
        assert "PostgreSQL" in response.explanation
        assert "requirement" in response.explanation.lower()
        assert "decision:dec-abc123" in response.grounded_in
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini"

    def test_grounded_includes_coverage_refs(self):
        """Grounded explanation should include PRD/issue/ref coverage references."""
        os.environ.pop("LLM_API_KEY", None)

        layer = LLMLayer()
        decision_data = {
            "id": "dec-xyz789",
            "question": "API design",
            "answer": "REST with JSON",
            "normalized_requirement": "Must be RESTful",
        }
        coverage_data = {
            "prd_refs": ["prd-1", "prd-2"],
            "issue_refs": ["issue-42"],
            "impl_refs": ["impl-api-001"],
            "verify_refs": ["verify-schema"],
            "is_fully_covered": True,
        }

        response = layer.explain(
            LLMExplanationRequest(decision_id="dec-xyz789"),
            decision_data,
            coverage_data,
        )

        assert len(response.grounded_in) >= 4
        assert "prd-1" in response.grounded_in
        assert "issue-42" in response.grounded_in
        assert "impl-api-001" in response.grounded_in
        assert "verify-schema" in response.grounded_in

    def test_fallback_when_key_set_but_no_api(self):
        """When key is set but no API call possible, should return fallback explanation."""
        os.environ["LLM_API_KEY"] = "sk-test-key-12345"

        layer = LLMLayer()
        decision_data = {
            "id": "dec-fallback",
            "question": "Feature priority",
            "answer": "High priority",
            "normalized_requirement": "Must ship by Q4",
        }

        response = layer.explain(
            LLMExplanationRequest(decision_id="dec-fallback"),
            decision_data,
        )

        assert isinstance(response, LLMExplanationResponse)
        assert response.decision_id == "dec-fallback"
        assert "Feature priority" in response.explanation
        assert "High priority" in response.explanation
        assert "Grounded in" in response.explanation
        # Even with key set, if no actual API integration, should fallback gracefully
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini"
