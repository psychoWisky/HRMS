# AVFU HRMS — Developer Guide

Technical reference for anyone building on, deploying, or handing over this
codebase. For what the system does and why, see
[`docs/PROJECT_BRIEF.md`](PROJECT_BRIEF.md).

---

## 1. Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.x (sync), Pydantic v2 |
| Database | PostgreSQL 16 (via `psycopg` v3 driver) |
| Auth | JWT (HS256), bcrypt password hashing |
| Frontend | Next.js 15 (App Router, Turbopack), React 19, TypeScript |
| Styling | Tailwind CSS v4, hand-written design tokens (no component library) |
| Frontend extras | framer-motion (animation), lucide-react (icons) |
| Reports | openpyxl (`.xlsx` generation) |

No ORM migrations tool (Alembic) is set up — the schema is created with
`Base.metadata.create_all()` and the dev workflow is drop-and-reseed (see
§4). No test suite exists yet.

---

## 2. Repository layout

```
HRMS-main/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, router registration, CORS
│   │   ├── core/
│   │   │   ├── config.py        # Settings (env vars), pydantic-settings
│   │   │   ├── database.py      # SQLAlchemy engine/session/Base
│   │   │   ├── security.py      # password hashing, JWT create/verify
│   │   │   ├── deps.py          # FastAPI dependencies: get_current_user,
│   │   │   │                    #   get_current_employee, require_perm()
│   │   │   ├── permissions.py   # permission codes + role -> permission map
│   │   │   └── audit.py         # audit.log() helper
│   │   ├── models/models.py     # every SQLAlchemy model (single file)
│   │   ├── schemas/schemas.py   # every Pydantic request/response model
│   │   ├── routers/             # one file per API area (see §6)
│   │   ├── services/            # business logic shared across routers
│   │   │   ├── org.py           # org-unit tree, scoping, cycle guards
│   │   │   ├── employee_id.py   # HRMS Employee ID generation
│   │   │   ├── hierarchy.py     # reporting chain, post vacancy math
│   │   │   ├── serializers.py   # model -> schema conversion helpers
│   │   │   ├── storage.py       # file upload storage (KYC docs, photos)
│   │   │   └── xlsx.py          # Excel report generation
│   │   └── data/avfu_master_data.py  # AVFU's real org structure (seed data)
│   ├── seed.py                  # drops/rebuilds schema, loads master data
│   ├── requirements.txt
│   ├── .env.example             # copy to .env and fill in
│   └── uploads/                 # KYC documents + employee photos (gitignored)
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages (see §7)
│   │   │   ├── login/page.tsx
│   │   │   ├── submit/page.tsx  # public new-employee onboarding form
│   │   │   └── (app)/           # everything behind the sidebar layout
│   │   ├── components/          # shared UI (DataTable, Modal, OrgUnitSelect, …)
│   │   └── lib/                 # api.ts, auth.tsx, nav.ts, perms.ts, format.ts
│   ├── next.config.mjs          # proxies /api/* to the backend
│   └── package.json
└── docs/
    ├── PROJECT_BRIEF.md         # what & why
    └── DEVELOPER_GUIDE.md       # this file
```

---

## 3. Running it locally

### Prerequisites
- Python 3.11+, Node.js 20+, PostgreSQL 16+ running locally (or reachable).

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# edit .env: set DATABASE_URL to a Postgres instance you control, and a real SECRET_KEY

# create the database once (adjust user/db name to match .env):
psql -U postgres -c "CREATE DATABASE avfu_hrms;"

# build the schema and load AVFU's org structure + 3 demo logins:
python seed.py

# run the API
python -m uvicorn app.main:app --reload --port 8002
```

`seed.py` **drops and rebuilds every table** by default (`python seed.py`).
Pass `--keep` to upsert into an existing database instead of rebuilding it
(`python seed.py --keep`).

After seeding, three accounts exist:

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@avfu.ac.in` | `Admin@1234` |
| HR | `hr@avfu.ac.in` | `HrAdmin@1234` |
| Department Head | `ananya.baruah@avfu.ac.in` | `DeptHead@1234` (forced password change on first login; manages "Directorate of Research") |

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Next.js picks the first free port starting at 3000 — check the terminal
output for the actual URL (commonly `http://localhost:3000` or `:3001` if
3000 is taken by another project).

The frontend never talks to the backend by absolute URL — every call is a
relative `/api/...` path, and `next.config.mjs` rewrites `/api/*` to
`http://127.0.0.1:8002/api/*` in dev. **The backend must run on port
8002** for this to work, unless you also edit the rewrite target.

