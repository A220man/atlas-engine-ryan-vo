# Atlas Engine

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


Decision traceability engine that enforces requirement propagation from resolved design decisions through **PRD → Issues → Implementation → Verification**.

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

## Prerequisites

- Python 3.12+
- Node.js 24+
- Docker + Docker Compose (optional, for full stack)

## Quick Start (Local Development)

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=backend .venv/bin/python -m pytest tests/
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
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
├── backend/
│   ├── app/
│   │   ├── api/routes/   # FastAPI routers
│   │   ├── core/         # Config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   └── services/     # Business logic
│   ├── tests/           # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/       # Typed API client
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

OAuth2/OIDC via Keycloak with **backend-managed sessions**:

1. Frontend calls `/auth/login` → receives authorization URL
2. User redirected to Keycloak → authenticates → redirected back with code
3. Frontend calls `/auth/callback` → backend exchanges code, creates session
4. Session token stored in **HttpOnly SameSite cookie** (not localStorage)
5. Frontend relies on cookie via `withCredentials: true`

**Security notes:**
- Session token NEVER stored in localStorage or sessionStorage
- OIDC state/nonce/code_verifier stored in sessionStorage (transient, per-redirect)
- Cookies are HttpOnly, SameSite=Lax
- CSRF protection on cookie-authenticated writes planned as future work

## Domain Engine

The `DesignTree` class enforces frontier-gated grilling:

- **Frontier**: decisions all of whose prerequisites are settled
- **Pivots**: frontier decisions scored by downstream dependency count
- **Coverage**: bidirectional link tracking from each decision to PRD, issues, implementation, and verification artifacts

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Start OIDC login flow |
| GET | `/auth/callback` | OIDC callback handler |
| POST | `/auth/logout` | End session |
| GET | `/auth/me` | Current user info |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/decisions` | List all decisions |
| POST | `/api/v1/decisions` | Create decision |
| GET | `/api/v1/decisions/{id}` | Get decision |
| PUT | `/api/v1/decisions/{id}` | Update decision |
| GET | `/api/v1/decisions/{id}/coverage` | Coverage report |
| GET | `/api/v1/frontier` | Frontier decisions |
| GET | `/api/v1/issues/unblocked` | Unblocked issues |

## Testing

### Backend

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v
```

### Frontend

```bash
cd frontend
npx vitest run      # run tests
npm run build       # type check + build
```

## License

MIT — Ryan Vo <ryandtvo@gmail.com>