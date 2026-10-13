# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-skeleton

## Roadmap

### core-skeleton — Core FastAPI/React skeleton with auth and database

Status: done

Acceptance:
- FastAPI app runs with SQLite backend
- React + TypeScript + Vite frontend builds
- OIDC Keycloak authentication configured
- Docker compose with backend, frontend, Keycloak, PostgreSQL
- Backend and frontend tests pass

Implementation: `backend/app/main.py`, `backend/app/api/routes/{auth,decisions,issues,prds,verifications,health}.py`, `backend/app/models/{decision,issue,prd,verification,user}.py`, `backend/app/services/auth.py`, `frontend/src/api/client.ts`, `frontend/src/app.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/hooks/useAuth.tsx`, `frontend/src/pages/{Dashboard,GrillSession,PrdView,IssueBoard,Verification,Settings,Callback,Login}.tsx`

Tests: `backend/tests/test_auth.py`, `backend/tests/test_decisions.py`, `backend/tests/test_prds.py`, `backend/tests/test_issues.py`, `backend/tests/test_verifications.py`, `frontend/src/pages/__tests__/Dashboard.test.tsx`, `frontend/src/pages/__tests__/Settings.test.tsx`, `frontend/src/components/__tests__/Layout.test.tsx`

### decision-ledger — Decision ledger for traceable requirements

Status: planned

Acceptance:
- Append-only decision records with stable IDs
- Normalized testable requirements extracted from answers
- Explicit constraints tracked per decision
- Version history for revised answers
- Coverage check: all decisions referenced in PRD/issues

### grill-workflow — Grill workflow with frontier gate and pivot ordering

Status: planned

Acceptance:
- Design tree with dependency tracking
- Frontier gate: only ask settled prerequisite questions
- Pivot ordering: tree-reshaping decisions first
- Incremental Q/A numbering
- Assumptions surfaced with veto capability
- Explicit confirmed exit gate

### prd-generation — PRD generation with decision mapping

Status: planned

Acceptance:
- PRD maps every decision record to user stories
- Decisions, constraints, acceptance evidence linked
- Stale reference detection for revised decisions
- Implementation-heavy design artifact option (to-design)

### issue-tracking — Issue tracking with completion signals

Status: planned

Acceptance:
- GitHub/GitLab issue creation from PRD
- Local markdown ticket support
- Completion step: resolution comment + close
- Frontier unblocking on ticket close
- PR-based workflow deferral

### verification — Implementation verification with evidence

Status: planned

Acceptance:
- Evidence linked per decision ID
- Acceptance criteria verification tracking
- Coverage report: decisions vs verified
- Gap warnings for missing evidence