### Production build check

```powershell
cd frontend
npm run build     # must succeed with no type errors before shipping
```

---

## 4. Database

### Connection

Set in `backend/.env` as `DATABASE_URL`, SQLAlchemy + psycopg3 URL form:

```
postgresql+psycopg://<user>:<password>@<host>:<port>/<database>
```

Local dev default: `postgresql+psycopg://postgres:postgres@localhost:5432/avfu_hrms`.

### Schema management

There is no migration tool. `Base.metadata.create_all(bind=engine)` runs
on every app startup (`app/main.py`) and creates any missing tables, but
**never alters existing ones**. If you change a model's columns, you must
either:
- drop and re-run `python seed.py` (loses data — fine in dev), or
- write the `ALTER TABLE` by hand against the running database (needed in
  any environment with real data you must keep).

If this project grows a real production deployment, introducing Alembic
for versioned migrations is the natural next step — it is not there yet.

### Tables (21)

`permissions`, `roles`, `role_permissions`, `users`, `locations`,
`org_units`, `designations`, `posts`, `employees`,
`reporting_relationships`, `position_history`,
`custom_field_definitions`, `custom_field_values`,
`custom_document_requirements`, `kyc`, `kyc_documents`, `kyc_history`,
`employee_submissions`, `submission_documents`, `audit_logs`,
`system_settings` (table still exists; its management UI was removed —
see Project Brief §5).

---

## 5. Data model — the core shape

The whole organisational hierarchy is **one self-referencing table**,
`OrgUnit`, not a separate table per level:

```python
class OrgUnitKind(str, Enum):
    college = "college"            # top level, parent_id is NULL
    establishment = "establishment"  # admin office; parent is a college
    department = "department"      # academic dept; parent is a college
                                    #   or an establishment
    section = "section"            # Section/Unit/Cell; parent is an
                                    #   establishment, department, or
                                    #   another section (nested once)
```

`OrgUnit.sub_kind` (`"section" | "unit" | "cell"`) further labels a
`section`-kind row. Every `OrgUnit` also carries the "Part A" general-info
fields (`reporting_authority_text`, `hrms_contact_*`, `office_email`,
`head_employee_id`) and, for sections, `officer_in_charge_employee_id` +
`headcount_note`.

`app/services/org.py` is where all tree logic lives:
`assert_valid_parent()` enforces the kind hierarchy above at
create/update time; `org_unit_ancestors()` / `org_unit_descendant_ids()`
walk the tree; `department_scope_ids()` is what turns a Department Head's
`User.managed_org_unit_id` into "every org unit id they're allowed to
touch" — every router that needs department-scoping calls this.

**Employee** attaches to exactly one `OrgUnit` via `org_unit_id` (any
level — an office directly, or one of its sections). It also holds
`designation_id` (job title — see §5.1) and optionally `post_id` (a
specific sanctioned seat).

