"""Employee directory and reporting hierarchy.

Admin, HR and Super Admin read the whole university directory. A Department
Head reads only the employees of the department they manage (their
``managed_org`` node and everything beneath it) — every directory list and
profile is filtered to that scope. Only Admin/HR can change the hierarchy.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import (
    client_ip,
    get_current_employee,
    get_current_user,
    require_perm,
)
from app.core.permissions import DIRECTORY_READ, REPORTING_MANAGE
from app.models.models import (
    Employee,
    ReportingRelationship,
    ReportingType,
    User,
)
from app.schemas.schemas import (
    EmployeeSummary,
    ReportingCreate,
    ReportingOut,
    ReportingStructure,
)
from app.services.hierarchy import (
    direct_reports,
    primary_manager_id,
    reporting_chain,
    would_create_reporting_cycle,
)
from app.services.org import (
    department_scope_ids,
    org_unit_descendant_ids as org_descendant_ids,
)
from app.services.serializers import employee_summary

router = APIRouter(prefix="/api", tags=["Directory & Reporting"])


def _require_directory(user: User) -> None:
    if not user.has_permission(DIRECTORY_READ):
        raise HTTPException(status_code=403, detail="Not permitted")


def _assert_employee_visible(db: Session, user: User, emp: Employee) -> None:
    """A Department Head may only open profiles inside the department they manage."""
    scope = department_scope_ids(db, user)
    if scope is not None and emp.org_unit_id not in scope:
        raise HTTPException(
            status_code=403,
            detail="This employee is outside the department you manage",
        )


def _reporting_out(db: Session, link: ReportingRelationship) -> ReportingOut:
    manager = link.manager
    return ReportingOut(
        id=link.id,
        employee_id=link.employee_id,
        employee_name=link.employee.full_name if link.employee else "",
        reports_to_id=link.reports_to_id,
        reports_to_name=manager.full_name if manager else "",
        reports_to_designation=(
            manager.designation.name if manager and manager.designation else None
        ),
        relationship_type=link.relationship_type,
        is_primary=link.is_primary,
        effective_from=link.effective_from,
        effective_to=link.effective_to,
    )


# ---------------------------------------------------------------------------
# Directory (read-only for every authenticated employee)
# ---------------------------------------------------------------------------
@router.get("/directory", response_model=list[EmployeeSummary])
def directory(
    q: str = "",
    org_unit_id: int | None = None,
    include_subtree: bool = True,
    location_id: int | None = None,
    designation_id: int | None = None,
    limit: int = Query(300, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_directory(user)

    query = db.query(Employee).filter(Employee.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Employee.full_name.ilike(like),
                Employee.hrms_employee_id.ilike(like),
                Employee.official_email.ilike(like),
            )
        )

    # A Department Head only ever sees their own department's employees.
    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(Employee.org_unit_id.in_(scope))

    if org_unit_id is not None:
        ids = (
            org_descendant_ids(db, org_unit_id)
            if include_subtree
            else {org_unit_id}
        )
        if scope is not None:
            ids &= scope
        query = query.filter(Employee.org_unit_id.in_(ids))
    if location_id is not None:
        query = query.filter(Employee.location_id == location_id)
    if designation_id is not None:
        query = query.filter(Employee.designation_id == designation_id)

    rows = query.order_by(Employee.full_name).offset(offset).limit(limit).all()
    return [employee_summary(db, e) for e in rows]


@router.get("/directory/{employee_id}", response_model=ReportingStructure)
def directory_profile(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The directory-permitted profile: who they are and where they sit."""
    _require_directory(user)
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _assert_employee_visible(db, user, emp)

    manager_id = primary_manager_id(db, emp.id)
    manager = db.get(Employee, manager_id) if manager_id else None
    extra_links = (
        db.query(ReportingRelationship)
        .filter(
            ReportingRelationship.employee_id == emp.id,
            ReportingRelationship.is_primary.is_(False),
            ReportingRelationship.effective_to.is_(None),
        )
        .all()
    )

    return ReportingStructure(
        employee=employee_summary(db, emp),
        reports_to=employee_summary(db, manager, include_manager=False)
        if manager
        else None,
        additional_authorities=[
            employee_summary(db, link.manager, include_manager=False)
            for link in extra_links
            if link.manager
        ],
        reporting_chain=[
            employee_summary(db, m, include_manager=False)
            for m in reporting_chain(db, emp.id)
        ],
        direct_reports=[
            employee_summary(db, r, include_manager=False)
            for r in direct_reports(db, emp.id)
        ],
    )


@router.get("/my-reporting", response_model=ReportingStructure)
def my_reporting_structure(
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee),
):
    return directory_profile(emp.id, db=db, user=emp.user)


