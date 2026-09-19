"""Import the AVFU organisational master data into the HRMS database.

Run:  python seed.py            (drops and rebuilds every table)
      python seed.py --keep     (upsert into an existing database)

The client-supplied structure lives in ``app/data/avfu_master_data.py`` and
is loaded from there — none of it is hard-coded into the API or the
frontend, and Admin/HR can change all of it later through the web interface.
"""
import argparse
import re
import sys
import unicodedata

from sqlalchemy.orm import Session

from app.core.auto_migrate import sync_enum_types, sync_missing_columns
from app.core.database import Base, SessionLocal, engine
from app.core.permissions import DEFAULT_ROLES, PERMISSIONS
from app.core.security import hash_password
from app.data import avfu_master_data as md
from app.models.models import (
    KYC,
    Designation,
    DesignationCategory,
    Employee,
    KYCStatus,
    Location,
    OrgUnit,
    OrgUnitKind,
    Permission,
    PositionEventType,
    PositionHistory,
    Post,
    ReportingRelationship,
    Role,
    SystemSetting,
    User,
)

ADMIN_EMAIL = "admin@avfu.ac.in"
ADMIN_PASSWORD = "Admin@1234"
HR_EMAIL = "hr@avfu.ac.in"
HR_PASSWORD = "HrAdmin@1234"
DEPARTMENT_HEAD_PASSWORD = "DeptHead@1234"

# One representative Department Head demo login. (employee_full_name, managed org-unit key)
DEPARTMENT_HEAD_DEMOS = [
    ("Dr. Ananya Baruah", "dor"),
]

# Demo employees so the directory, reporting and department-scoping are
# testable out of the box. (full_name, designation_name, org_unit_key, phone)
DEMO_PEOPLE = [
    ("Dr. Ananya Baruah", "Director of Research", "dor", "9864000001"),
    ("Dr. Pranab Das", "Professor", "dor", "9864000002"),
    ("Rekha Kalita", "Junior Administrative Assistant", "dor", "9864000003"),
    ("Bhaskar Nath", "Computer Assistant", "dor", "9864000004"),
    ("Dr. Nabajit Hazarika", "Deputy Director of Research", "grs_burnihat", "9864000005"),
    ("Junmoni Bora", "Junior Administrative Assistant", "grs_burnihat", "9864000006"),
    ("Dr. Hiren Sarma", "Director of Extension Education", "doee", "9864000007"),
    ("Momi Deka", "Computer Assistant", "doee", "9864000008"),
    ("Dr. Kamal Choudhury", "Registrar", "registrar", "9864000009"),
]

DEMO_REPORTING = [
    ("Dr. Pranab Das", "Dr. Ananya Baruah"),
    ("Rekha Kalita", "Dr. Ananya Baruah"),
    ("Bhaskar Nath", "Dr. Ananya Baruah"),
    ("Dr. Nabajit Hazarika", "Dr. Ananya Baruah"),
    ("Junmoni Bora", "Dr. Nabajit Hazarika"),
    ("Momi Deka", "Dr. Hiren Sarma"),
]

TITLES = {"dr", "mr", "mrs", "ms", "sri", "smt", "prof"}


def slug_email(full_name: str, taken: set[str]) -> str:
    cleaned = unicodedata.normalize("NFKD", full_name)
    words = [w.strip(".") for w in re.split(r"[\s.]+", cleaned) if w.strip(".")]
    words = [w for w in words if w.lower().strip(".") not in TITLES]
    parts = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in words]
    parts = [p for p in parts if p]
    base = ".".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "staff")
    email = f"{base}@avfu.ac.in"
    counter = 2
    while email in taken:
        email = f"{base}{counter}@avfu.ac.in"
        counter += 1
    taken.add(email)
    return email


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
def seed_rbac(db: Session) -> dict[str, Role]:
    by_code: dict[str, Permission] = {}
    for code, group, description in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm is None:
            perm = Permission(code=code, group=group, description=description)
            db.add(perm)
        else:
            perm.group, perm.description = group, description
        by_code[code] = perm
    db.flush()

    roles: dict[str, Role] = {}
    for code, name, description, permission_codes, is_system, is_hidden in DEFAULT_ROLES:
        role = db.query(Role).filter(Role.code == code).first()
        if role is None:
            role = Role(code=code, name=name, description=description)
            db.add(role)
        role.name, role.description = name, description
        role.is_system = is_system
        role.is_hidden = is_hidden
        role.permissions = [by_code[c] for c in permission_codes if c in by_code]
        roles[code] = role
    db.flush()
    return roles


# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------
def seed_locations(db: Session) -> dict[str, Location]:
    result: dict[str, Location] = {}
    for item in md.LOCATIONS:
        key = item["key"]
        loc = db.query(Location).filter(Location.name == item["name"]).first()
        if loc is None:
            loc = Location(**{k: v for k, v in item.items() if k != "key"})
            db.add(loc)
        result[key] = loc
    db.flush()
    return result


def seed_designations(db: Session) -> dict[str, Designation]:
    result: dict[str, Designation] = {}
    for name, short_name, category, rank in md.DESIGNATIONS:
        d = db.query(Designation).filter(Designation.name == name).first()
        if d is None:
            d = Designation(name=name)
            db.add(d)
        d.short_name = short_name
        d.category = DesignationCategory(category)
        d.rank_level = rank
        result[name] = d
    db.flush()
    return result


def seed_org_units(
    db: Session, locations: dict[str, Location]
) -> dict[str, OrgUnit]:
    """University -> Colleges -> Establishments / Departments -> Sections, in dependency order."""
    units: dict[str, OrgUnit] = {}

    def _loc_id(k):
        return locations[k].id if k in locations else None

    # 0. University — the one true root of the tree.
    for order, (key, name, short, loc) in enumerate(md.ORG_UNIVERSITY):
        u = OrgUnit(
            kind=OrgUnitKind.university,
            name=name,
            short_code=short.upper(),
            code=key,
            location_id=_loc_id(loc),
            sort_order=order,
        )
        db.add(u)
        units[key] = u
    db.flush()

    # 1. Colleges
    for order, (key, name, short, parent_key, loc) in enumerate(md.ORG_COLLEGES):
        u = OrgUnit(
            kind=OrgUnitKind.college,
            name=name,
            short_code=short.upper(),
            code=key,
            location_id=_loc_id(loc),
            sort_order=order,
        )
        db.add(u)
        units[key] = u
    db.flush()
    for key, _n, _s, parent_key, _l in md.ORG_COLLEGES:
        if parent_key:
            units[key].parent_id = units[parent_key].id
    db.flush()

    # 2. Establishments
    for order, (key, name, short, college_key, loc) in enumerate(md.ORG_ESTABLISHMENTS):
        u = OrgUnit(
            kind=OrgUnitKind.establishment,
            name=name,
            short_code=short.upper(),
            code=key,
            parent_id=units[college_key].id,
            location_id=_loc_id(loc),
            sort_order=order,
        )
        db.add(u)
        units[key] = u
    db.flush()

    # 3. Departments (academic) — parented to their college
    for order, (key, name, short, college_key) in enumerate(md.ORG_DEPARTMENTS):
        u = OrgUnit(
            kind=OrgUnitKind.department,
            name=name,
            short_code=short.upper(),
            code=key,
            parent_id=units[college_key].id,
            sort_order=1000 + order,
        )
        db.add(u)
        units[key] = u
        # also index by (college, name) for demo/section lookups
        units[f"{college_key}:{name}"] = u
    db.flush()

    # 4. Sections / units / cells — parented to an establishment (or a college's Dean)
    for order, (key, name, sub_kind, parent_key, officer, headcount) in enumerate(
        md.ORG_SECTIONS
    ):
        resolved = parent_key
        if parent_key in md.COLLEGE_KEY_TO_DEAN_EST:
            resolved = md.COLLEGE_KEY_TO_DEAN_EST[parent_key]
        parent = units.get(resolved)
        if parent is None:
            # Unknown parent key in the source data — skip rather than crash.
            continue
        u = OrgUnit(
            kind=OrgUnitKind.section,
            sub_kind=sub_kind if sub_kind in {"section", "unit", "cell"} else "section",
            name=name,
            code=key,
            parent_id=parent.id,
            headcount_note=headcount,
            sort_order=2000 + order,
        )
        db.add(u)
        units[key] = u
        units.setdefault(f"__oic__{key}", officer)  # remember officer name for later
    db.flush()
    return units


