# API Reference

Base URL: `/api/v1` (except auth endpoints at `/auth`)

## Authentication

### POST /auth/login
Start OIDC login flow. Returns authorization URL and PKCE parameters.

**Response:**
```json
{
  "authorization_url": "https://keycloak/realms/atlas/protocol/...",
  "state": "random-uuid",
  "nonce": "random-uuid",
  "code_verifier": "base64-encoded-verifier"
}
```

### POST /auth/callback
Exchange OIDC code for session. Backend sets HttpOnly SameSite cookie.

**Request:**
```json
{"code": "...", "state": "...", "code_verifier": "..."}
```

### POST /auth/logout
Clear session cookie.

### GET /auth/me
Get current user info. Requires cookie or Bearer token.

## Decisions

### GET /api/v1/decisions
List all decisions. Returns array of decision objects with status, title, and coverage summary.

### POST /api/v1/decisions
Create a new decision.

**Request:**
```json
{"title": "Use PostgreSQL for production", "constraints": {"depends_on": []}}
```

### GET /api/v1/decisions/{id}
Get a single decision by ULID.

### PUT /api/v1/decisions/{id}
Update decision status (e.g., to RESOLVED).

## Design Tree

### GET /api/v1/frontier
Get frontier decisions — those whose prerequisites are all settled.

**Response:**
```json
{
  "frontier": [{"id": "...", "title": "..."}],
  "pivots": [{"id": "...", "title": "...", "downstream_count": 5}]
}
```

## Coverage

### GET /api/v1/decisions/{id}/coverage
Get coverage report for a decision.

**Response:**
```json
{
  "decision_id": "...",
  "fully_covered": true,
  "categories": {
    "prd": [{"id": "...", "status": "mapped"}],
    "issue": [{"id": "...", "status": "open"}],
    "implementation": [{"id": "...", "status": "complete"}],
    "verification": [{"id": "...", "status": "verified"}]
  }
}
```

## Issues

### GET /api/v1/issues/unblocked
Get issues not blocked by any open decision prerequisite.

### GET /api/v1/issues
List all issues with decision linkage.

### POST /api/v1/issues
Create a new issue linked to a decision.

### POST /api/v1/issues/{id}/complete
Complete an issue and create a new decision if covered.

## Health

### GET /api/v1/health
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00Z",
  "service": "atlas-engine"
}
```