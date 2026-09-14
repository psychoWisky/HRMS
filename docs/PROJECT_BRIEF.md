# AVFU HRMS — Project Brief

**Client:** Assam Veterinary and Fishery University (AVFU)
**Purpose:** One centralised system to manage every employee, office and
reporting line across the university, replacing scattered paper/Excel
records kept independently by each establishment and college.

This document explains **what the system does and why**, in plain terms,
for anyone picking up the project — a new developer, a client stakeholder,
or a future maintainer. For technical setup and codebase internals, see
[`docs/DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md).

---

## 1. The problem this solves

AVFU is one university made of three constituent colleges (CVSc, CFSc,
LCVSc) plus the university's own administrative directorates (Registrar,
Comptroller, Directorate of Research, etc.). Historically, each office
tracked its own staff, sanctioned posts, and reporting lines on paper or in
local spreadsheets — submitted to the university on a standard paper form
(see §6, "Source documents").

The HRMS digitises that exact structure: one login system, one employee
record per person no matter which office they sit in, and one place to see
who reports to whom, which posts are sanctioned/filled/vacant, and whose
KYC documents have been verified.

## 2. Who uses it

Three visible roles, plus one hidden technical role:

| Role | Who | Can do |
|---|---|---|
| **Administrator** | University IT/registrar staff | Everything — the only role that can manage other users' roles |
| **HR** | University HR office | Everything except managing roles/permissions |
| **Department Head** | The head of one specific establishment/department | Everything HR can do, but **only within their own office and everything beneath it** — cannot see or touch other departments, cannot restructure the university (add/edit Colleges/Establishments/Departments) |
| *Super Admin (hidden)* | Developers only | Unrestricted; never appears in the Users screen; not assigned to anyone by default |

There is **one login system** for the whole university — no separate
per-campus logins. Ordinary employees (Professors, clerks, etc.) do **not**
get a login by default; only Admin/HR/Department Head accounts do.

## 3. The core flow

```
University (AVFU)
 └─ College (CVSc / CFSc / LCVSc)
     ├─ Establishment (an administrative office — e.g. "Directorate of Research")
     │   └─ Section / Unit / Cell   (e.g. "Academic Cell (UG)")
     └─ Department (an academic teaching department — e.g. "Dept. of Anatomy")
         └─ Section / Unit / Cell

Every Employee belongs to exactly one of these places (any level),
holds one Designation (job title, e.g. "Professor"), and optionally
one sanctioned Post.
```

**When a new campus/college/establishment/department opens**, an
Administrator or HR user adds it directly in the app (Administration →
Organisation Structure) — no code change or developer involvement needed.

## 4. What the system tracks, end to end

1. **The org structure itself** — Colleges, Establishments, Departments,
   Sections/Units/Cells, each with a Head of Office, reporting authority,
   and contact details. Fully editable by Admin/HR; a Department Head can
   edit only inside their own office.
2. **Employees** — one record per person: name, designation, which office
   they sit in, pay scale, contact details, photo, employment status
   (active/inactive/retired/transferred). A permanent **HRMS Employee ID**
   is generated automatically in the form `AVFU/<Establishment
   code>/<Department code or GEN>/<serial>`.
3. **Promotion & history** — every designation change, pay-scale change, or
   move between offices is recorded as a permanent timeline entry on the
   employee (never overwritten). Moving to a different Establishment mints
   a *new* Employee ID automatically; the old one stays visible in the
   history.
4. **Reporting hierarchy** — who reports to whom, editable per employee,
   with cycle protection (you cannot make A report to B if B already
   reports to A, directly or indirectly).
5. **KYC / document verification** — Aadhaar, PAN, qualification
   certificates and any HR-defined extra documents, each individually
   markable as checked, with an approve/reject/resubmission workflow and a
   full audit history per record.
6. **New-employee self-service onboarding** — a public link (no login)
   where a new joinee fills in their own details and uploads their
   documents, gets a reference code to track status, and is only added to
   the real employee list once HR/Admin/Department Head reviews and
   approves the submission.
7. **Directory & search** — every authenticated user can browse the
   university-wide staff directory (Department Heads see only their own
   department); click through to see anyone's reporting chain and direct
   reports.
8. **Reports** — fixed reports (staff by office, by campus, sanctioned
   posts & vacancies, KYC status, reporting hierarchy) and a combinable
   filtered employee report, both downloadable as `.xlsx`.
9. **Audit log** — every meaningful action (who created/edited/promoted/
   deactivated what, and when) is recorded and readable by Admin/HR.

## 5. Deliberately *not* in scope

To keep the system focused on its actual purpose (one org chart + one
employee record + document verification), the following were built,
evaluated, and then **removed** as unnecessary complexity for this client:

- **Sanctioned-post management screen** — the underlying data (from Part B
  of the source documents) still exists and drives the vacancy counts on
  the dashboard, but there is no dedicated "Posts & Vacancies" page to
  edit it live; it is set once via the seed data.
- **System Settings screen** — no in-app configuration panel; the handful
  of values it held (university name, password length) are fixed in code.
- **New-joinee access tokens** — early versions gated the public
  onboarding form behind an admin-issued token per applicant. This was
  removed; the form is open (no token) and every submission still requires
  HR/Admin/Department Head review before anyone is added as a real
  employee.

## 6. Source documents

The organisational structure (colleges, establishments, sanctioned posts,
sections/units/cells) was transcribed from AVFU's own prescribed
submission format, one form per office:

- **Part A — General Information**: office name, Head of Office, reporting
  authority, HRMS contact person.
- **Part B — Organizational Hierarchy**: Designation → To Report → Number
  of Sanctioned Posts → Remarks, level by level.
- **Part C — Sections/Units/Cells under the Office**: name,
  officer-in-charge, number of employees.

Plus a fixed **University Organogram** (Chancellor → Vice-Chancellor →
Registrar/Financial Officer → Deans/Directors/Controller of
Examination/Librarian → their sub-roles), which is shown as a static
diagram on the public hierarchy page since it reflects the university's
statute, not day-to-day data.

## 7. Current status

The core system — org structure, employees, promotions/history, reporting,
KYC, onboarding, directory, reports, audit log, role/permission
management — is built and working. The database runs on PostgreSQL. See
[`docs/DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) for how to run it, the
exact API surface, and the codebase map.
