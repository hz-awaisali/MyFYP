# AI Agent Prompts — Smart University Frontend (Phase 1)

Use this document to instruct AI coding agents (Cursor, Copilot, Claude, etc.) to build **complete frontends** against the existing FastAPI backend.

|Deliverable|Platform|Primary users|Prompt section|
|-|-|-|-|
|Admin web dashboard|**React**|Super Admin, HOD, officers, registrars|[Prompt A — React](#prompt-a--react-admin-web-complete)|
|Student mobile app|**Flutter**|Students|[Prompt B — Flutter](#prompt-b--flutter-student-mobile-complete)|

**Mandatory companion doc:** [`FRONTEND\\\_API\\\_GUIDE.md`](./FRONTEND_API_GUIDE.md) — canonical API contracts, JSON examples, error shapes, WebSocket URL, and code snippets. The agent **must** follow it; do not invent endpoints or response fields.

**Backend scope:** Phase 1 only. Do **not** implement UI for attendance, analytics, dashboards, or AI assistant (Phase 2 — no routes yet).

\---

## How to use these prompts

1. Open a **new agent chat** dedicated to one platform (React or Flutter).
2. Attach or paste:

   * The full **Prompt A** or **Prompt B** below (copy the entire fenced block).
   * The file `docs/FRONTEND\\\_API\\\_GUIDE.md` (or ensure the agent can read it from the repo).
3. Optionally set environment variable placeholders:

   * React: `VITE\\\_API\\\_URL=http://localhost:8000/api/v1`
   * Flutter: configurable base URL (emulator: `http://10.0.2.2:8000/api/v1`, iOS sim: `http://localhost:8000/api/v1`).
4. Ask the agent to implement **screen-by-screen** using the API mapping tables in the prompt.
5. Verify against Swagger: `http://localhost:8000/docs`.

\---

## Shared API implementation guidelines (React \& Flutter)

Every agent **must** implement the following. These rules apply to **all 56 REST endpoints** and the notification WebSocket.

### 1\. Base URL and versioning

* All REST calls: `{BASE}/api/v1/...` where `BASE` is the server origin (e.g. `http://localhost:8000`).
* Never call `/api/v2` or unversioned paths except `GET /health`.
* JSON requests: header `Content-Type: application/json` (except multipart upload).

### 2\. Authentication

|Rule|Implementation|
|-|-|
|Access token|Header: `Authorization: Bearer <access\\\_token>` on every protected route|
|Storage|React: `localStorage` or secure cookie via BFF; Flutter: `flutter\\\_secure\\\_storage`|
|Login|`POST /auth/login` → store `tokens.access\\\_token` + `tokens.refresh\\\_token` + cache `user`|
|Session restore|On app start: if access token exists → `GET /auth/me`; on failure → logout|
|Refresh|On **401** (once per request): `POST /auth/refresh` with `{ "refresh\\\_token": "..." }` → replace both tokens → retry original request|
|Logout|`POST /auth/logout` (best effort) + clear tokens + clear user cache + redirect to login|
|Register|**Public** `POST /auth/register` — no Bearer header; then show **pending** UI (do not expect login until approved)|

**Account status handling (`user.status`):**

|Status|Login|UI behavior|
|-|-|-|
|`pending`|401 on login|“Awaiting admin approval”|
|`approved`|OK|Full access per permissions|
|`rejected`|401|Show contact admin|
|`suspended`|401|Show suspended message|

### 3\. Authorization (permissions, not hardcoded roles)

* After login / `GET /auth/me`, read `user.role.permissions\\\[].code`.
* **Gate routes, menus, and buttons** by permission code (see tables in Prompt A/B).
* `user.role.name === "super\\\_admin"` → treat as all permissions in UI (server already bypasses).
* **Do not** hide officer actions based only on job title strings; use `approve\\\_application`, `manage\\\_users`, etc.
* If API returns **403** `permission\\\_denied`, show inline error — do not crash.

### 4\. Pagination

For every list endpoint that returns `{ items, meta }`:

* Send query params: `page`, `size` (max 100), optional `search`, `sort\\\_by`, `sort\\\_order`.
* Bind UI pagination to `meta.page`, `meta.pages`, `meta.total`.
* Do not assume `items.length === total`; always use `meta.total`.

### 5\. Error handling

Parse failures uniformly:

```json
{
  "success": false,
  "error": {
    "code": "validation\\\_error",
    "message": "Human-readable message",
    "details": \\\[]
  }
}
```

|HTTP|Action|
|-|-|
|401|Refresh once → else logout|
|403|Show “You don’t have permission”|
|404|Show not found|
|409|Show conflict (duplicate email, etc.)|
|422|Show `error.message`; map `error.details` to form fields when present|

### 6\. UUIDs and enums

* IDs are UUID strings; store as string (TypeScript `string`, Dart `String`).
* Use **exact** enum strings from the API guide (lowercase): e.g. `application\\\_status`: `draft`, `pending`, `returned`, `forwarded`, `completed`.
* Workflow actions for officer UI: `approve`, `reject`, `forward`, `return\\\_for\\\_correction`, `add\\\_remarks`, `close`, `reopen` via `POST /applications/{id}/actions` — **not** `submit` (submit uses separate endpoint).

### 7\. List scoping (applications)

**Do not** filter applications only on the client. The server scopes by role:

|User|`GET /applications` returns|
|-|-|
|Student|Own applications only|
|Staff with `view\\\_department\\\_applications`|Department’s applications|
|Staff with `view\\\_all\\\_applications` / super admin|All|

Same for `GET /applications/{id}` — 403 if out of scope.

### 8\. Dynamic application forms

1. `GET /application-categories/{category\\\_id}` → read `forms` → use **active** form (`is\\\_active === true`, highest `version` if multiple).
2. Render fields sorted by `display\\\_order`.
3. Map `field\\\_type` → widget (see API guide §6.4).
4. Build `responses: \\\[{ field\\\_key, value }]` for `POST /applications`.
5. Validate required fields client-side; server returns 422 on mismatch.
6. **File fields:** `POST /attachments?owner\\\_type=application\\\&owner\\\_id=<id>` multipart **after** draft created; then optionally store reference in response value.

### 9\. Application lifecycle (strict order)

```
POST /applications          → status: draft
POST /attachments           → optional, owner\\\_id = application.id
POST /applications/{id}/submit   → pending | submitted (starts workflow)
GET  /applications/{id}/timeline → officer/student history
POST /applications/{id}/actions  → officer only (approve\\\_application)
```

* Student may **submit** when status is `draft` or `returned`.
* Officer actions require permission `approve\\\_application` and correct workflow step (403 if wrong role/step).

### 10\. Notifications

|Feature|API|
|-|-|
|Inbox|`GET /notifications?page=\\\&size=\\\&unread\\\_only=`|
|Badge|`GET /notifications/unread-count`|
|Mark one|`POST /notifications/{id}/read`|
|Mark all|`POST /notifications/read-all`|
|Realtime|WebSocket `ws(s)://<host>/api/v1/notifications/ws?token=<access\\\_token>`|

WebSocket message shape:

```json
{
  "event": "notification",
  "data": {
    "id": "uuid",
    "type": "application\\\_forwarded",
    "title": "...",
    "body": "...",
    "reference\\\_type": "application",
    "reference\\\_id": "uuid"
  }
}
```

On `reference\\\_type === "application"`, navigate to application detail.

### 11\. Attachments (Backblaze B2)

* Upload: `multipart/form-data`, field name `file`, query `owner\\\_type`, `owner\\\_id`.
* Response includes `download\\\_url` (presigned, **expires** \~1 hour).
* Before download, refresh URL via `GET /attachments/{attachment\\\_id}` if expired.
* Allowed: pdf, docx, png, jpg, jpeg; max 10 MB default.

### 12\. Phase 2 — do not implement

No UI or API calls for: attendance, analytics, dashboard aggregates, AI writing. Stub screens with “Coming soon” only if navigation placeholder is required.

\---

## Master API → feature mapping (both platforms)

Use this checklist to ensure **every Phase 1 endpoint** is wired in the correct app.

|#|Endpoint|React Admin|Flutter Student|
|-|-|:-:|:-:|
|1|`POST /auth/register`|—|Registration screen|
|2|`POST /auth/login`|Login|Login|
|3|`POST /auth/refresh`|HTTP interceptor|Dio interceptor|
|4|`POST /auth/logout`|Logout action|Logout|
|5|`GET /auth/me`|Boot + profile|Boot + profile|
|6|`GET /users`|User list|—|
|7|`POST /users`|Create staff|—|
|8|`PATCH /users/me`|Admin profile|Student profile|
|9|`GET /users/{id}`|User detail|—|
|10|`PATCH /users/{id}`|Edit user|—|
|11|`PATCH /users/{id}/status`|Approve/reject students|—|
|12|`GET /roles`|Roles admin|—|
|13|`GET /roles/permissions`|Permissions view|—|
|14|`GET /departments`|Dept list + register helper|Register: pick program|
|15|`POST /departments`|Create dept|—|
|16|`GET /departments/{id}`|Dept detail|—|
|17|`PATCH /departments/{id}`|Edit dept|—|
|18|`DELETE /departments/{id}`|Delete dept|—|
|19|`GET /departments/{id}/programs`|Programs tab|—|
|20|`POST /departments/{id}/programs`|Add program|—|
|21|`PATCH /departments/programs/{id}`|Edit program|—|
|22|`DELETE /departments/programs/{id}`|Delete program|—|
|23|`GET /application-categories`|Category list|Home: enabled categories|
|24|`POST /application-categories`|Create category|—|
|25|`GET /application-categories/{id}`|Form builder / preview|New application form|
|26|`PATCH /application-categories/{id}`|Edit category|—|
|27|`DELETE /application-categories/{id}`|Delete|—|
|28|`POST /.../categories/{id}/forms`|Create form + fields|—|
|29|`GET /.../forms/{form\\\_id}`|Form editor|—|
|30|`POST /.../forms/{id}/fields`|Add field|—|
|31|`DELETE /.../fields/{field\\\_id}`|Remove field|—|
|32|`GET /applications`|Work queue|My applications|
|33|`POST /applications`|—|Create draft|
|34|`GET /applications/{id}`|Review detail|Application detail|
|35|`POST /applications/{id}/submit`|—|Submit button|
|36|`POST /applications/{id}/actions`|Approve/reject/return/etc.|—|
|37|`GET /applications/{id}/timeline`|Timeline tab|Status timeline|
|38|`GET /workflows`|Workflow list|—|
|39|`POST /workflows`|Create workflow|—|
|40|`GET /workflows/{id}`|Workflow detail|—|
|41|`PATCH /workflows/{id}`|Update|—|
|42|`DELETE /workflows/{id}`|Delete|—|
|43|`POST /workflows/{id}/steps`|Add step|—|
|44|`POST /workflows/{id}/reorder`|Drag-drop reorder|—|
|45|`DELETE /workflows/steps/{id}`|Delete step|—|
|46|`GET /notifications`|Notification center|Notification list|
|47|`GET /notifications/unread-count`|Header badge|App bar badge|
|48|`POST /notifications/{id}/read`|Mark read|On open|
|49|`POST /notifications/read-all`|Mark all|Optional|
|50|`WS /notifications/ws`|Realtime toasts|Realtime + refresh list|
|51|`POST /attachments`|Admin upload if needed|File field upload|
|52|`GET /attachments/{id}`|Download link refresh|Open/download file|
|53|`DELETE /attachments/{id}`|Delete file|Remove before submit|
|54|`GET /audit-logs`|Audit page|—|
|55|`GET /system-settings`|Settings page|—|
|56|`PUT /system-settings`|Upsert setting|—|
|57|`GET /health`|Optional status indicator|Optional splash check|

\---

# Prompt A — React Admin Web (complete)

Copy everything inside the block below into your AI agent.

````markdown
# ROLE

You are a Senior Frontend Engineer building the \\\*\\\*Smart University Management System — Admin Web Application\\\*\\\* using \\\*\\\*React 18+\\\*\\\*, \\\*\\\*TypeScript\\\*\\\*, and modern tooling. You integrate \\\*\\\*only\\\*\\\* with the existing Phase 1 FastAPI backend. You do not mock business logic that the API already provides.

# SOURCE OF TRUTH

Read and strictly follow the repository file `docs/FRONTEND\\\_API\\\_GUIDE.md` for:
- Request/response JSON shapes
- Enum values
- Error envelope
- Pagination
- WebSocket URL
- Permission codes

OpenAPI (when backend runs): `http://localhost:8000/docs`  
Base API URL: `import.meta.env.VITE\\\_API\\\_URL` defaulting to `http://localhost:8000/api/v1`

# PRODUCT SCOPE

Build a \\\*\\\*responsive admin dashboard\\\*\\\* for university staff and super admin:

- \\\*\\\*Users:\\\*\\\* approve pending student registrations, CRUD staff, assign roles/departments
- \\\*\\\*University structure:\\\*\\\* departments and programs
- \\\*\\\*Application configuration:\\\*\\\* categories, dynamic form builder (all field types), workflow definitions
- \\\*\\\*Operations:\\\*\\\* application work queue, review screen with workflow actions, timeline, audit logs
- \\\*\\\*Notifications:\\\*\\\* inbox + unread badge + WebSocket realtime
- \\\*\\\*System settings:\\\*\\\* key/value settings
- \\\*\\\*NOT in scope:\\\*\\\* attendance, analytics dashboards, AI assistant (Phase 2 — no API routes; do not call them)

Primary personas: `super\\\_admin`, `hod`, `hod\\\_assistant`, `examination\\\_officer`, `registrar\\\_officer`, `it\\\_officer`, `transport\\\_officer`, `treasurer\\\_officer`. Students do \\\*\\\*not\\\*\\\* use this web app for registration (that is Flutter); but admin approves students here.

# TECH STACK (required)

- React 18 + TypeScript + Vite
- React Router v6 (protected routes)
- TanStack Query (React Query) for server state
- Axios (or fetch wrapper) with interceptors
- UI: Tailwind CSS + shadcn/ui (or MUI if you justify one choice and stay consistent)
- Forms: React Hook Form + Zod (client validation aligned with API)
- Toast notifications for API errors/success
- Optional: openapi-typescript generated types from `/api/v1/openapi.json`

# PROJECT STRUCTURE (create this)

```
src/
  api/
    client.ts          # axios instance, auth header, refresh interceptor
    endpoints/         # one file per module: auth, users, departments, ...
    types/             # API types (manual or generated)
  auth/
    AuthContext.tsx    # user, permissions, login, logout, loadMe
    ProtectedRoute.tsx
    Can.tsx            # permission wrapper component
  features/
    users/
    departments/
    categories/        # application categories + form builder
    workflows/
    applications/      # queue + review + actions + timeline
    notifications/
    audit/
    settings/
  layouts/
    AdminLayout.tsx    # sidebar from permissions
  pages/
  hooks/
  utils/
    errors.ts          # parse API error envelope
```

# API IMPLEMENTATION RULES (non-negotiable)

1. \\\*\\\*Every\\\*\\\* endpoint in the Master API table for “React Admin” must be implemented in `src/api/endpoints/` and used by at least one screen (no orphan API wrappers).
2. Attach `Authorization: Bearer` on all routes except `POST /auth/login` and `POST /auth/refresh`.
3. On 401: call `POST /auth/refresh` once with stored refresh token; on failure → logout and redirect `/login`.
4. Parse errors from `{ success: false, error: { code, message, details? } }`.
5. Paginated lists: use `page`, `size`, display `meta.total` / `meta.pages`.
6. Permission gates: read `user.role.permissions\\\[].code`; use `<Can permission="manage\\\_users">` etc.
7. Applications list: do not client-filter by department; trust `GET /applications` server scoping.
8. Officer actions: `POST /applications/{id}/actions` body `{ action, remarks? }` — remarks required when action is `add\\\_remarks`.
9. Submit is \\\*\\\*not\\\*\\\* used on web for student flows; students use mobile. Admin may only use actions + timeline.
10. Workflow designer: load roles via `GET /roles` to pick `role\\\_id` on steps; load departments for `department\\\_id`.
11. Form builder: support all `field\\\_type` values; dropdown/radio/checkbox require `options` array in UI.
12. Attachments: use `FormData` on `POST /attachments`; display `download\\\_url`; refresh via `GET /attachments/{id}` before download if link may expire.
13. WebSocket: connect to `ws://<host>/api/v1/notifications/ws?token=` + access token; on message invalidate React Query keys `notifications` and `unread-count`.
14. Do not implement Phase 2 APIs.

# SCREENS \\\& EXACT API WIRING

Implement these routes and wire APIs exactly as specified:

## Public

| Route | APIs |
|-------|------|
| `/login` | `POST /auth/login` → save tokens + user; redirect by permissions |

## Authenticated shell (`GET /auth/me` on load)

| Route | Permission | APIs |
|-------|------------|------|
| `/dashboard` | any | `GET /notifications/unread-count`, `GET /applications?size=5` (summary widgets) |
| `/users` | `manage\\\_users` | `GET /users` (filters: status, role\\\_id, department\\\_id, search) |
| `/users/new` | `manage\\\_users` | `POST /users` (role\\\_name, department\\\_id, status default approved) |
| `/users/:id` | `manage\\\_users` | `GET /users/{id}`, `PATCH /users/{id}`, `PATCH /users/{id}/status` |
| `/users/pending` | `manage\\\_users` | `GET /users?status=pending` + approve/reject actions |
| `/departments` | `manage\\\_departments` OR read for all | `GET /departments` |
| `/departments/new` | `manage\\\_departments` | `POST /departments` |
| `/departments/:id` | `manage\\\_departments` | `GET/PATCH/DELETE /departments/{id}`, `GET/POST /departments/{id}/programs`, `PATCH/DELETE /departments/programs/{program\\\_id}` |
| `/roles` | `manage\\\_roles` | `GET /roles`, `GET /roles/permissions` (read-only UI) |
| `/categories` | `manage\\\_application\\\_categories` | `GET /application-categories` |
| `/categories/new` | `manage\\\_application\\\_categories` | `POST /application-categories` (optional workflow\\\_id from workflows list) |
| `/categories/:id` | `manage\\\_application\\\_categories` | `GET/PATCH/DELETE /application-categories/{id}`, `POST /application-categories/{id}/forms`, field CRUD, `GET /application-categories/forms/{form\\\_id}` |
| `/workflows` | `manage\\\_workflows` | `GET /workflows` |
| `/workflows/new` | `manage\\\_workflows` | `POST /workflows` with steps array |
| `/workflows/:id` | `manage\\\_workflows` | `GET/PATCH/DELETE /workflows/{id}`, add step, `POST /workflows/{id}/reorder`, delete step |
| `/applications` | `view\\\_department\\\_applications` OR `view\\\_all\\\_applications` | `GET /applications` (filters: status, category\\\_id, pagination) |
| `/applications/:id` | same + `approve\\\_application` for actions | `GET /applications/{id}`, `GET /applications/{id}/timeline`, `POST /applications/{id}/actions` |
| `/notifications` | any authenticated | `GET /notifications`, mark read, read all, WebSocket |
| `/audit` | `view\\\_all\\\_applications` | `GET /audit-logs?entity\\\_type=\\\&entity\\\_id=\\\&actor\\\_id=` |
| `/settings` | `manage\\\_settings` | `GET /system-settings`, `PUT /system-settings` |
| `/profile` | any | `PATCH /users/me` |

## Sidebar visibility (permission codes)

- `manage\\\_users` → Users, Pending registrations
- `manage\\\_departments` → Departments
- `manage\\\_roles` → Roles
- `manage\\\_application\\\_categories` → Application categories
- `manage\\\_workflows` → Workflows
- `view\\\_department\\\_applications` or `view\\\_all\\\_applications` → Applications queue
- `view\\\_all\\\_applications` → Audit logs
- `manage\\\_settings` → Settings

## Application review page (critical UX)

Load application + timeline in parallel.

Show:
- Status badge (enum)
- Student info (from application.student\\\_id — may need user lookup if not embedded; use list data or add note in UI)
- Form responses (field\\\_key → value)
- Timeline: `workflow\\\_actions\\\[]` with actor, action, remarks, timestamps

Action toolbar (only if `approve\\\_application`):
- Approve → `{ action: "approve", remarks?: string }`
- Reject → `{ action: "reject", remarks?: string }`
- Return → `{ action: "return\\\_for\\\_correction", remarks: required }`
- Forward → `{ action: "forward" }`
- Add remarks → `{ action: "add\\\_remarks", remarks: required }`
- Close / Reopen when appropriate

On success: invalidate queries `applications`, `application`, `timeline`, `notifications`.

# END-TO-END FLOWS TO TEST

1. Login as `admin@university.edu` / `Admin@12345`
2. `GET /users?status=pending` → approve one student
3. Create department + program if not seeded
4. Create workflow with 2 steps → create category linked to workflow → create form with 3 fields
5. (Student submits on mobile) → appear in `GET /applications?status=pending`
6. Open application → approve → verify timeline + notification

# DELIVERABLES

1. Full React project in `frontend-admin/` (or repo root folder specified by user)
2. `.env.example` with `VITE\\\_API\\\_URL`
3. README: install, run, how to point at backend
4. No placeholder TODO for Phase 1 APIs — all admin endpoints must be wired
5. Clean, accessible UI; loading and error states on every mutation/query

# QUALITY BAR

- TypeScript strict mode, no `any` on API responses
- Centralized `parseApiError(error)` utility
- React Query `queryKey` conventions documented in README
- Mobile-responsive sidebar (collapsible)

Begin by scaffolding the project, then implement `api/client.ts` + `AuthContext`, then features in order: auth → users → departments → workflows → categories → applications → notifications → audit → settings.
````

\---

# Prompt B — Flutter Student Mobile (complete)

Copy everything inside the block below into your AI agent.

````markdown
# ROLE

You are a Senior Flutter Engineer building the \\\*\\\*Smart University Management System — Student Mobile App\\\*\\\* for \\\*\\\*Android and iOS\\\*\\\*. You integrate \\\*\\\*only\\\*\\\* with the existing Phase 1 FastAPI backend. You do not invent APIs or business rules.

# SOURCE OF TRUTH

Read and strictly follow `docs/FRONTEND\\\_API\\\_GUIDE.md` for all contracts, enums, errors, pagination, WebSocket, and file upload rules.

Base API URL must be configurable:
- Android emulator: `http://10.0.2.2:8000/api/v1`
- iOS simulator: `http://localhost:8000/api/v1`
- Physical device: `http://<LAN\\\_IP>:8000/api/v1`

# PRODUCT SCOPE

Mobile app for \\\*\\\*students only\\\*\\\* (role `student`):

- Register (pending approval)
- Login after admin approval
- Browse enabled application categories
- Fill \\\*\\\*dynamic forms\\\*\\\* from server-driven field definitions
- Upload attachments (file fields)
- Save draft → submit application → track status
- View timeline / workflow history
- Notifications (list + unread badge + WebSocket)
- Edit profile

\\\*\\\*NOT in scope on mobile:\\\*\\\* staff admin features (user management, workflow designer, category builder, audit logs, system settings). Do not call those APIs except where noted (e.g. `GET /departments` for registration).

\\\*\\\*NOT Phase 2:\\\*\\\* attendance, analytics, AI writer — no API calls; optional “Coming soon” placeholder only.

# TECH STACK (required)

- Flutter 3.x stable
- Dart 3
- \\\*\\\*dio\\\*\\\* for HTTP
- \\\*\\\*flutter\\\_secure\\\_storage\\\*\\\* for tokens
- \\\*\\\*riverpod\\\*\\\* or \\\*\\\*bloc\\\*\\\* for state (pick one, document choice)
- \\\*\\\*go\\\_router\\\*\\\* for navigation
- \\\*\\\*web\\\_socket\\\_channel\\\*\\\* for notifications WS
- \\\*\\\*file\\\_picker\\\*\\\* / \\\*\\\*image\\\_picker\\\*\\\* for file fields
- \\\*\\\*url\\\_launcher\\\*\\\* or \\\*\\\*open\\\_filex\\\*\\\* for opening presigned `download\\\_url`
- Models: manual from API guide or `json\\\_serializable`

# PROJECT STRUCTURE (create this)

```
lib/
  core/
    config/app\\\_config.dart       # baseUrl
    network/dio\\\_client.dart      # interceptors, refresh, auth header
    network/api\\\_error.dart       # parse error envelope
    storage/secure\\\_storage.dart
    router/app\\\_router.dart
  features/
    auth/                        # login, register, pending screen
    departments/                 # load depts/programs for register
    applications/
      data/applications\\\_api.dart
      presentation/
        categories\\\_screen.dart
        form\\\_screen.dart         # dynamic form renderer
        my\\\_applications\\\_screen.dart
        application\\\_detail\\\_screen.dart
    notifications/
    profile/
  shared/
    widgets/
    models/                      # User, Application, Field, PageMeta, ...
```

# API IMPLEMENTATION RULES (non-negotiable)

1. Implement \\\*\\\*every\\\*\\\* endpoint marked “Flutter Student” in the Master API mapping table in `docs/AI\\\_AGENT\\\_FRONTEND\\\_PROMPTS.md`.
2. Public routes (no Bearer): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` (refresh uses body token, not Bearer).
3. Store `access\\\_token` and `refresh\\\_token` in \\\*\\\*flutter\\\_secure\\\_storage\\\*\\\* only.
4. On 401: refresh once via `POST /auth/refresh`; else clear storage → navigate to login.
5. After login: persist user JSON from `AuthResponse.user` OR refetch `GET /auth/me` on cold start.
6. If `user.status != approved` after login attempt, show dedicated screens (pending / rejected / suspended) based on API message.
7. Registration flow:
   - `GET /departments?page=1\\\&size=50` → user picks department → programs from `department.programs` or `GET /departments/{id}/programs`
   - `POST /auth/register` with `program\\\_id` UUID string
   - Navigate to \\\*\\\*Pending approval\\\*\\\* screen (no login retry loop)
8. Categories home: `GET /application-categories?enabled\\\_only=true` — only show `is\\\_enabled: true`.
9. Dynamic form:
   - `GET /application-categories/{id}` → select active form → render fields by `field\\\_type` and `display\\\_order`
   - Validate `is\\\_required` and `validation` rules client-side
   - `POST /applications` with `{ category\\\_id, subject, responses: \\\[{ field\\\_key, value }] }`
10. File fields workflow:
    - After draft created, `POST /attachments` multipart `file` + query `owner\\\_type=application`, `owner\\\_id=<application.id>`
    - Use returned `download\\\_url` only for preview/download; refresh with `GET /attachments/{id}` if expired
11. Submit: `POST /applications/{id}/submit` when status is `draft` or `returned` — no body.
12. My applications: `GET /applications` with pagination — server returns \\\*\\\*only own\\\*\\\* applications.
13. Detail: `GET /applications/{id}` + `GET /applications/{id}/timeline` for status history.
14. Notifications:
    - `GET /notifications/unread-count` for app bar badge
    - `GET /notifications` with `unread\\\_only` filter tab
    - `POST /notifications/{id}/read` when user opens item
    - WebSocket: `ws://<host>/api/v1/notifications/ws?token=<access\\\_token>` — on event, refresh list + badge
    - Tap notification: if `reference\\\_type == application`, go to application detail with `reference\\\_id`
15. Profile: `GET /auth/me`, `PATCH /users/me` (only full\\\_name, phone — do not send department\\\_id)
16. Logout: `POST /auth/logout` + clear storage
17. Do \\\*\\\*not\\\*\\\* call officer/admin endpoints (`/users` list, `/workflows`, `POST .../actions`, audit, settings, etc.)

# SCREENS \\\& EXACT API WIRING

| Screen | Route | APIs (in order) |
|--------|-------|-----------------|
| Splash | `/` | optional `GET /health`; if token → `GET /auth/me` |
| Login | `/login` | `POST /auth/login` |
| Register | `/register` | `GET /departments` → pick program → `POST /auth/register` |
| Pending approval | `/pending` | none (static + logout) |
| Home | `/home` | `GET /application-categories?enabled\\\_only=true` |
| New application | `/apply/:categoryId` | `GET /application-categories/{id}` → render form → `POST /applications` → uploads → `POST .../submit` |
| My applications | `/applications` | `GET /applications?page\\\&size\\\&status?` |
| Application detail | `/applications/:id` | `GET /applications/{id}`, `GET /applications/{id}/timeline` |
| Resubmit | same as new | when `status == returned`, allow edit responses if you implement local re-draft or re-submit flow per API guide §7.3 (submit again on returned) |
| Notifications | `/notifications` | list, unread count, mark read, WS |
| Profile | `/profile` | `GET /auth/me`, `PATCH /users/me` |
| Logout | — | `POST /auth/logout`, clear storage |

# DYNAMIC FORM RENDERER (required behavior)

Map `field\\\_type` → widget:

| field\\\_type | Widget | value in responses |
|------------|--------|-------------------|
| text | TextField | string |
| textarea | multiline | string |
| number | numeric keyboard | number as string |
| date | date picker | ISO date `YYYY-MM-DD` |
| email | email keyboard | string |
| phone | phone keyboard | string |
| dropdown | DropdownButton | single option string |
| radio | RadioListTile | single option string |
| checkbox | CheckboxListTile multi | list → API accepts array |
| file | pick file → upload attachment API | store filename or attachment id in value after upload |

For `dropdown`/`radio`/`checkbox`, options come from field `options` JSON array.

Show field `label` and enforce `is\\\_required`.

# APPLICATION STATUS UI

Map backend status to student-friendly labels:

| status | Color / icon | Actions available |
|--------|--------------|-------------------|
| draft | grey | Continue, Submit |
| pending | orange | View only |
| returned | amber | Fix and Submit again |
| rejected | red | View only |
| forwarded | blue | View only |
| completed | green | View only |
| closed | grey | View only |

# NOTIFICATION TYPES

Handle `type` for icons/copy: `application\\\_submitted`, `application\\\_approved`, `application\\\_rejected`, `application\\\_returned`, `application\\\_forwarded`, `account\\\_approved`, `system`, etc.

# ERROR UX

- Show `error.message` from API in SnackBar or dialog
- 422: show validation text; highlight fields when `details` maps to keys
- Network errors: retry button on lists
- 403: rare for student — show generic forbidden

# END-TO-END TEST SCRIPT

1. Register new student → see pending screen
2. Admin approves on web (outside this app)
3. Login → home shows categories (seeded: Transcript Request)
4. Create application with reason + copies + delivery → submit
5. See item in My applications with status `pending`
6. Open detail + timeline tab
7. Receive notification on WebSocket when officer acts (if web used)

# DELIVERABLES

1. Flutter project in `mobile-student/` (or user-specified folder)
2. `lib/core/config/app\\\_config.dart` with base URL comment for emulator/device
3. README: flutter run, API URL configuration
4. All student-mapped APIs implemented — no stubbed Phase 1 endpoints
5. Material 3 UI, loading indicators, pull-to-refresh on lists

# QUALITY BAR

- Null-safe Dart
- Repository pattern: `XApi` class per module calling dio
- Unit tests for `ApiError.parse` and form validation logic (minimum)
- Do not hardcode category names or form fields — always server-driven

Begin with `dio\\\_client` + secure storage + auth flow, then registration, then applications feature, then notifications + WebSocket, then profile.
````

\---

## Optional: combined verification prompt

After either frontend is generated, run this **QA agent** prompt:

````markdown
Audit the \\\[React admin / Flutter student] app against `docs/FRONTEND\\\_API\\\_GUIDE.md` and the Master API mapping table in `docs/AI\\\_AGENT\\\_FRONTEND\\\_PROMPTS.md`.

For each of the 57 endpoints, report:
- Implemented / Missing / Wrong method or path
- Correct permission gating (React) or correctly omitted (Flutter)
- Error handling uses `error.message`
- Pagination uses `meta`
- Token refresh on 401

Fix all Missing and Wrong items. Do not add Phase 2 features.
````

\---

## Document links

|File|Purpose|
|-|-|
|[FRONTEND\_API\_GUIDE.md](./FRONTEND_API_GUIDE.md)|API contracts \& examples|
|[AI\_AGENT\_FRONTEND\_PROMPTS.md](./AI_AGENT_FRONTEND_PROMPTS.md)|This file — agent prompts|
|[../README.md](../README.md)|Backend setup \& deploy|

*Version: Phase 1 — matches backend modular monolith foundation.*

