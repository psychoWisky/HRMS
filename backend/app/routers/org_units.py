"""Org-unit hierarchy, campuses, and the office (Part A/B/C) bundle.

Reading the hierarchy is open to every authenticated employee. Creating or
editing a College / Establishment / Department needs ``structure:manage``;
Section/Unit/Cell rows use ``org:create`` / ``org:edit`` / ``org:delete``.
A Department Head may only edit units inside the subtree they manage.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user, require_perm
from app.core.permissions import (
    ORG_CREATE,
    ORG_DELETE,
    ORG_EDIT,
    ORG_READ,
    STRUCTURE_MANAGE,
)
from app.models.models import (
    Employee,
    Location,
    OrgUnit,
    OrgUnitKind,
    Post,
    User,
)
from app.schemas.schemas import (
    LocationCreate,
    LocationOut,
    LocationUpdate,
    OfficeDetail,
    OrgUnitCreate,
    OrgUnitNode,
    OrgUnitOut,
    OrgUnitUpdate,
)
from app.services.hierarchy import occupied_counts
from app.services.org import (
    assert_unit_in_scope,
    assert_valid_parent,
    department_scope_ids,
    employee_counts_by_unit,
    org_unit_descendant_ids,
    sanctioned_counts_by_unit,
    would_create_cycle,
)
from app.services.serializers import org_unit_out, post_out

router = APIRouter(prefix="/api", tags=["Org units"])

# Kinds that are a full "office" (carry Part A + Part B + Part C).
OFFICE_KINDS = {OrgUnitKind.establishment, OrgUnitKind.department}
# Kinds managed with structure:manage rather than the section permissions.
STRUCTURAL_KINDS = {
    OrgUnitKind.college,
    OrgUnitKind.establishment,
    OrgUnitKind.department,
}


def _require_read(user: User) -> None:
    if not user.has_permission(ORG_READ):
        raise HTTPException(status_code=403, detail="Not permitted")


def _perm_for(kind: OrgUnitKind, action: str) -> str:
    if kind in STRUCTURAL_KINDS:
        return STRUCTURE_MANAGE
    return {"create": ORG_CREATE, "edit": ORG_EDIT, "delete": ORG_DELETE}[action]


# ---------------------------------------------------------------------------
# Locations (campuses)
# ---------------------------------------------------------------------------
@router.get("/locations", response_model=list[LocationOut])
def list_locations(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Location)
    if not include_inactive:
        query = query.filter(Location.is_active.is_(True))
    scope = department_scope_ids(db, user)
    scoped_employee_query = db.query(Employee).filter(Employee.is_active.is_(True))
    if scope is not None:
        scoped_employee_query = scoped_employee_query.filter(Employee.org_unit_id.in_(scope))
    rows = (
        scoped_employee_query.with_entities(Employee.location_id, func.count(Employee.id))
        .group_by(Employee.location_id)
        .all()
    )
    counts = {loc_id: count for loc_id, count in rows}
    if scope is not None:
        allowed_location_ids = {
            location_id for location_id, _count in rows if location_id is not None
        }
        query = query.filter(Location.id.in_(allowed_location_ids))
    return [
        LocationOut(
            **{
                c: getattr(loc, c)
                for c in (
                    "id", "name", "code", "address", "city",
                    "district", "state", "pincode", "is_active",
                )
            },
            employee_count=counts.get(loc.id, 0),
        )
        for loc in query.order_by(Location.name).all()
    ]


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(ORG_CREATE)),
):
    if db.query(Location).filter(func.lower(Location.name) == payload.name.lower()).first():
        raise HTTPException(status_code=409, detail="A location with that name exists")
    loc = Location(**payload.model_dump())
    db.add(loc)
    db.flush()
    audit.log(db, user, "location.create", entity_type="location", entity_id=loc.id,
              summary=f"Created location {loc.name}", ip=client_ip(request))
    db.commit()
    db.refresh(loc)
    return LocationOut.model_validate(loc)


@router.put("/locations/{location_id}", response_model=LocationOut)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(ORG_EDIT)),
):
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(loc, k) for k in changes}
    for key, value in changes.items():
        setattr(loc, key, value)
    audit.log(db, user, "location.update", entity_type="location", entity_id=loc.id,
              summary=f"Updated location {loc.name}", detail=audit.diff(before, changes),
              ip=client_ip(request))
    db.commit()
    db.refresh(loc)
    return LocationOut.model_validate(loc)


# ---------------------------------------------------------------------------
# Org units
# ---------------------------------------------------------------------------
@router.get("/org-units", response_model=list[OrgUnitOut])
def list_org_units(
    kind: OrgUnitKind | None = None,
    parent_id: int | None = None,
    college_id: int | None = None,
    location_id: int | None = None,
    q: str = "",
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_read(user)
    query = db.query(OrgUnit)
    if kind is not None:
        query = query.filter(OrgUnit.kind == kind)
    if parent_id is not None:
        query = query.filter(OrgUnit.parent_id == parent_id)
    if location_id is not None:
        query = query.filter(OrgUnit.location_id == location_id)
    if q:
        query = query.filter(OrgUnit.name.ilike(f"%{q.strip()}%"))
    if not include_inactive:
        query = query.filter(OrgUnit.is_active.is_(True))

    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(OrgUnit.id.in_(scope))

    units = query.order_by(OrgUnit.sort_order, OrgUnit.name).all()
    if college_id is not None:
        keep = org_unit_descendant_ids(db, college_id)
        units = [u for u in units if u.id in keep]

    emp_counts = employee_counts_by_unit(db)
    sanc_counts = sanctioned_counts_by_unit(db)
    return [org_unit_out(db, u, emp_counts, sanc_counts) for u in units]


@router.get("/org-units/tree", response_model=list[OrgUnitNode])
def org_unit_tree(
    root_id: int | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_read(user)
    query = db.query(OrgUnit)
    if not include_inactive:
        query = query.filter(OrgUnit.is_active.is_(True))
    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(OrgUnit.id.in_(scope))
    units = query.order_by(OrgUnit.sort_order, OrgUnit.name).all()

    emp_direct = employee_counts_by_unit(db)
    sanc_direct = sanctioned_counts_by_unit(db)

    by_parent: dict[int | None, list[OrgUnit]] = {}
    for u in units:
        by_parent.setdefault(u.parent_id, []).append(u)

    def build(u: OrgUnit) -> OrgUnitNode:
        children = [build(c) for c in by_parent.get(u.id, [])]
        return OrgUnitNode(
            id=u.id,
            name=u.name,
            short_code=u.short_code,
            kind=u.kind,
            sub_kind=u.sub_kind,
            location_name=u.location.name if u.location else None,
            head_name=u.head.full_name if u.head else None,
            head_id=u.head_employee_id,
            officer_in_charge_name=(
                u.officer_in_charge.full_name if u.officer_in_charge else None
            ),
            direct_employee_count=emp_direct.get(u.id, 0),
            total_employee_count=emp_direct.get(u.id, 0)
            + sum(c.total_employee_count for c in children),
            sanctioned_count=sanc_direct.get(u.id, 0)
            + sum(c.sanctioned_count for c in children),
            is_active=u.is_active,
            children=children,
        )

    roots = (
        [u for u in units if u.id == root_id]
        if root_id is not None
        else by_parent.get(None, [])
    )
    return [build(r) for r in roots]


@router.get("/org-units/{unit_id}", response_model=OfficeDetail)
def get_org_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One unit's full detail — Part A on the row, Part B posts, Part C sections."""
    _require_read(user)
    unit = db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Org unit not found")
    assert_unit_in_scope(db, user, unit_id)

    emp_counts = employee_counts_by_unit(db)
    sanc_counts = sanctioned_counts_by_unit(db)
    base = org_unit_out(db, unit, emp_counts, sanc_counts)

    occ = occupied_counts(db)
    posts = (
        db.query(Post)
        .filter(Post.org_unit_id == unit_id, Post.is_active.is_(True))
        .all()
    )
    posts.sort(key=lambda p: (p.level_no, p.designation.rank_level if p.designation else 999))
    part_b = [post_out(p, occ.get(p.id, 0)) for p in posts]

    sections = (
        db.query(OrgUnit)
        .filter(OrgUnit.parent_id == unit_id, OrgUnit.kind == OrgUnitKind.section)
        .order_by(OrgUnit.sort_order, OrgUnit.name)
        .all()
    )
    part_c = [org_unit_out(db, s, emp_counts, sanc_counts) for s in sections]

    return OfficeDetail(**base.model_dump(), part_b=part_b, part_c=part_c)


