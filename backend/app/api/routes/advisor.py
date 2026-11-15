from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_session
from app.services.llm_advisor import LLMLayer, LLMExplanationRequest, LLMExplanationResponse
from app.models.decision import Decision, DecisionStatus
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/advisor", tags=["advisor"])


class GetExplanationRequest(BaseModel):
    decision_id: str = Field(..., description="The decision to explain")
    context: Optional[str] = Field(
        None, description="Optional user context for the explanation"
    )


@router.post("/explanation", response_model=LLMExplanationResponse)
async def get_explanation(
    request: GetExplanationRequest,
    session: AsyncSession = Depends(get_session),
):
    """Get a natural-language explanation for a decision rationale.

    Optional LLM integration. If LLM_API_KEY is not set, returns a
    grounded explanation built from the decision record without contacting
    any LLM API.
    """
    from app.services.llm_advisor import LLMLayer

    service = LLMLayer()

    # Fetch the decision and its coverage
    result = await session.execute(
        select(Decision, DecisionCoverage).outerjoin(
            DecisionCoverage, Decision.id == DecisionCoverage.decision_id
        ).where(Decision.id == request.decision_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision, coverage = row
    decision_data = {
        "id": decision.id,
        "question": decision.question,
        "answer": decision.answer or "",
        "normalized_requirement": decision.normalized_requirement or "",
        "status": decision.status.value,
        "version": decision.version,
    }

    coverage_data: Optional[dict] = None
    if coverage:
        coverage_data = {
            "prd_refs": coverage.prd_refs or [],
            "issue_refs": coverage.issue_refs or [],
            "impl_refs": coverage.impl_refs or [],
            "verify_refs": coverage.verify_refs or [],
            "is_fully_covered": coverage.is_fully_covered,
        }

    explanation = service.explain(
        LLMExplanationRequest(decision_id=request.decision_id, context=request.context),
        decision_data,
        coverage_data if coverage_data.get("is_fully_covered") else None,
    )

    return explanation
