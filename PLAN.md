# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

deterministic-frontier-ordering

## Roadmap

### deterministic-frontier-ordering — Deterministic frontier and pivot ordering

Status: done

Acceptance:
- Frontier decisions sorted by question_number for consistent API responses
- Pivot decisions sorted by descending pivot score, then by question_number for deterministic tiebreaker
- All existing tests pass

Implementation: `backend/app/services/decisions.py`, `backend/app/api/routes/decisions.py`

Tests: `backend/tests/test_decisions.py::test_frontier`

### continue-implementation — Continue implementation and resolve known failures

Status: done

Acceptance:
- Run checks, fix failures, and implement the next planned feature

Implementation: `backend/app/api/routes/decisions.py`, `backend/app/services/decisions.py`, `frontend/src/pages/GrillSession.tsx`, `frontend/src/components/DecisionCard.tsx`

Tests: `backend/tests/test_decisions.py::test_frontier`

### llm-advisory-layer — LLM advisory layer for decision explanations

Status: planned

Acceptance:
- Optional LLM integration for natural-language explanations of decision rationale
- Explanations grounded in actual decision records and PRD/issue links
- Configurable via environment variable (no LLM key required for offline core)
- Does not affect deterministic DesignTree core

Implementation: `backend/app/services/llm_advisor.py`, `backend/app/api/routes/advisor.py`

Tests: `backend/tests/test_advisor.py`

