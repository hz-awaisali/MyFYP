# Smart University Management System (SUMS) — Project Context

> **Version:** 1.0.0  
> **Stack:** Python 3.12+ / FastAPI (async) / PostgreSQL / SQLAlchemy 2.0 / Alembic  
> **Repository root:** `E:\Development\FYP\FastAPI_backend\MyFYP`

---

## 1. Overview

A **university administrative workflow engine** that digitizes student applications (e.g. Transcript Requests) through dynamic forms and multi-step approval chains. Built as an async FastAPI backend with RBAC, audit logging, real-time notifications, file attachments, and an AI assistant interface.

### Core Flow

```
Student → Submits Application → Workflow Engine Routes to Approvers
    ↓                                 ↓
Audit Logged                    Notifications + WebSocket Push
```

---

## 2. Directory Layout

```
MyFYP/
├── app/                      # Application package
│   ├── __init__.py           # Version: 1.0.0
│   ├── main.py               # FastAPI app factory (create_app)
│   ├── ai_services/          # AI provider abstraction (OpenRouter, Groq, Mock)
│   ├── applications/         # Dynamic forms, categories, application CRUD, workflow actions
│   ├── attachments/          # File upload/download (local or B2 storage)
│   ├── audit_logs/           # Read-only audit trail
│   ├── auth/                 # Register, login, JWT refresh, logout
│   ├── common/               # Base ORM models, shared enums, Pydantic schemas, generic repository
│   ├── core/                 # Config, DB engine, security, deps, middleware, exceptions, pagination
│   ├── departments/          # Department & Program models
│   ├── notifications/        # In-app notifications + WebSocket `/ws` stream
│   ├── roles/                # RBAC: Role, Permission, permission catalog
│   ├── system_settings/      # Key-value system settings
│   ├── users/                # User management + StudentProfile
│   └── workflows/            # Workflow definitions, steps, instances, action history
├── alembic/                  # Database migrations
├── docs/                     # Documentation
├── scripts/
│   └── seed.py               # Idempotent seed script (permissions, roles, admin, demo data)
├── tests/                    # Test suite
├── .env.example              # Environment variable template
├── docker-compose.yml        # PostgreSQL + app containers
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
└── pytest.ini
```

---

## 3. Configuration (`app/core/config.py`)

Settings loaded from environment / `.env` via `pydantic-settings` (`Settings` class). Key groups:

| Group | Key Settings |
|---|---|
| **App** | `APP_NAME`, `APP_ENV`, `DEBUG`, `API_V1_PREFIX` (default `/api/v1`) |
| **Database** | `DATABASE_URL` (asyncpg, default `postgresql+asyncpg://postgres:postgres@localhost:5432/sums`) |
| **JWT** | `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (30), `REFRESH_TOKEN_EXPIRE_DAYS` (7) |
| **Super Admin** | `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_FULL_NAME` |
| **CORS** | `CORS_ORIGINS` (supports `*` or comma-separated) |
| **Attachments** | `MAX_UPLOAD_SIZE_MB` (10), `ALLOWED_FILE_EXTENSIONS`, `STORAGE_BACKEND` (b2\|local), `PRESIGNED_URL_EXPIRE_SECONDS` |
| **B2** | `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_ENDPOINT_URL`, `B2_REGION` |
| **Local Storage** | `LOCAL_STORAGE_DIR` (default `uploads`) |
| **AI Providers** | `AI_DEFAULT_PROVIDER` (openrouter\|groq\|mock), `OPENROUTER_API_KEY`/`MODEL`, `GROQ_API_KEY`/`MODEL` |

---

## 4. Database Models (SQLAlchemy 2.0 async)

All models extend `Base` (declarative base) with mixins:
- `UUIDMixin` — UUID primary key (`id`)
- `TimestampMixin` — `created_at`, `updated_at` (timezone-aware, server defaults)

### 4.1 Users & Roles (RBAC)

```
User (users)
├── id (UUID PK), email (unique), hashed_password, full_name, phone
├── status: pending | approved | rejected | suspended
├── is_active: bool
├── role_id → Role
├── department_id → Department
├── role (relationship, selectin)
├── department (relationship)
└── student_profile (1:1 StudentProfile)

