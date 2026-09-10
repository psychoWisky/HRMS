"""Canonical permission catalogue and the default role -> permission map.

Four roles exist:

  * ``admin``           — visible. Multiple Administrators can exist, each
                           with their own login. Full system access.
  * ``hr_admin``         — visible. Full HRMS management access.
  * ``department_head``  — visible. Access like HR, but every query is
                           additionally scoped (in the route handlers, using
                           ``services.hierarchy.department_scope_ids``) to
                           the one organisation the account is assigned to
                           manage (``User.managed_org_id``) and everything
                           beneath it.
  * ``super_admin``      — HIDDEN technical role. Unrestricted access, but
                           excluded from the Roles & Users management screen
                           (see ``app/routers/admin_users.py``). Not seeded
                           onto any account by default; intended only for
                           manual system/developer administration.

Permissions themselves are boolean and university-wide; department-level
restriction for ``department_head`` is enforced separately, in the routers,
because "can edit employees" and "can edit employees in my department only"
are the same capability at different scopes, not different permissions.
"""

# --- permission codes -------------------------------------------------------
# directory / read
DIRECTORY_READ = "directory:read"
ORG_READ = "org:read"
EMPLOYEE_READ = "employee:read"
REPORT_READ = "report:read"

# self-service (for the administrative users who do hold logins)
PROFILE_EDIT_OWN = "profile:edit_own"
PASSWORD_CHANGE_OWN = "password:change_own"

# employee management
EMPLOYEE_CREATE = "employee:create"
EMPLOYEE_EDIT = "employee:edit"
EMPLOYEE_DELETE = "employee:delete"
EMPLOYEE_PROMOTE = "employee:promote"

# hierarchy management: covers both Departments (academic) and
# Establishments (administrative) — the two peer categories every real
# AVFU unit falls into — plus their Sections/Units/Cells and campuses.
# Only Admin/HR ever hold this; Department Head does not.
ORG_CREATE = "org:create"
ORG_EDIT = "org:edit"
ORG_DELETE = "org:delete"
STRUCTURE_MANAGE = "structure:manage"

# designation & post management
DESIGNATION_MANAGE = "designation:manage"
POST_MANAGE = "post:manage"

# reporting hierarchy
REPORTING_MANAGE = "reporting:manage"

# document verification
SUBMISSION_REVIEW = "submission:review"
KYC_VERIFY = "kyc:verify"

# configurable employee fields & document requirements
CUSTOM_FIELD_MANAGE = "custom_field:manage"

# users, roles, credentials
USER_MANAGE = "user:manage"
USER_RESET_PASSWORD = "user:reset_password"
ROLE_MANAGE = "role:manage"

# system
AUDIT_READ = "audit:read"
SETTINGS_MANAGE = "settings:manage"


PERMISSIONS: list[tuple[str, str, str]] = [
    # (code, group, description)
    (DIRECTORY_READ, "Directory", "View the university-wide employee directory"),
    (ORG_READ, "Directory", "View the establishment/department hierarchy"),
    (EMPLOYEE_READ, "Directory", "View employee records"),
    (REPORT_READ, "Reports", "Generate and view reports"),
    (PROFILE_EDIT_OWN, "Self service", "Edit own contact details"),
    (PASSWORD_CHANGE_OWN, "Self service", "Change own password"),
    (EMPLOYEE_CREATE, "Employees", "Create employee records"),
    (EMPLOYEE_EDIT, "Employees", "Edit employee records and assignments"),
    (EMPLOYEE_DELETE, "Employees", "Deactivate or delete employee records"),
    (EMPLOYEE_PROMOTE, "Employees", "Promote an employee, preserving history"),
    (ORG_CREATE, "Structure", "Create sections, units or cells"),
    (ORG_EDIT, "Structure", "Edit sections, units or cells"),
    (ORG_DELETE, "Structure", "Deactivate sections, units or cells"),
    (STRUCTURE_MANAGE, "Structure", "Create and edit Departments and Establishments"),
    (DESIGNATION_MANAGE, "Structure", "Manage designations"),
    (POST_MANAGE, "Structure", "Manage sanctioned posts and vacancies"),
    (REPORTING_MANAGE, "Structure", "Modify the reporting hierarchy"),
    (
        SUBMISSION_REVIEW,
        "Verification",
        "Review new-employee document submissions and admit them into the HRMS",
    ),
    (KYC_VERIFY, "Verification", "Verify, approve or reject employee documents"),
    (
        CUSTOM_FIELD_MANAGE,
        "Configuration",
        "Create custom employee fields and document requirements",
    ),
    (USER_MANAGE, "Users", "Create and manage administrative user accounts"),
    (USER_RESET_PASSWORD, "Users", "Reset another user's password"),
    (ROLE_MANAGE, "Users", "Manage roles and permissions"),
    (AUDIT_READ, "System", "Read audit logs"),
    (SETTINGS_MANAGE, "System", "Manage system configuration"),
]

ALL_PERMISSION_CODES = [p[0] for p in PERMISSIONS]

# HR: full operational authority over HRMS data and document verification.
HR_ADMIN_PERMISSIONS = [
    c for c in ALL_PERMISSION_CODES if c not in (ROLE_MANAGE, SETTINGS_MANAGE)
]

# Admin: everything.
ADMIN_PERMISSIONS = list(ALL_PERMISSION_CODES)

# Department Head: HR-like operational authority, but every one of these is
# scoped to the org unit they manage (their subtree) in the route handlers.
# They may manage the structure and reporting *inside* their department
# (Sections/Units/Cells, sanctioned posts, reporting links) — the handlers
# reject anything outside their subtree — but they cannot create or edit a
# College / Establishment / Department (``structure:manage``), nor touch
# designations, custom fields, users/roles or system settings.
DEPARTMENT_HEAD_PERMISSIONS = [
    DIRECTORY_READ,
    ORG_READ,
    EMPLOYEE_READ,
    EMPLOYEE_EDIT,
    REPORT_READ,
    PROFILE_EDIT_OWN,
    PASSWORD_CHANGE_OWN,
    SUBMISSION_REVIEW,
    KYC_VERIFY,
    ORG_CREATE,
    ORG_EDIT,
    ORG_DELETE,
    POST_MANAGE,
    REPORTING_MANAGE,
]

# Super Admin: unrestricted, hidden.
SUPER_ADMIN_PERMISSIONS = list(ALL_PERMISSION_CODES)


DEFAULT_ROLES: list[tuple[str, str, str, list[str], bool, bool]] = [
    # (code, name, description, permissions, is_system, is_hidden)
    (
        "admin",
        "Administrator",
        "Full system access. Multiple Administrators can exist.",
        ADMIN_PERMISSIONS,
        True,
        False,
    ),
    (
        "hr_admin",
        "HR",
        "Full HRMS management access",
        HR_ADMIN_PERMISSIONS,
        True,
        False,
    ),
    (
        "department_head",
        "Department Head",
        "HR-like access restricted to one assigned department",
        DEPARTMENT_HEAD_PERMISSIONS,
        True,
        False,
    ),
    (
        "super_admin",
        "Super Admin",
        "Hidden technical role for system/developer administration",
        SUPER_ADMIN_PERMISSIONS,
        True,
        True,
    ),
]
