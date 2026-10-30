# Atlas Engine — Ryan Vo | AI & Machine Learning

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


Atlas Engine is a **decision-traceability engine** that closes the
`grill → PRD → issues → implementation → verification` gap: every resolved
design decision must survive intact through the artifacts that depend on it, and
any drift must be detectable. Its domain engine is a deterministic
**design-tree reasoner** — a `DesignTree` that performs frontier-gated grilling
(only decisions whose prerequisites are all settled are ready to ask) and
pivot-first ordering (ranking tree-reshaping decisions highest) — so the next
question to resolve is never a guess. An optional, operator-configured LLM layer
can later surface advisory natural-language explanations grounded in actual
records; the offline reasoning core requires no LLM key. Intended for engineers
who need auditable, non-lossy reasoning across a full implementation workflow.

> Work in progress. See `PLAN.md` and `STATUS.md` before use. Not all planned
> features are implemented; the LLM advisory layer is not yet wired up.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vite/React)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Dashboard   │  │  Grill Room  │  │ PRD / Issues │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│           │              │                  │           │
│           ▼              ▼                  ▼           │
│         API Client (axios, withCredentials)              │
└────────────────────────┬──────────────────────────────────┘
                         │ HttpOnly cookie (SameSite=Lax)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Design   │  │   PRD    │  │  Issues  │  │ Verif.   │ │
│  │ Decisions │  │ Mappings │  │ & Block- │  │ Evidence │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│         │              │              │              │   │
│         └────────── DesignTree ──────────┘              │
│                  Frontier + Coverage                     │
│         │                                              │
│         ▼                                              │
│  ┌──────────────────────────────────┐                  │
│  │        PostgreSQL / SQLite        │                  │
│  │   Async SQLAlchemy models         │                  │
│  └──────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────┐
  │   Keycloak  │  OIDC SSO (SAML broker optional)
  └─────────────┘
```

## AI/ML evaluation

**Component under evaluation:** the `DesignTree` reasoning engine
(`backend/app/services/decisions.py`) — frontier gating and pivot ranking over a
decision dependency graph.

**Data provenance:** decisions are created via `POST /decisions` with a ULID
primary key and an optional `constraints.depends_on` list of prerequisite
decision IDs (the graph edges). The tree is materialized from persisted records
per `session_id` (SQLite in dev, PostgreSQL in prod). No external data source or
LLM key is involved in the offline core.

**Baseline (deterministic):**
- `get_frontier(settled)` returns only decisions whose prerequisite set is a
  subset of `settled`.
- `get_pivots(frontier)` orders frontier decisions by descending downstream
  dependency count (pivots rank first).
- Dependency cycles do not crash (`_get_downstream` uses a visited set).

**Reproducible command:**

```bash
PYTHONPATH=backend .venv/bin/python - <<'PY'
from app.services.decisions import DesignTree
t = DesignTree()
t.add_node("q1", {"q": "What database?"}, [])
t.add_node("q2", {"q": "Connection pooling?"}, ["q1"])
t.add_node("q3", {"q": "Migrate data?"}, ["q1"])
t.add_node("q4", {"q": "Backfill strategy?"}, ["q3"])
print("frontier(none settled):", sorted(t.get_frontier(set())))
print("frontier(q1 settled):", sorted(t.get_frontier({"q1"})))
print("pivots(q1 settled):", t.get_pivots(t.get_frontier({"q1"})))
PY
```

**Measured results (this run):**
```
frontier(none settled): ['q1']
frontier(q1 settled): ['q2', 'q3']
pivots(q1 settled): ['q3', 'q2']
```
`q3` ranks before `q2` because it has a downstream dependent (`q4`), confirming
pivot-first ordering. Full correctness is also asserted by the backend test
suite: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q`
(37 tests passing).

**Failure cases / limitations:**
- The reasoner assumes a DAG; cyclic inputs are handled safely (no crash) but
  produce no meaningful ordering.
- Coverage reporting flags per-decision gaps (missing PRD/issue/impl/verification
  reference) and PRD→decision version staleness, but does not yet auto-warn on
  orphaned decisions (a decision referenced by no PRD/issue).
- The LLM advisory layer is not yet implemented; explanations are produced by the
  deterministic engine only.

## Prerequisites

- Python 3.12+
- Node.js 24+
- Docker + Docker Compose (optional, for full stack)

## Quick Start (Local Development)

### Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

### Full Stack (Docker Compose)