def seed_posts(
    db: Session,
    units: dict[str, OrgUnit],
    designations: dict[str, Designation],
) -> int:
    count = 0
    for parent_key, desig_name, level_no, sanctioned, vacant, note, remarks in md.ORG_POSTS:
        resolved = parent_key
        if parent_key in md.COLLEGE_KEY_TO_DEAN_EST:
            resolved = md.COLLEGE_KEY_TO_DEAN_EST[parent_key]
        unit = units.get(resolved)
        designation = designations.get(desig_name)
        if unit is None or designation is None:
            continue
        exists = (
            db.query(Post)
            .filter(Post.org_unit_id == unit.id, Post.designation_id == designation.id)
            .first()
        )
        if exists is None:
            db.add(
                Post(
                    org_unit_id=unit.id,
                    designation_id=designation.id,
                    level_no=level_no,
                    level_label=str(level_no) if level_no else "",
                    sanctioned_count=sanctioned,
                    reported_vacant_count=vacant,
                    reports_to_note=note,
                    remarks=remarks,
                )
            )
            count += 1
    db.flush()
    return count


def seed_people(
    db: Session,
    units: dict[str, OrgUnit],
    designations: dict[str, Designation],
) -> dict[str, Employee]:
    taken_emails = {u.email for u in db.query(User).all()}
    people: dict[str, Employee] = {}

    # Per-establishment running serial for AVFU/<EST>/<GEN>/#### IDs.
    serials: dict[str, int] = {}

    def _est_short_for(unit: OrgUnit) -> str:
        cur = unit
        seen = set()
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            if cur.kind is OrgUnitKind.establishment:
                return (cur.short_code or "GEN").upper()
            if cur.parent_id is None:
                return (cur.short_code or "GEN").upper()
            cur = db.get(OrgUnit, cur.parent_id)
        return "GEN"

    for full_name, desig_name, unit_key, phone in DEMO_PEOPLE:
        unit = units.get(unit_key)
        if unit is None:
            continue
        est_short = _est_short_for(unit)
        serials[est_short] = serials.get(est_short, 0) + 1
        hrms_id = f"AVFU/{est_short}/GEN/{serials[est_short]:04d}"

        emp = Employee(hrms_employee_id=hrms_id)
        db.add(emp)
        emp.full_name = full_name
        emp.designation_id = (
            designations[desig_name].id if desig_name in designations else None
        )
        emp.org_unit_id = unit.id
        emp.location_id = unit.location_id
        emp.phone = phone
        db.flush()

        emp.official_email = slug_email(full_name, taken_emails)
        db.add(
            PositionHistory(
                employee_id=emp.id,
                event_type=PositionEventType.joining,
                new_designation_id=emp.designation_id,
                new_org_unit_id=unit.id,
                new_employee_code=hrms_id,
                remarks="Joined AVFU",
            )
        )
        if db.query(KYC).filter(KYC.employee_id == emp.id).first() is None:
            db.add(KYC(employee_id=emp.id, status=KYCStatus.not_started))
        people[full_name] = emp
    db.flush()
    return people


def seed_reporting(db: Session, people: dict[str, Employee]) -> int:
    created = 0
    for employee_name, manager_name in md.REPORTING + DEMO_REPORTING:
        emp = people.get(employee_name)
        manager = people.get(manager_name)
        if emp is None or manager is None or emp.id == manager.id:
            continue
        exists = (
            db.query(ReportingRelationship)
            .filter(
                ReportingRelationship.employee_id == emp.id,
                ReportingRelationship.reports_to_id == manager.id,
            )
            .first()
        )
        if exists is None:
            db.add(
                ReportingRelationship(
                    employee_id=emp.id, reports_to_id=manager.id, is_primary=True
                )
            )
            created += 1
    db.flush()
    return created


def seed_settings(db: Session) -> None:
    for key, value, description in md.SYSTEM_SETTINGS:
        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if s is None:
            s = SystemSetting(key=key)
            db.add(s)
        s.value = value
        s.description = description
    db.flush()


def seed_admin_accounts(
    db: Session, roles: dict[str, Role], units: dict[str, OrgUnit]
) -> None:
    specs = [
        (ADMIN_EMAIL, ADMIN_PASSWORD, "admin", "AVFU HRMS Administrator",
         "avfu", "AVFU-ADMIN-01"),
        (HR_EMAIL, HR_PASSWORD, "hr_admin", "AVFU HR Administrator",
         "registrar", "AVFU-ADMIN-02"),
    ]
    for email, password, role_code, display_name, unit_key, hrms_id in specs:
        account = db.query(User).filter(User.email == email).first()
        if account is None:
            account = User(email=email)
            db.add(account)
        account.hashed_password = hash_password(password)
        account.role_id = roles[role_code].id
        account.is_active = True
        account.must_change_password = False
        db.flush()

        emp = db.query(Employee).filter(Employee.user_id == account.id).first()
        if emp is None:
            emp = Employee(hrms_employee_id=hrms_id)
            db.add(emp)
            emp.user_id = account.id
        emp.full_name = display_name
        emp.official_email = email
        unit = units.get(unit_key)
        emp.org_unit_id = unit.id if unit else None
        emp.location_id = unit.location_id if unit else None
        db.flush()
        if db.query(KYC).filter(KYC.employee_id == emp.id).first() is None:
            db.add(KYC(employee_id=emp.id, status=KYCStatus.not_started))
    db.flush()


