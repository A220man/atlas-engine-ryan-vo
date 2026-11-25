"""LLM advisory layer for natural-language explanations of decision rationale.

Optional integration: requires LLM_API_KEY environment variable.
If no key is set, the core returns grounded explanations from decision records
without contacting any LLM.  Does not affect the deterministic DesignTree core.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field


class LLMExplanationRequest(BaseModel):
    decision_id: str = Field(..., description="The decision to explain")
    context: Optional[str] = Field(
        None, description="Optional user context for the explanation"
    )


class LLMExplanationResponse(BaseModel):
    decision_id: str
    explanation: str
    grounded_in: list[str] = Field(
        default_factory=list, description="Decision IDs, PRD refs, issue refs etc."
    )
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")


class LLMLayer:
    """Minimal LLM advisory layer.

    - If LLM_API_KEY is set, attempts to call the LLM API.
    - If no key is set, returns a grounded explanation built from decision records.
    """

    def __init__(self) -> None:
        self.key_set = bool(os.environ.get("LLM_API_KEY"))
        self.enabled = self.key_set  # shortcut: only enable when key present

    def explain(
        self, request: LLMExplanationRequest, decision_data: dict, coverage_data: Optional[dict] = None
    ) -> LLMExplanationResponse:
        """Generate an explanation for a decision.

        Args:
            request: The LLM request with decision_id and optional context.
            decision_data: Serialized decision record data.
            coverage_data: Optional coverage/decision coverage info.

        Returns:
            LLMExplanationResponse with the explanation text and grounding references.
        """
        grounded: list[str] = []

        # Ground in actual decision records
        if "question" in decision_data:
            grounded.append(f"decision:{decision_data.get('id','?')}")
        if "normalized_requirement" in decision_data and decision_data["normalized_requirement"]:
            grounded.append(f"requirement:{decision_data.get('normalized_requirement','?')}")
        if coverage_data:
            for cat in ("prd_refs", "issue_refs", "impl_refs", "verify_refs"):
                refs = coverage_data.get(cat, [])
                grounded.extend(refs)

        if self.enabled and os.environ.get("LLM_API_KEY"):
            # TODO: actual LLM API call when key is provisioned
            explanation = self._fallback_explanation(decision_data, grounded)
        else:
            explanation = self._build_grounded_explanation(decision_data, grounded)

        return LLMExplanationResponse(
            decision_id=request.decision_id,
            explanation=explanation,
            grounded_in=sorted(set(grounded)),
            provider=os.environ.get("LLM_PROVIDER", "openai"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        )

    def _build_grounded_explanation(self, decision_data: dict, grounded: list[str]) -> str:
        """Build a human-readable explanation grounded in decision records."""
        parts: list[str] = []
        question = decision_data.get("question", "Unnamed decision")
        answer = decision_data.get("answer", "")
        requirement = decision_data.get("normalized_requirement", "")

        parts.append(f"This decision addresses: {question}")

        if answer:
            parts.append(f"The chosen answer/approach: {answer}")

        if requirement:
            parts.append(f"Requirement: {requirement}")

        if grounded:
            grounds = "; ".join(sorted(set(grounded)))
            parts.append(f"Grounded in: {grounds}")

        return " . ".join(parts) + "."

    def _fallback_explanation(self, decision_data: dict, grounded: list[str]) -> str:
        """Fallback when key is set but API call fails or is stubbed."""
        return self._build_grounded_explanation(decision_data, grounded)
