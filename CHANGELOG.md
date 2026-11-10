# Changelog

## 1.6.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.5.1 — work-in-progress checkpoint

### Added
- Deterministic frontier ordering by question_number for consistent API responses
- Deterministic pivot ordering with score then question_number tiebreaker

### Fixed
- Frontier and pivot lists now have stable ordering regardless of insertion order

### Tests
- All 38 backend tests pass
- All 6 frontend tests pass

## 1.5.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.4.0 — work-in-progress checkpoint

### Added
- Comprehensive test for decision frontier endpoint (`test_frontier`)
- Settled decision tracking in GrillSession UI with checkbox on each DecisionCard
- Frontier query now respects user-selected settled decisions

### Fixed
- `FrontierRequest` model no longer requires `session_id` in body (comes from path parameter)
- Decision creation in tests now properly flushes to generate ULIDs before using them as dependencies

### Tests
- All 38 backend tests pass (including new `test_frontier`)
- All 6 frontend tests pass
- Frontend builds successfully

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [1.0.0] - 2025-10-13

### Added
- Core skeleton: FastAPI + React decision traceability engine
- `DesignTree` class with frontier detection and pivot scoring
- DecisionCoverage model with bidirectional link tracking (PRD, issue, implementation, verification)
- `/api/v1/frontier` endpoint returning frontier decisions with prerequisites
- `/api/v1/issues/unblocked` endpoint returning unblocked issues
- OIDC authentication via Keycloak with backend-managed sessions, HttpOnly SameSite cookies
- Role-based authorization: viewer < operator < analyst < admin
- `create_session_token`, `decode_session_token`, `get_or_create_user`, `validate_token` auth service
- Dashboard, GrillSession, PrdView, IssueBoard, Verification, Settings, Callback, Login frontend pages
- Typed ApiClient (axios) with `withCredentials: true` for cookie-based auth
- React context-based auth provider with in-memory token management
- 31 backend tests (FastAPI + httpx + async SQLAlchemy)
- 6 frontend tests (vitest + testing-library)
- Docker Compose with backend, frontend, Keycloak, PostgreSQL, pgAdmin
- CI workflow: backend tests, frontend type-check + tests, Docker builds, prettier check

### Fixed
- `Backend: missing `aiosqlite` and `PyJWT` in requirements.txt; removed duplicate `httpx`
- `Backend: missing `UniqueConstraint` import in prd.py
- `Backend: auth.py had delayed imports (NameError); `require_role` was async (FastAPI can't use async dependency factory)
- `Backend: `JSONVariant` class couldn't compile under SQLite; replaced with dialect-agnostic `JSON` type
- `Backend: `ulid-py` 1.x `ULID()` requires buffer arg; changed all imports to `from ulid import new as ULID`
- `Backend: duplicate `__table_args__` index in user.py conflicted with column `index=True`
- `Backend: `DecisionCoverage` list columns silently skipped appends; switched to `MutableList.as_mutable(JSON)`
- `Backend: `flag_modified` not called for in-place `acceptance_criteria` dict mutations in `complete_issue`
- `Backend: `complete_issue` endpoint returned 200 instead of 201 (creates new decision)
- `Backend: 4 handlers didn't create `DecisionCoverage` if missing before updating refs
- `Backend: `get_unblocked_issues` excluded DONE issues from closed_ids computation
- `Backend: `CoverageReport.add_decision` mapped wrong category→attribute names
- `Backend: frontier endpoint always returned empty prerequisites; now reads from `depends_on`
- `Backend: `test_get_unblocked_issues` used `id=None` for issue3 (fixed with explicit ULID)
- Frontend: `Layout.tsx` had JSX syntax error (`<ryandtvo@gmail.com>`) and used `<Outlet />` instead of `{children}`
- Frontend: `Callback.tsx` had `useState` import at bottom, unused `storedNonce`, passed access_token to `setUser`
- Frontend: `useAuth.tsx` stored session token in localStorage (security violation); removed; token is now in-memory only
- Frontend: all TypeScript errors (unused imports, untyped callbacks, missing `vite-env.d.ts`)
- Frontend: `PrdView.tsx` had unclosed function brace

### Security
- Removed localStorage token storage; auth relies on HttpOnly SameSite cookies
- OIDC state/nonce/code_verifier stored in sessionStorage (transient, cleared post-redirect)
- API client uses `withCredentials: true` for cookie-based auth

### Infrastructure
- Added `.gitignore`, `.env.example`, `portfolio.json`, `LICENSE`, `compose.yaml`
- Added `backend/Dockerfile` + `.dockerignore`
- Added `frontend/Dockerfile` + `.dockerignore` + `nginx.conf`
- Added `.github/workflows/ci.yml` with test, build, and Docker build jobs
- Added `backend/pyproject.toml` with project metadata
- Added `README.md` with install/run/test instructions and architecture diagram