def seed_department_heads(
    db: Session,
    roles: dict[str, Role],
    units: dict[str, OrgUnit],
    people: dict[str, Employee],
) -> tuple[int, list[tuple[str, str]]]:
    count = 0
    lines: list[tuple[str, str]] = []
    dept_head_role = roles["department_head"]
    for full_name, unit_key in DEPARTMENT_HEAD_DEMOS:
        emp = people.get(full_name)
        unit = units.get(unit_key)
        if emp is None or unit is None:
            continue
        email = emp.official_email
        account = db.query(User).filter(User.email == email).first()
        if account is None:
            account = User(email=email)
            db.add(account)
        account.hashed_password = hash_password(DEPARTMENT_HEAD_PASSWORD)
        account.role_id = dept_head_role.id
        account.managed_org_unit_id = unit.id
        account.is_active = True
        account.must_change_password = True
        db.flush()
        emp.user_id = account.id
        count += 1
        lines.append((email, unit.name))
    db.flush()
    return count, lines


# ---------------------------------------------------------------------------
def main(keep: bool = False) -> None:
    if not keep:
        print("Rebuilding schema...")
        reset_database()
    else:
        Base.metadata.create_all(bind=engine)
        sync_enum_types(engine, Base)
        sync_missing_columns(engine, Base)

    db = SessionLocal()
    try:
        print("Seeding roles and permissions...")
        roles = seed_rbac(db)

        print("Seeding campuses...")
        locations = seed_locations(db)

        print("Seeding designations...")
        designations = seed_designations(db)

        print("Seeding org units (colleges -> establishments/departments -> sections)...")
        units = seed_org_units(db, locations)

        print("Seeding Part B sanctioned posts...")
        post_count = seed_posts(db, units, designations)

        print("Seeding demo employees...")
        people = seed_people(db, units, designations)

        print("Seeding reporting hierarchy...")
        reporting_count = seed_reporting(db, people)

        seed_settings(db)
        seed_admin_accounts(db, roles, units)

        print("Seeding demo Department Head login...")
        dept_head_count, dept_head_lines = seed_department_heads(
            db, roles, units, people
        )

        universities = sum(1 for u in units.values() if getattr(u, "kind", None) == OrgUnitKind.university)
        colleges = sum(1 for u in units.values() if getattr(u, "kind", None) == OrgUnitKind.college)
        establishments = sum(
            1 for u in units.values() if getattr(u, "kind", None) == OrgUnitKind.establishment
        )
        departments = sum(
            1 for u in units.values() if getattr(u, "kind", None) == OrgUnitKind.department
        )
        sections = sum(
            1 for u in units.values() if getattr(u, "kind", None) == OrgUnitKind.section
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("\nSeed complete.")
    print(f"  Campuses / locations : {len(locations)}")
    print(f"  Universities         : {universities}")
    print(f"  Colleges             : {colleges}")
    print(f"  Establishments       : {establishments}")
    print(f"  Academic departments : {departments}")
    print(f"  Sections/units/cells : {sections}")
    print(f"  Designations         : {len(designations)}")
    print(f"  Part B post rows     : {post_count}")
    print(f"  Demo employees       : {len(people)}")
    print(f"  Reporting links      : {reporting_count}")
    print(f"  Login accounts       : {2 + dept_head_count} (admin + HR + {dept_head_count} Department Head)")
    print("\nSign in with:")
    print(f"  Administrator   : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  HR              : {HR_EMAIL} / {HR_PASSWORD}")
    for email, unit_name in dept_head_lines:
        print(
            f"  Department Head : {email} / {DEPARTMENT_HEAD_PASSWORD}  "
            f"(manages {unit_name}, forced password change on first sign-in)"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Upsert into the existing database instead of rebuilding it",
    )
    args = parser.parse_args()
    try:
        main(keep=args.keep)
    except Exception as exc:  # pragma: no cover
        print(f"\nSeed failed: {exc}", file=sys.stderr)
        raise