**Post** = "N sanctioned seats of Designation X inside OrgUnit Y"
(`unique(org_unit_id, designation_id)`), carrying `sanctioned_count`,
`level_no` (their ordering in the source document's Part B table), and
`reports_to_note` (free text like "HOD / Dean / Registrar", not a real
FK). Occupied/vacant counts are computed on the fly from active employees
holding that post (`app/services/hierarchy.py: occupied_counts`), never
stored.

**PositionHistory** is an append-only timeline per employee — one row per
joining/promotion/establishment-change/employee-ID-change event. Nothing
here is ever edited or deleted; `promote_employee()` in
`app/routers/employees.py` writes new rows and then updates the live
`Employee` columns.

### 5.1 Employee ID generation

Format: `AVFU/<Establishment short code>/<Department short code or GEN>/<4-digit serial>`.

`app/services/employee_id.py`:
- `resolve_id_segments(db, unit)` walks up from the employee's `OrgUnit`
  to find the nearest `establishment` and (if any) `department` ancestor
  and returns their `short_code`s; if there's no department in the chain,
  the segment is the literal `"GEN"`.
- `next_employee_id(db, unit)` finds the highest existing serial for that
  establishment prefix and returns the next one, zero-padded to 4 digits.
  The serial is **per establishment**, not per establishment+department.

On promotion (`POST /api/employees/{id}/promote`): if the new office
resolves to the *same* establishment, the Employee ID is left unchanged
and a `PositionHistory` row with `event_type=promotion` is written. If it
resolves to a *different* establishment, a new ID is generated, the live
`Employee.hrms_employee_id` is updated, and **two** history rows are
written: `establishment_change` (old/new office) and
`employee_id_change` (old/new ID string) — the frontend history timeline
renders both.

### 5.2 Roles, permissions, department scoping

`app/core/permissions.py` defines ~24 permission codes grouped by area
(Directory, Employees, Structure, Verification, Configuration, Users,
System) and the exact list each of the four roles holds — read that file
directly, it is short and is the single source of truth; do not infer
permissions from the UI.

Enforcement is two-layered:
1. **Permission check** — `Depends(require_perm(SOME_PERMISSION))` on the
   route (`app/core/deps.py`). A user without the permission gets 403
   immediately.
2. **Scope check** (Department Head only) — inside the handler,
   `department_scope_ids(db, user)` returns `None` for Admin/HR/Super
   Admin (unrestricted) or a `set[int]` of allowed `OrgUnit` ids for a
   Department Head. Handlers filter queries by this set and call
   `assert_unit_in_scope()` / `assert_employee_in_scope()` before writes,
   raising 403 if the target falls outside the manager's subtree.

The frontend's `src/lib/perms.ts` (`P` object) and `src/lib/nav.ts`
mirror these codes only to decide what to *render* — every one of them is
independently re-checked server-side, so the frontend gate is a UX
convenience, never the actual security boundary.

---

## 6. Backend API surface

All routes are prefixed `/api/...` except `/`, `/docs` (Swagger UI, auto
generated — the fastest way to explore the live API), and `/api/health`.
Every router file maps to one area:

| Router | Prefix | Covers |
|---|---|---|
| `auth.py` | `/api/auth` | login, token refresh, `/me`, change/forgot/reset password |
| `org_units.py` | `/api` | `/locations` (campuses), `/org-units` (CRUD + `/tree` + per-unit detail bundling Part A + Part C) |
| `designations.py` | `/api` | `/designations` CRUD, `/posts` CRUD (sanctioned posts — API only, no dedicated UI) |
| `employees.py` | `/api/employees` | self profile (`/me`), CRUD, photo upload, `/history`, `/promote`, `/activation`, `/credentials` |
| `directory.py` | `/api` | `/directory` (list + profile), `/my-reporting`, `/reporting` CRUD, `/reporting/chart/{id}`, `/reporting/top` |
| `kyc.py` | `/api/kyc` | list/detail, edit declared info, document upload/verify, approve/reject/resubmission workflow |
| `submissions.py` | `/api/submissions` | Admin/HR/Dept-Head review queue for onboarding submissions (start-review, reject, approve → creates the real Employee) |
| `public.py` | `/api/public` | **no auth** — dropdown option lists, `/org-unit-tree`, and the applicant-facing submission lifecycle (create/edit/upload/submit) |
| `custom_fields.py` | `/api/custom-fields`, `/api/custom-documents` | HR-defined extra employee fields and required document types, optionally scoped to one org unit |
| `dashboard.py` | `/api/dashboard` | `/admin` and `/me` summary dashboards, fixed reports + export, filtered employee report + export |
| `admin_users.py` | `/api/admin` | user accounts (list/role/activation/reset-password/scope), roles & permissions CRUD, audit log |

Every non-public router requires `Authorization: Bearer <JWT>`. The JWT is
obtained from `POST /api/auth/login` and expires per
`ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`.

For the exact request/response shape of any endpoint, open
`http://localhost:8002/docs` with the backend running — it's generated
directly from the Pydantic schemas in `app/schemas/schemas.py`, so it
never drifts from reality.

---

## 7. Frontend page map

All authenticated pages live under `src/app/(app)/` and share one layout
(`(app)/layout.tsx`) that renders the sidebar (built from `nav.ts`,
filtered by the current user's permissions) and redirects to `/login` if
there's no session, or to `/change-password` if
`must_change_password` is set.

| Route | Purpose | Who sees it in nav |
|---|---|---|
| `/login` | Sign-in, forgot/reset password | anyone |
| `/submit` | Public new-employee onboarding form (no login) | anyone (linked from `/login`) |
| `/dashboard` | Role-appropriate summary (Admin/HR see university-wide stats; everyone else sees their own office) | everyone |
| `/directory`, `/directory/[id]` | University-wide (or, for a Dept Head, department-scoped) staff directory and profile/reporting-chain view | `directory:read` |
| `/organization` | The static University Organogram | `org:read` |
| `/manage/employees` | Create, edit, promote, deactivate employees; issue photo/credentials; view history timeline | `employee:read` (edit/promote/etc. individually gated) |
| `/manage/org-units`, `/manage/org-units/[id]` | Manage Colleges/Establishments/Departments/Sections; the `[id]` "Office" page shows Part A info + its Sections/Units/Cells | `structure:manage` / `org:edit` / `org:create` |
| `/manage/campuses` | Manage physical campuses/locations | `org:create` / `org:edit` |
| `/manage/designations` | Manage job-title designations (name, category, seniority rank) | `designation:manage` |
| `/manage/reporting` | Assign/remove reporting-authority links between employees | `reporting:manage` |
| `/manage/custom-fields` | Define extra employee fields / extra required document types | `custom_field:manage` |
| `/manage/reports` | Fixed + filterable reports, `.xlsx` export | `report:read` |
| `/manage/submissions` | Review queue for onboarding submissions | `submission:review` |
| `/manage/kyc` | Review queue for KYC/document verification | `kyc:verify` |
| `/manage/users` | Manage administrative accounts, roles & permissions | `user:manage` |
| `/manage/audit` | Read the audit log | `audit:read` |
| `/profile`, `/change-password` | Self-service for the signed-in user | everyone |

### Key shared frontend pieces (`src/lib/`, `src/components/`)

- **`lib/api.ts`** — `api` (authenticated fetch wrapper, attaches the JWT,
  redirects to `/login` on 401) and `publicApi` (no auth, used only by
  `/submit`). `ApiError` carries the HTTP status + server message.
- **`lib/auth.tsx`** — `AuthProvider`/`useAuth()`; holds the `CurrentUser`
  (id, role, `permissions: string[]`, `managed_org_unit_id`, etc.) fetched
  from `/api/auth/me`, exposes `can(permission)`.
- **`lib/nav.ts`** / **`lib/perms.ts`** — the sidebar structure and the
  permission-code constants, described in §5.2.
- **`components/OrgUnitSelect.tsx`** — the searchable, kind-grouped
  dropdown used everywhere an "office" needs picking (search box +
  College/Establishment/Department/Section groups) — this replaced every
  flat, ungrouped `<select>` that used to just say "Organisation".
- **`components/OrgUnitPicker.tsx`** — the 4-level cascading picker
  (College → Establishment → Department → Section) used specifically in
  the employee create/edit and promotion forms.
- **`components/UniversityOrganogram.tsx`** — the static Chancellor → VC →
  … diagram shown on `/organization`.
- **`components/DataTable.tsx`**, **`Modal.tsx`** — the generic sortable/
  searchable/paginated table and modal dialog every management page is
  built from.

---

## 8. Conventions worth knowing before you touch this codebase

- **One employee ID scheme, generated server-side only** — never construct
  an Employee ID in the frontend; always call the create/promote endpoints
  and read back whatever the server assigns.
- **Department Head scoping is enforced in every handler that touches
  employees, org units, posts, or reporting** — if you add a new endpoint
  that lists or mutates any of those, you must call
  `department_scope_ids()` / `assert_*_in_scope()` yourself; there is no
  middleware doing this automatically.
- **Nothing is hard-deleted by default.** Employees are deactivated
  (`is_active=False`, `employment_status` changed), never dropped — their
  documents and `PositionHistory` stay intact. Org units are deactivated
  the same way unless explicitly hard-deleted with `?hard=true` (only
  allowed when empty of children/staff).
- **`PositionHistory` rows are append-only** — never update or delete an
  existing row; always insert a new one.
- **The frontend never hits the backend by absolute URL** — always
  relative `/api/...` paths, so the `next.config.mjs` proxy (dev) or
  reverse proxy (production) is the only place that knows the backend's
  real address.
- **Custom fields / documents can be scoped to one org unit** — `null`
  scope means university-wide; a set scope applies to that unit and
  everything beneath it (`applicable_fields()` /
  `applicable_document_labels()` in `custom_fields.py` walk the ancestor
  chain to resolve this).

---

## 9. Known gaps / natural next steps

- No automated tests (unit or e2e) exist yet.
- No Alembic migrations — schema changes require manual `ALTER TABLE` or a
  reseed.
- No production deployment config (Dockerfile, CI pipeline) is checked in.
- `system_settings` table still exists in the schema but has no
  management UI (removed deliberately — see Project Brief §5); if a real
  need for runtime-configurable settings comes back, the table is already
  there to build against.
