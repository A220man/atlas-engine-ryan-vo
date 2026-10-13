# Architecture

## Overview

Atlas Engine is a **decision traceability engine** that enforces bidirectional
requirement propagation from resolved design decisions through PRD → Issues →
Implementation → Verification. It combines a FastAPI backend with a React/Vite
frontend, backed by SQLAlchemy async ORM and Keycloak OIDC authentication.

## High-Level Diagram

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

## Components

### Frontend

- **Vite + React 18 + TypeScript**: build tooling and component runtime
- **TanStack Query**: server state management with caching
- **Axios**: typed API client with `withCredentials: true` for cookie-based auth
- **Lucide React**: icon library

### Backend

- **FastAPI**: async web framework with automatic OpenAPI docs
- **SQLAlchemy 2.0**: async ORM with SQLite (dev) / PostgreSQL (prod)
- **Alembic**: database migrations
- **ULID**: conflict-free ID generation
- **PyJWT**: session token creation and validation

## Data Model

### Decision
A design decision with a status lifecycle: DRAFT → RESOLVED → SUPERSEDED.

### DecisionCoverage
Tracks bidirectional links from each decision to:
- PRD references (`prd_refs`)
- Issue references (`issue_refs`)
- Implementation references (`impl_refs`)
- Verification references (`verify_refs`)

### DesignTree
Domain engine that:
1. Builds a dependency graph from `depends_on` constraints
2. `get_frontier(settled)` returns decisions whose prerequisites are all settled
3. `get_pivots(frontier)` scores frontier decisions by downstream count

## Authentication Flow

1. Frontend calls `POST /auth/login` → backend returns OIDC authorization URL with state/nonce/code_verifier
2. Frontend stores state/nonce/code_verifier in sessionStorage, redirects to Keycloak
3. User authenticates → Keycloak redirects back to `/auth/callback`
4. Backend exchanges code for OIDC token, validates, creates user if needed
5. Backend creates session JWT, sets it as HttpOnly SameSite cookie
6. Frontend calls `GET /auth/me` (cookie sent via `withCredentials`)
7. Subsequent API calls authenticated via cookie

## Authorization

Role hierarchy: `viewer(0) < operator(1) < analyst(2) < admin(3)`

- `viewer`: read decisions and coverage reports
- `operator`: create/update issues, complete issues
- `analyst`: create PRD mappings, manage verification entries
- `admin`: full access including user management

## Deployment

### Docker Compose

Three tiers:
- **Frontend**: nginx serving static build, proxying `/api` to backend
- **Backend**: Python uvicorn, async PostgreSQL driver
- **Keycloak**: OIDC provider with realm import on startup

### Production Considerations

- PostgreSQL instead of SQLite for concurrent access
- `COOKIE_SECURE=true` for HTTPS-only cookies
- CSRF protection for cookie-authenticated writes (future)
- Rate limiting on auth endpoints (future)