StudentProfile (student_profiles)
├── user_id → User (unique, CASCADE)
├── registration_number (unique)
├── program_id → Program
├── semester, batch
└── program (relationship)

Role (roles)
├── name (unique), description, is_system
├── permissions M:N → Permission (via role_permissions table)
├── users (relationship)
└── @property permission_codes: set[str]

Permission (permissions)
├── code (unique), description
└── roles M:N → Role
```

### 4.2 Departments & Programs

```
Department (departments)
├── name (unique), code (unique), description, is_active
├── hod_id → User (use_alter FK to break circular dep)
├── hod, members, programs (relationships)
└── programs (cascade delete)

Program (programs)
├── name, code (unique), description, duration_years, is_active
├── department_id → Department (CASCADE)
├── department (relationship)
└── students → StudentProfile (relationship)
```

### 4.3 Application Domain (Dynamic Forms)

```
ApplicationCategory (application_categories)
├── name, description, is_enabled
├── department_id → Department (SET NULL)
├── workflow_id → WorkflowDefinition (SET NULL)
└── forms → ApplicationForm[] (cascade delete)

ApplicationForm (application_forms)
├── category_id → ApplicationCategory (CASCADE)
├── name, version (int), is_active
├── category (relationship)
└── fields → ApplicationField[] (ordered by display_order, cascade delete)

ApplicationField (application_fields)
├── form_id → ApplicationForm (CASCADE)
├── key (machine name), label (display), field_type (enum: text|textarea|number|date|dropdown|radio|checkbox|file|email|phone)
├── is_required, default_value, validation (JSON), options (JSON), display_order
└── visibility_rule (JSON) — placeholder for conditional visibility

Application (applications)
├── category_id → ApplicationCategory
├── form_id → ApplicationForm (SET NULL)
├── student_id → User (CASCADE)
├── department_id → Department (denormalized from category, SET NULL)
├── status: draft|submitted|pending|under_review|returned|rejected|approved|forwarded|completed|closed
├── subject, submitted_at
├── category (relationship)
└── responses → ApplicationResponse[] (cascade delete)

ApplicationResponse (application_responses)
├── application_id → Application (CASCADE)
├── field_id → ApplicationField (CASCADE)
├── field_key, value (Text)
└── application (relationship)
```

### 4.4 Workflow Engine

```
WorkflowDefinition (workflow_definitions)
├── name, description, is_active
└── steps → WorkflowStep[] (ordered by step_order, cascade delete)