@router.post("/org-units", response_model=OrgUnitOut, status_code=status.HTTP_201_CREATED)
def create_org_unit(
    payload: OrgUnitCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.has_permission(_perm_for(payload.kind, "create")):
        raise HTTPException(status_code=403, detail="Not permitted for this kind of unit")

    parent = None
    if payload.parent_id is not None:
        parent = db.get(OrgUnit, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent unit not found")
    assert_valid_parent(db, payload.kind, parent)
    if payload.kind is OrgUnitKind.section and payload.parent_id is not None:
        assert_unit_in_scope(db, user, payload.parent_id)

    data = payload.model_dump()
    if data.get("short_code"):
        data["short_code"] = data["short_code"].strip().upper()
    _assert_short_code_free(db, payload.kind, data.get("short_code"), None)

    unit = OrgUnit(**data)
    db.add(unit)
    db.flush()
    audit.log(db, user, "org_unit.create", entity_type="org_unit", entity_id=unit.id,
              summary=f"Created {unit.kind.value} '{unit.name}'", ip=client_ip(request))
    db.commit()
    db.refresh(unit)
    return org_unit_out(db, unit, employee_counts_by_unit(db), sanctioned_counts_by_unit(db))


@router.put("/org-units/{unit_id}", response_model=OrgUnitOut)
def update_org_unit(
    unit_id: int,
    payload: OrgUnitUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    unit = db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Org unit not found")
    if not user.has_permission(_perm_for(unit.kind, "edit")):
        raise HTTPException(status_code=403, detail="Not permitted for this kind of unit")
    assert_unit_in_scope(db, user, unit_id)

    changes = payload.model_dump(exclude_unset=True)
    new_kind = changes.get("kind", unit.kind)
    if "parent_id" in changes:
        if would_create_cycle(db, unit_id, changes["parent_id"]):
            raise HTTPException(status_code=400, detail="That parent would create a cycle")
        parent = db.get(OrgUnit, changes["parent_id"]) if changes["parent_id"] else None
        assert_valid_parent(db, new_kind, parent)
    if "short_code" in changes and changes["short_code"]:
        changes["short_code"] = changes["short_code"].strip().upper()
        _assert_short_code_free(db, new_kind, changes["short_code"], unit_id)

    before = {k: getattr(unit, k) for k in changes}
    for key, value in changes.items():
        setattr(unit, key, value)
    audit.log(db, user, "org_unit.update", entity_type="org_unit", entity_id=unit.id,
              summary=f"Updated {unit.kind.value} '{unit.name}'",
              detail=audit.diff(before, changes), ip=client_ip(request))
    db.commit()
    db.refresh(unit)
    return org_unit_out(db, unit, employee_counts_by_unit(db), sanctioned_counts_by_unit(db))


@router.delete("/org-units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_org_unit(
    unit_id: int,
    request: Request,
    hard: bool = Query(False, description="Permanently delete instead of deactivating"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    unit = db.get(OrgUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Org unit not found")
    if not user.has_permission(_perm_for(unit.kind, "delete")):
        raise HTTPException(status_code=403, detail="Not permitted for this kind of unit")
    assert_unit_in_scope(db, user, unit_id)

    staff = db.query(Employee).filter(Employee.org_unit_id == unit_id).count()
    if hard:
        if unit.children:
            raise HTTPException(status_code=400, detail="Remove child units first")
        if staff:
            raise HTTPException(
                status_code=400,
                detail=f"{staff} employee(s) are still assigned to this unit",
            )
        db.delete(unit)
        action, summary = "org_unit.delete", f"Deleted {unit.kind.value} '{unit.name}'"
    else:
        unit.is_active = False
        action, summary = "org_unit.deactivate", f"Deactivated {unit.kind.value} '{unit.name}'"

    audit.log(db, user, action, entity_type="org_unit", entity_id=unit_id,
              summary=summary, ip=client_ip(request))
    db.commit()


def _assert_short_code_free(
    db: Session, kind: OrgUnitKind, short_code: str | None, exclude_id: int | None
) -> None:
    """Short codes must be unique within a kind (they build Employee IDs)."""
    if not short_code or kind not in (OrgUnitKind.college, OrgUnitKind.establishment, OrgUnitKind.department):
        return
    clash = (
        db.query(OrgUnit)
        .filter(
            OrgUnit.kind == kind,
            func.upper(OrgUnit.short_code) == short_code,
            OrgUnit.id != (exclude_id or -1),
        )
        .first()
    )
    if clash:
        raise HTTPException(
            status_code=409,
            detail=f"Short code '{short_code}' is already used by another {kind.value}",
        )
