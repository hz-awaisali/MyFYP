# Smart University Management System - Backend

Production-grade, async FastAPI backend for digitalizing university workflows:
student applications, configurable approval workflows, departmental processing,
notifications, audit logging and file attachments. Built as a **modular
monolith** so future Flutter mobile and React admin clients can consume the same
versioned REST + WebSocket API without architectural changes.

> Phase 1 (this repo): core platform - auth, RBAC, users, university structure,
> dynamic applications, workflow engine, notifications, attachments, audit logs.
> Phase 2 (scaffolded): attendance, analytics, dashboards and the AI writing
> assistant (provider abstraction already in place).

## Tech stack

- **FastAPI** (async) + Uvicorn, OpenAPI/Swagger at `/docs`
- **PostgreSQL** via **SQLAlchemy 2.0 (async)** + **asyncpg**, migrations with **Alembic**
- **JWT** access + refresh tokens, **permission-based RBAC**
- **WebSockets** for realtime notifications
- **Backblaze B2** (S3-compatible) for attachment storage, presigned downloads
- **pytest** + httpx test suite

## Architecture

```
app/
  core/            # config, async DB, security (JWT/hash), deps & guards,
                   #   exceptions, pagination, middleware, websocket manager
  common/          # Base model, mixins, base repository, enums, schemas
  auth/            # register / login / refresh / logout
  roles/           # roles + permissions (RBAC)
  users/           # user accounts + lifecycle + student profiles
  departments/     # departments + programs
  applications/    # categories, dynamic form builder, applications, responses
  workflows/       # configurable workflow engine (definitions/steps/instances)
  notifications/   # notifications + WebSocket push
  attachments/     # storage abstraction (Backblaze B2 default)
  audit_logs/      # audit trail recorded on every state change
  system_settings/ # configurable runtime settings
  attendance/  analytics/  dashboard/  ai_services/   # Phase 2 (scaffolded)
```

Each module owns its `models / schemas / repository / service / router /
permissions`. Routers stay thin; business logic lives in services; DB access in
repositories.

## Local development

Requires Python 3.12 (3.11-3.13 fine) and a PostgreSQL instance.

```bash
# 1. Create a virtualenv and install deps
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env            # then edit values (DB URL, JWT secrets, B2 keys)

# 3. Run migrations and seed baseline data
alembic upgrade head
python -m scripts.seed

# 4. Start the API
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for Swagger.

**Frontend integration:**
- [docs/FRONTEND_API_GUIDE.md](docs/FRONTEND_API_GUIDE.md) — API contracts, request/response examples, React & Flutter snippets
- [docs/AI_AGENT_FRONTEND_PROMPTS.md](docs/AI_AGENT_FRONTEND_PROMPTS.md) — copy-paste AI agent prompts to generate the full React admin web and Flutter student mobile apps

> Tip: for fully offline dev, set `STORAGE_BACKEND=local` to store attachments on
> disk instead of Backblaze B2.

## Run with Docker Compose

```bash
copy .env.example .env            # set JWT secrets and B2 keys
docker compose up --build
```

This starts PostgreSQL and the backend. Migrations run automatically on startup
(via `entrypoint.sh`); set `SEED_ON_START=true` to also seed baseline data.

## Tests

```bash
pytest
```

Tests run against an in-memory SQLite database (no external services needed) and
cover auth, RBAC guards, repositories, dynamic-form validation and the workflow
engine.

## Database migrations

```bash
alembic revision --autogenerate -m "describe change"   # after model changes
alembic upgrade head                                    # apply
alembic downgrade -1                                    # roll back one
```

## Backblaze B2 (attachments)

Create a bucket and an application key, then set in `.env`:

```
STORAGE_BACKEND=b2
B2_KEY_ID=...
B2_APPLICATION_KEY=...
B2_BUCKET_NAME=...
B2_ENDPOINT_URL=https://s3.<region>.backblazeb2.com
B2_REGION=<region>
```

Files are uploaded to B2 and served to clients via short-lived presigned URLs;
the API never proxies file bytes.

## Deploying to Coolify (Contabo VPS)

1. Push this repo to GitHub:
   ```bash
   git remote add origin git@github.com:<you>/<repo>.git
   git push -u origin main
   ```
2. In Coolify, create a new resource from your GitHub repo. Choose either:
   - **Docker Compose** (uses `docker-compose.yml`), or
   - **Dockerfile** (single service; point `DATABASE_URL` at a Coolify-managed
     PostgreSQL).
3. Set environment variables in Coolify (never commit secrets): `DATABASE_URL`,
   `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `SUPERADMIN_*`, the `B2_*` keys,
   and `CORS_ORIGINS`.
4. Deploy. The container runs `alembic upgrade head` on start. Set
   `SEED_ON_START=true` for the first deploy to create roles, permissions and the
   super admin.

## Default super admin

Seeded from `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` (defaults
`admin@university.edu` / `Admin@12345`). **Change these in production.**

## API overview

All endpoints are versioned under `/api/v1`:

| Area | Prefix |
|------|--------|
| Auth | `/auth` |
| Roles & permissions | `/roles` |
| Users | `/users` |
| Departments & programs | `/departments` |
| Application categories & forms | `/application-categories` |
| Applications | `/applications` |
| Workflows | `/workflows` |
| Notifications (+ `/notifications/ws`) | `/notifications` |
| Attachments | `/attachments` |
| Audit logs | `/audit-logs` |
| System settings | `/system-settings` |