# ---------------------------------------------------------------------------
# Reporting hierarchy management (Admin/HR only)
# ---------------------------------------------------------------------------
@router.get("/reporting", response_model=list[ReportingOut])
def list_reporting(
    employee_id: int | None = None,
    reports_to_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_directory(user)
    query = db.query(ReportingRelationship).filter(
        ReportingRelationship.effective_to.is_(None)
    )
    if employee_id is not None:
        query = query.filter(ReportingRelationship.employee_id == employee_id)
    if reports_to_id is not None:
        query = query.filter(ReportingRelationship.reports_to_id == reports_to_id)

    # A Department Head only sees links whose subordinate is in their department.
    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.join(
            Employee, Employee.id == ReportingRelationship.employee_id
        ).filter(Employee.org_unit_id.in_(scope))

    return [_reporting_out(db, link) for link in query.all()]


@router.post(
    "/reporting", response_model=ReportingOut, status_code=status.HTTP_201_CREATED
)
def set_reporting(
    payload: ReportingCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(REPORTING_MANAGE)),
):
    employee = db.get(Employee, payload.employee_id)
    manager = db.get(Employee, payload.reports_to_id)
    if employee is None or manager is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.id == manager.id:
        raise HTTPException(
            status_code=400, detail="An employee cannot report to themselves"
        )

    # A Department Head may only set reporting for their own department's staff.
    scope = department_scope_ids(db, user)
    if scope is not None and employee.org_unit_id not in scope:
        raise HTTPException(
            status_code=403,
            detail="This employee is outside the department you manage",
        )
    if would_create_reporting_cycle(db, employee.id, manager.id):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{manager.full_name} already reports to {employee.full_name} "
                "(directly or indirectly) — that would create a circular "
                "reporting relationship"
            ),
        )

    existing = (
        db.query(ReportingRelationship)
        .filter(
            ReportingRelationship.employee_id == employee.id,
            ReportingRelationship.reports_to_id == manager.id,
        )
        .first()
    )
    if existing:
        link = existing
        link.relationship_type = payload.relationship_type
        link.is_primary = payload.is_primary
        link.effective_from = payload.effective_from
        link.effective_to = None
    else:
        link = ReportingRelationship(
            employee_id=employee.id,
            reports_to_id=manager.id,
            relationship_type=payload.relationship_type,
            is_primary=payload.is_primary,
            effective_from=payload.effective_from,
        )
        db.add(link)

    # Exactly one primary authority per employee.
    if payload.is_primary:
        db.flush()
        (
            db.query(ReportingRelationship)
            .filter(
                ReportingRelationship.employee_id == employee.id,
                ReportingRelationship.id != link.id,
            )
            .update({ReportingRelationship.is_primary: False})
        )

    audit.log(
        db,
        user,
        "reporting.set",
        entity_type="employee",
        entity_id=employee.id,
        summary=f"{employee.full_name} now reports to {manager.full_name}",
        detail={"is_primary": payload.is_primary},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(link)
    return _reporting_out(db, link)


@router.delete("/reporting/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_reporting(
    link_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(REPORTING_MANAGE)),
):
    link = db.get(ReportingRelationship, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Reporting relationship not found")

    scope = department_scope_ids(db, user)
    if scope is not None:
        subordinate = db.get(Employee, link.employee_id)
        if subordinate is None or subordinate.org_unit_id not in scope:
            raise HTTPException(
                status_code=403,
                detail="This employee is outside the department you manage",
            )

    summary = (
        f"Removed reporting link: {link.employee.full_name} -> "
        f"{link.manager.full_name if link.manager else link.reports_to_id}"
    )
    audit.log(
        db,
        user,
        "reporting.remove",
        entity_type="employee",
        entity_id=link.employee_id,
        summary=summary,
        ip=client_ip(request),
    )
    db.delete(link)
    db.commit()


@router.get("/reporting/chart/{employee_id}")
def reporting_chart(
    employee_id: int,
    depth: int = Query(3, ge=1, le=6),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Nested who-is-under-whom tree rooted at one employee."""
    _require_directory(user)
    root = db.get(Employee, employee_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _assert_employee_visible(db, user, root)

    scope = department_scope_ids(db, user)

    def build(emp: Employee, level: int) -> dict:
        node = {
            "id": emp.id,
            "hrms_employee_id": emp.hrms_employee_id,
            "full_name": emp.full_name,
            "designation": emp.designation.name if emp.designation else None,
            "organization": emp.org_unit.name if emp.org_unit else None,
            "children": [],
        }
        if level < depth:
            # A subordinate's reporting line doesn't have to mirror the org
            # tree (e.g. a cross-department secondment) — re-check scope on
            # every descendant, not just the root, so a Department Head
            # can't see into another department via a reporting chain.
            node["children"] = [
                build(child, level + 1)
                for child in direct_reports(db, emp.id)
                if scope is None or child.org_unit_id in scope
            ]
        return node

    return build(root, 0)


@router.get("/reporting/top")
def reporting_top(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Employees with no reporting authority — the apex of the university."""
    _require_directory(user)
    subquery = (
        db.query(ReportingRelationship.employee_id)
        .filter(
            ReportingRelationship.is_primary.is_(True),
            ReportingRelationship.effective_to.is_(None),
        )
        .subquery()
    )
    query = db.query(Employee).filter(
        Employee.is_active.is_(True), Employee.id.notin_(subquery)
    )
    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(Employee.org_unit_id.in_(scope))
    roots = query.order_by(Employee.full_name).all()
    return [employee_summary(db, e, include_manager=False) for e in roots]