```bash
cp .env.example .env
# Edit .env with your OIDC credentials
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Keycloak: http://localhost:8080
- PostgreSQL: http://localhost:5432
- pgAdmin: http://localhost:5050

## Project Structure

```
atlas-engine/
├── pyproject.toml            # project metadata
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI routers
│   │   ├── core/             # Config, database
│   │   ├── models/           # SQLAlchemy models
│   │   └── services/         # Business logic (DesignTree, OIDC)
│   ├── tests/                # pytest suite
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/              # Typed API client
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── __tests__/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.ts
│   └── package.json
├── compose.yaml
├── portfolio.json
└── .github/workflows/ci.yml
```

## Authentication

OIDC authorization-code login through Keycloak with **backend-managed sessions**
(HttpOnly SameSite cookies) and server-side state/nonce/PKCE validation:

1. Frontend calls `POST /auth/login` → backend returns the authorization URL and
   binds `state`, `nonce`, and `code_verifier` to a short-lived signed
   `oauth_state` cookie (HttpOnly, SameSite=Strict, cleared on use).
2. Frontend redirects the browser to Keycloak.
3. Keycloak redirects back to the SPA `/callback` with `code` + `state`.
4. The SPA POSTs `{code, state, code_verifier}` to `POST /auth/callback`. The
   backend validates `state` and `code_verifier` against the `oauth_state`
   cookie (CSRF + PKCE defense-in-depth), exchanges the code, validates the
   `id_token` signature/issuer/audience **and nonce** (RS256), then issues the
   session token.
5. The session token is stored in an **HttpOnly SameSite cookie** (never
   localStorage/sessionStorage). Subsequent calls use the cookie via
   `withCredentials: true`.

**Security notes:**
- Session and OAuth-state tokens never appear in `localStorage`.
- State/nonce/code_verifier are validated server-side on callback (rejections
  return 400).
- Role checks run on every data endpoint (`viewer < operator < analyst < admin`).
- CSRF protection for cookie-authenticated writes is tracked as future work.

## Domain Engine

The `DesignTree` class enforces frontier-gated grilling:

- **Frontier**: decisions whose prerequisites are all settled.
- **Pivots**: frontier decisions scored by downstream dependency count
  (tree-reshaping decisions first).
- **Coverage**: bidirectional link tracking from each decision to PRD, issues,
  implementation, and verification artifacts, with PRD→decision staleness checks.

## API Reference

| Resource | Method | Path | Description |
|----------|--------|------|-------------|
| Auth | POST | `/auth/login` | Start OIDC login; returns auth URL + PKCE/state/nonce |
| Auth | POST | `/auth/callback` | Exchange code; validates state/nonce/PKCE; sets session |
| Auth | POST | `/auth/logout` | Clear session |
| Auth | GET | `/auth/me` | Current user |
| Health | GET | `/health` | Health check |
| Health | GET | `/health/db` | Database connectivity |
| Decisions | POST | `/decisions` | Create a decision |
| Decisions | GET | `/decisions/session/{session_id}` | List decisions for a session |
| Decisions | GET | `/decisions/{decision_id}` | Get a decision |
| Decisions | GET | `/decisions/{decision_id}/coverage` | Decision coverage |
| Decisions | POST | `/decisions/{decision_id}/supersede` | Supersede (version) a decision |
| Decisions | GET | `/decisions/session/{session_id}/coverage` | Session coverage report |
| Decisions | POST | `/decisions/session/{session_id}/frontier` | Frontier + pivots |
| PRDs | POST | `/prds` | Create a PRD / design doc |
| PRDs | GET | `/prds/session/{session_id}` | List PRDs |
| PRDs | GET | `/prds/{prd_id}` | Get a PRD with mappings |
| PRDs | POST | `/prds/{prd_id}/mappings` | Add a decision mapping |
| PRDs | GET | `/prds/{prd_id}/staleness` | Staleness check |
| Issues | POST | `/issues` | Create an issue |
| Issues | GET | `/issues/session/{session_id}` | List issues |
| Issues | GET | `/issues/{issue_id}` | Get an issue |
| Issues | PATCH | `/issues/{issue_id}` | Update an issue |
| Issues | POST | `/issues/{issue_id}/complete` | Complete an issue |
| Issues | GET | `/issues/session/{session_id}/frontier` | Unblocked issues |
| Verifications | POST | `/verifications` | Create a verification |
| Verifications | GET | `/verifications/session/{session_id}` | List verifications |
| Verifications | GET | `/verifications/{verification_id}` | Get a verification |
| Verifications | PATCH | `/verifications/{verification_id}` | Update a verification |
| Verifications | GET | `/verifications/session/{session_id}/coverage` | Session coverage report |

Required roles: write endpoints (`POST/PATCH`) require `operator` or above; read
endpoints require an authenticated session (`viewer`+); unauthenticated requests
are rejected with 401.

## Testing

### Backend

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v
```

### Frontend

```bash
cd frontend
npm test         # vitest
npm run build    # typecheck + vite build
```

## License

MIT — Ryan Vo <ryandtvo@gmail.com>