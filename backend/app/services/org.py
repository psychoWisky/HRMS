"""Org-unit hierarchy services.

The AVFU hierarchy is a fixed-depth tree of ``OrgUnit`` rows:

    university  ->  college  ->  establishment | department  ->  section (section/unit/cell)

Everything here is derived from ``parent_id`` — nothing about the AVFU
structure is hard-coded.
"""
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Employee, OrgUnit, OrgUnitKind, Post, User

# Guards against a cycle introduced by bad data making traversal run forever.
MAX_CHAIN_DEPTH = 50

# Which parent kinds each kind may attach to. university has no parent —
# it is the true root. A college's parent is optional (None, or the
# university). An establishment/department may attach to a college or
# straight to the university (a central office reporting to AVFU itself).
VALID_PARENT_KINDS: dict[OrgUnitKind, set[OrgUnitKind | None]] = {
    OrgUnitKind.university: {None},
    OrgUnitKind.college: {None, OrgUnitKind.university},
    OrgUnitKind.establishment: {OrgUnitKind.college, OrgUnitKind.university},
    OrgUnitKind.department: {
        OrgUnitKind.college, OrgUnitKind.establishment, OrgUnitKind.university,
    },
    OrgUnitKind.section: {OrgUnitKind.establishment, OrgUnitKind.department, OrgUnitKind.section},
}

# A section may only nest one extra level under another section.
MAX_SECTION_DEPTH = 2


def assert_valid_parent(
    db: Session, kind: OrgUnitKind, parent: OrgUnit | None
) -> None:
    """Enforce the fixed-depth shape at create/update time (raises 400)."""
    allowed = VALID_PARENT_KINDS[kind]
    parent_kind = parent.kind if parent is not None else None
    if parent_kind not in allowed:
        names = ", ".join(sorted(k.value for k in allowed if k is not None)) or "no parent"
        raise HTTPException(
            status_code=400,
            detail=f"A {kind.value} must sit under: {names}",
        )
    if kind is OrgUnitKind.section and parent is not None and parent.kind is OrgUnitKind.section:
        depth = 1
        cur = parent
        seen = {parent.id}
        while cur.parent_id and cur.parent.kind is OrgUnitKind.section and depth < MAX_SECTION_DEPTH:
            cur = cur.parent
            if cur.id in seen:
                break
            seen.add(cur.id)
            depth += 1
        if depth >= MAX_SECTION_DEPTH:
            raise HTTPException(
                status_code=400,
                detail="Sections/units/cells may not be nested more than two levels deep",
            )


# ---------------------------------------------------------------------------
# Tree traversal
# ---------------------------------------------------------------------------
def org_unit_ancestors(db: Session, unit_id: int) -> list[OrgUnit]:
    """From the immediate parent up to the root university, in that order."""
    chain: list[OrgUnit] = []
    seen: set[int] = {unit_id}
    current = db.get(OrgUnit, unit_id)
    depth = 0
    while current is not None and current.parent_id and depth < MAX_CHAIN_DEPTH:
        if current.parent_id in seen:
            break
        parent = db.get(OrgUnit, current.parent_id)
        if parent is None:
            break
        chain.append(parent)
        seen.add(parent.id)
        current = parent
        depth += 1
    return chain


def org_unit_descendant_ids(db: Session, unit_id: int) -> set[int]:
    """The node itself plus every unit beneath it."""
    rows = db.query(OrgUnit.id, OrgUnit.parent_id).all()
    children: dict[int, list[int]] = {}
    for oid, pid in rows:
        if pid is not None:
            children.setdefault(pid, []).append(oid)
    result: set[int] = set()
    stack = [unit_id]
    while stack:
        cur = stack.pop()
        if cur in result:
            continue
        result.add(cur)
        stack.extend(children.get(cur, []))
    return result


def would_create_cycle(db: Session, unit_id: int, new_parent_id: int | None) -> bool:
    if new_parent_id is None:
        return False
    if new_parent_id == unit_id:
        return True
    return new_parent_id in org_unit_descendant_ids(db, unit_id)


def org_path(db: Session, unit: OrgUnit | None) -> str:
    """Readable breadcrumb, e.g. 'AVFU > CVSc > Directorate of Research'."""
    if unit is None:
        return ""
    parts = [a.name for a in reversed(org_unit_ancestors(db, unit.id))]
    parts.append(unit.name)
    return " > ".join(parts)


def nearest_of_kind(
    db: Session, unit: OrgUnit | None, kind: OrgUnitKind
) -> OrgUnit | None:
    """The unit itself or its nearest ancestor of the given kind."""
    if unit is None:
        return None
    if unit.kind is kind:
        return unit
    for anc in org_unit_ancestors(db, unit.id):
        if anc.kind is kind:
            return anc
    return None


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------
def employee_counts_by_unit(db: Session) -> dict[int, int]:
    """org_unit_id -> active employees assigned directly to it."""
    rows = (
        db.query(Employee.org_unit_id, func.count(Employee.id))
        .filter(Employee.is_active.is_(True), Employee.org_unit_id.isnot(None))
        .group_by(Employee.org_unit_id)
        .all()
    )
    return {uid: count for uid, count in rows}


def sanctioned_counts_by_unit(db: Session) -> dict[int, int]:
    """org_unit_id -> sanctioned post strength declared directly on it."""
    rows = (
        db.query(Post.org_unit_id, func.sum(Post.sanctioned_count))
        .filter(Post.is_active.is_(True))
        .group_by(Post.org_unit_id)
        .all()
    )
    return {uid: int(total or 0) for uid, total in rows}


# ---------------------------------------------------------------------------
# Department-Head scoping
# ---------------------------------------------------------------------------
def department_scope_ids(db: Session, user: User) -> set[int] | None:
    """Org-unit ids a user's actions are limited to.

    ``None`` = unrestricted (Admin, HR, Super Admin). A Department Head's
    scope is their assigned unit plus everything beneath it.

    A ``department_head`` account with no ``managed_org_unit_id`` assigned
    yet is scoped to nothing (an empty set) rather than being treated as
    unrestricted — an unassigned Department Head must see no data, never
    all of it, until Admin/HR assigns their department.
    """
    if user.role and user.role.code == "department_head":
        if not user.managed_org_unit_id:
            return set()
        return org_unit_descendant_ids(db, user.managed_org_unit_id)
    if not user.managed_org_unit_id:
        return None
    return org_unit_descendant_ids(db, user.managed_org_unit_id)


def assert_employee_in_scope(db: Session, user: User, employee: Employee) -> None:
    """Raise 403 if `employee` falls outside a Department Head's scope."""
    scope = department_scope_ids(db, user)
    if scope is None:
        return
    if employee.org_unit_id not in scope:
        raise HTTPException(
            status_code=403,
            detail="This employee is outside the department you manage",
        )


def assert_unit_in_scope(db: Session, user: User, unit_id: int | None) -> None:
    """Raise 403 if `unit_id` is outside a Department Head's scope."""
    scope = department_scope_ids(db, user)
    if scope is None:
        return
    if unit_id is None or unit_id not in scope:
        raise HTTPException(
            status_code=403,
            detail="That org unit is outside the department you manage",
        )
