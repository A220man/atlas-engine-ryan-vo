# Deployment Guide

## Docker Compose (Recommended)

```bash
cp .env.example .env
# Edit .env with your credentials
docker compose up --build
```

### Port Mapping

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | Vite dev or nginx production |
| Backend | 8000 | FastAPI API |
| Keycloak | 8080 | OIDC provider |
| PostgreSQL | 5432 | Primary database |
| pgAdmin | 5050 | Database UI |

All ports bound to `127.0.0.1` only (not exposed to external traffic).

### Keycloak Realm Import

Place realm JSON in `keycloak/realms/atlas-realm.json`. The compose file mounts
this directory and Keycloak imports on startup via `start-dev --import-realm`.

### Production Checklist

1. Set `COOKIE_SECURE=true` (HTTPS required for cookie auth)
2. Set `OIDC_REDIRECT_URI` to your production domain
3. Provide a strong `SESSION_SECRET_KEY` (at least 32 bytes)
4. Set `CORS_ORIGINS` to your frontend domain
5. Configure PostgreSQL credentials (not dev defaults)
6. Enable rate limiting (future)
7. Add CSRF protection for cookie-authenticated writes (future)