WorkflowStep (workflow_steps)
├── workflow_id → WorkflowDefinition (CASCADE)
├── step_order, name
├── role_id → Role (who acts at this step)
├── department_id → Department (optional fixed dept; null = use application's)
├── approval_required, can_forward, can_return, can_reject, is_final
└── workflow (relationship)

WorkflowInstance (workflow_instances)
├── workflow_id → WorkflowDefinition
├── application_id → Application (unique)
├── current_step_id → WorkflowStep (SET NULL)
├── is_complete, started_at, completed_at
├── workflow, current_step (relationships)
└── actions → WorkflowAction[] (ordered by created_at, cascade delete)

WorkflowAction (workflow_actions)
├── instance_id → WorkflowInstance (CASCADE)
├── step_id → WorkflowStep (SET NULL)
├── actor_id → User (SET NULL)
├── action: submit|approve|reject|forward|return_for_correction|add_remarks|close|reopen
├── remarks, from_status, to_status
└── instance (relationship)
```

### 4.5 Attachments

```
Attachment (attachments)
├── owner_type (polymorphic, e.g. "application"), owner_id (UUID)
├── filename, content_type, size_bytes (BigInteger)
├── storage_backend (b2|local), storage_key, bucket
└── uploaded_by → User (SET NULL)
```

### 4.6 Notifications

```
Notification (notifications)
├── user_id → User (CASCADE)
├── department_id → Department (SET NULL) — for broadcast
├── type: application_submitted|approved|rejected|returned|forwarded|new_remark|attendance_marked|account_approved|system
├── title, body
├── reference_type, reference_id (polymorphic entity ref)
├── is_read, read_at
└── reads → NotificationRead[] (cascade delete)

NotificationRead (notification_reads)
├── notification_id → Notification (CASCADE)
├── user_id → User (CASCADE)
└── read_at
```

### 4.7 Audit Logs

```
AuditLog (audit_logs)
├── actor_id → User (SET NULL), actor_role
├── action, entity_type, entity_id
├── old_status, new_status, remarks
├── department_id, ip_address
└── created_at (inherited)
```

---

## 5. API Routes

All mounted under `API_V1_PREFIX` (`/api/v1` by default). Defined in `app/main.py:62-72`.

| Router | Prefix | Description |
|---|---|---|
| `auth` | `/auth` | Register (student), login, token refresh, logout, `/me` |
| `roles` | `/roles` | Role & permission management |
| `users` | `/users` | User CRUD, approve/suspend |
| `departments` | `/departments` | Department & Program management |
| `application-categories` | `/application-categories` | Category CRUD, form builder, field management |
| `applications` | `/applications` | Create draft, list, get, submit, act (approve/reject/forward/return), timeline |
| `workflows` | `/workflows` | Workflow definitions, instances |
| `notifications` | `/notifications` | List, unread count, mark read, `GET /ws` (WebSocket) |
| `attachments` | `/attachments` | Upload, download, delete |
| `audit-logs` | `/audit-logs` | Read-only search/filter |
| `system-settings` | `/system-settings` | Key-value settings CRUD |

Additional top-level:
- `GET /health` — `{"status": "ok", "app": "...", "version": "..."}`
- `GET /` — Redirect to docs info

---

## 6. Authentication & Authorization

### JWT Tokens
- **Access token** (30 min) + **Refresh token** (7 days)
- Tokens contain `sub` (user UUID), `type` (access/refresh), `exp`
- Decoded by `decode_token()` in `app/core/security.py`

### Dependencies (`app/core/deps.py`)
| Dependency | Behavior |
|---|---|
| `CurrentUser` | Resolves JWT → fetches user from DB; rejects if inactive/unapproved |
| `require_permissions(...)` | Checks user.role.permission_codes; super admins bypass |
| `require_any_permission(...)` | At least one of the listed permissions required |

### Permission Catalog (`app/roles/permissions.py`)
15 permissions defined as data (not hardcoded in routes):
`create_application`, `view_own_applications`, `view_department_applications`, `view_all_applications`, `approve_application`, `manage_application_categories`, `manage_workflows`, `manage_departments`, `manage_users`, `manage_roles`, `manage_attendance`, `view_attendance`, `view_analytics`, `manage_settings`, `use_ai_assistant`

---

## 7. Shared Infrastructure

### Generic Repository (`app/common/repository.py`)
```
BaseRepository[ModelType]
├── get(id) → ModelType | None
├── get_by(**filters) → ModelType | None
├── list(offset, limit, order_by, **filters) → Sequence[ModelType]
├── count(**filters) → int
├── add(obj) → ModelType
└── delete(obj) → None
```

### Pagination (`app/core/pagination.py`)
- `PaginationParams(page, size, sort_by, sort_order, search)` — parsed from query params
- `build_page_meta(total, page, size)` → `{"total", "page", "size", "pages"}`

### Response Schemas (`app/common/schemas.py`)
- `Page[T](items: list[T], meta: PageMeta)` — paginated response wrapper
- `Message(success=True, message: str)` — simple success/error
- `ORMBase` — base schema with `from_attributes = True`

### Exception Handling (`app/core/exceptions.py`)
Custom exception hierarchy:
- `AppException` (base) → `NotFoundError` (404), `ConflictError` (409), `ValidationError` (422), `AuthenticationError` (401), `PermissionDeniedError` (403)
- Global handlers registered in `register_exception_handlers()`
- Response shape: `{"success": false, "error": {"code": "...", "message": "..."}}`

### Middleware (`app/core/middleware.py`)
- `RequestContextMiddleware` — attaches `X-Request-ID` header + client IP to `request.state`
- `SimpleRateLimitMiddleware` — in-memory fixed-window rate limiter (disabled by default)

### Error Response Envelope
All errors follow: `{"success": false, "error": {"code": "error_code", "message": "Human-readable message", "details": [...]}}`

---

## 8. Application Lifecycle & Workflow

### Status Transitions
```
DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED (final step) → COMPLETED
                  ↘ RETURNED → (student resubmits → UNDER_REVIEW)
                  ↘ REJECTED → CLOSED
FORWARDED → (next step's UNDER_REVIEW)
CLOSED → REOPENED → UNDER_REVIEW
```

### Workflow Engine Logic
1. **Submit** → Creates `WorkflowInstance` pointing to step 1, status → `SUBMITTED`
2. **Approve** → Advances to next step; if final step, status → `APPROVED`
3. **Forward** → Skips to a specific step
4. **Return** → Sends back to previous step, status → `RETURNED`
5. **Reject** → Status → `REJECTED`
6. **Close/Reopen** → Manual terminal state management

Each action records a `WorkflowAction` and an `AuditLog` entry.

---

## 9. File Attachments

- **Storage backends**: `LocalStorage` (filesystem) or `B2Storage` (Backblaze B2 S3-compatible)
- **Selection**: `STORAGE_BACKEND` env var (`b2` | `local`)
- **Upload validation**: File extension whitelist + max size (configurable)
- **Download**: Local serves via `/api/v1/attachments/local/{key}`; B2 returns presigned URLs

---

## 10. Notifications & WebSocket

- REST endpoints for listing, marking read, unread count
- Real-time push via WebSocket at `/api/v1/notifications/ws?token=<access_token>`
- Authenticated via JWT access token in query param
- Powered by `WebSocketManager` in `app/core/websocket.py` (connection registry by user_id)

---

## 11. AI Assistant

- Abstract `AIProvider` interface with `generate_application(prompt, context) → GeneratedApplication`
- Three implementations: `OpenRouterProvider` (default), `GroqProvider`, `MockProvider`
- `GeneratedApplication` contains `subject`, `body`, `structured_description`
- Provider selection via `AI_DEFAULT_PROVIDER` env var
- Concrete request/response wiring planned for Phase 2

---

## 12. Seeded Data (`scripts/seed.py`)

Idempotent seed script run via `python -m scripts.seed`:

| Entity | Details |
|---|---|
| **Permissions** | All 15 from the catalog |
| **Roles** | Super Admin, Student, HOD, HOD Assistant, Examination Officer, Registrar Officer, IT Officer, Transport Officer, Treasurer Officer — each with default permission set |
| **Super Admin** | Email/password from env (`admin@university.edu` / `Admin@12345`) |
| **Department** | "CS & IT Department" (code `CSIT`) |
| **Programs** | BS Computer Science (BSCS), BS IT (BSIT), BS AI (BSAI), BS Data Science (BSDS) — all 4-year |
| **Workflow** | "Transcript Request Workflow" — Step 1: HOD Approval, Step 2: Examination Processing (final) |
| **Category** | "Transcript Request" linked to CS&IT dept + above workflow |
| **Form** | "Transcript Request Form" with 3 fields: reason (textarea, required), copies (number, 1-10), delivery (dropdown: Pickup/Email/Postal) |

---

## 13. Testing

- **Framework**: pytest (configured in `pytest.ini`)
- **Async support**: via `pytest-asyncio`
- **Test location**: `tests/`

Run with:
```bash
pytest
```

---

## 14. Environment Setup

Copy `.env.example` → `.env` and configure:

```bash
# Minimum required for local dev:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sums
STORAGE_BACKEND=local
AI_DEFAULT_PROVIDER=mock

# Start PostgreSQL (Docker):
docker-compose up -d db

# Run migrations:
alembic upgrade head

# Seed data:
python -m scripts.seed

# Start the app:
uvicorn app.main:app --reload
```

---

## 15. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Async throughout** | Non-blocking I/O for DB, file storage, AI provider calls |
| **Dynamic forms** | Categories + Forms + Fields as data, not code — admin-configurable |
| **Workflow as data** | Approval chains stored in DB rows; engine interprets at runtime — no code changes needed |
| **RBAC via data** | Permissions are DB rows, routes declare required codes — flexible reassignment |
| **Separate service layer** | Routes thin, business logic in `Service` classes |
| **Generic repository** | Base CRUD for all models; domain repos extend it |
| **Storage abstraction** | `StorageBackend` protocol; callers don't care about local vs cloud |
| **Polymorphic attachments** | `owner_type`/`owner_id` pattern avoids separate join tables per entity |
