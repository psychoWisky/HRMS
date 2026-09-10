"""Admin/HR/Department-Head dashboards, plus filterable reports (Excel export)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_employee, get_current_user, require_perm
from app.core.permissions import EMPLOYEE_READ, REPORT_READ
from app.models.models import (
    KYC,
    Designation,
    Employee,
    EmployeeSubmission,
    EmploymentStatus,
    KYCStatus,
    Location,
    OrgUnit,
    OrgUnitKind,
    Post,
    ReportingRelationship,
    SubmissionStatus,
    User,
)
from app.schemas.schemas import AdminDashboard, CountItem, EmployeeDashboard
from app.services.hierarchy import (
    direct_reports,
    occupied_counts,
    primary_manager_id,
)
from app.services.org import (
    department_scope_ids,
    org_path,
    org_unit_descendant_ids as org_descendant_ids,
)
from app.services.xlsx import xlsx_response

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard & Reports"])


@router.get("/admin", response_model=AdminDashboard)
def admin_dashboard(
    db: Session = Depends(get_db), user: User = Depends(require_perm(EMPLOYEE_READ))
):
    scope = department_scope_ids(db, user)

    emp_query = db.query(Employee)
    if scope is not None:
        emp_query = emp_query.filter(Employee.org_unit_id.in_(scope))
    total = emp_query.count()
    active = emp_query.filter(Employee.is_active.is_(True)).count()

    occupied_by_post = occupied_counts(db)
    active_posts = db.query(Post).filter(Post.is_active.is_(True))
    if scope is not None:
        active_posts = active_posts.filter(Post.org_unit_id.in_(scope))
    active_posts = active_posts.all()
    sanctioned = sum(p.sanctioned_count for p in active_posts)
    occupied = sum(occupied_by_post.get(p.id, 0) for p in active_posts)
    vacant = sum(
        max(p.sanctioned_count - occupied_by_post.get(p.id, 0), 0)
        for p in active_posts
    )

    def kyc_count(*statuses: KYCStatus) -> int:
        q = db.query(func.count(KYC.id)).filter(KYC.status.in_(statuses))
        if scope is not None:
            q = q.join(Employee, KYC.employee_id == Employee.id).filter(
                Employee.org_unit_id.in_(scope)
            )
        return q.scalar() or 0

    def submission_count(*statuses: SubmissionStatus) -> int:
        q = db.query(func.count(EmployeeSubmission.id)).filter(
            EmployeeSubmission.status.in_(statuses)
        )
        if scope is not None:
            q = q.filter(EmployeeSubmission.org_unit_id.in_(scope))
        return q.scalar() or 0

    loc_q = (
        db.query(Location.name, func.count(Employee.id))
        .join(Employee, Employee.location_id == Location.id)
        .filter(Employee.is_active.is_(True))
    )
    if scope is not None:
        loc_q = loc_q.filter(Employee.org_unit_id.in_(scope))
    by_location = [
        CountItem(label=name or "Unassigned", count=count)
        for name, count in loc_q.group_by(Location.name)
        .order_by(func.count(Employee.id).desc())
        .all()
    ]

    org_q = (
        db.query(OrgUnit.name, func.count(Employee.id))
        .join(Employee, Employee.org_unit_id == OrgUnit.id)
        .filter(Employee.is_active.is_(True))
    )
    if scope is not None:
        org_q = org_q.filter(Employee.org_unit_id.in_(scope))
    by_organization = [
        CountItem(label=name or "Unassigned", count=count)
        for name, count in org_q.group_by(OrgUnit.name)
        .order_by(func.count(Employee.id).desc())
        .limit(15)
        .all()
    ]

    desig_q = (
        db.query(Designation.name, func.count(Employee.id))
        .join(Employee, Employee.designation_id == Designation.id)
        .filter(Employee.is_active.is_(True))
    )
    if scope is not None:
        desig_q = desig_q.filter(Employee.org_unit_id.in_(scope))
    by_designation = [
        CountItem(label=name or "Unassigned", count=count)
        for name, count in desig_q.group_by(Designation.name)
        .order_by(func.count(Employee.id).desc())
        .limit(15)
        .all()
    ]

    org_count_q = db.query(func.count(OrgUnit.id)).filter(
        OrgUnit.is_active.is_(True)
    )
    if scope is not None:
        org_count_q = org_count_q.filter(OrgUnit.id.in_(scope))

    return AdminDashboard(
        total_employees=total,
        active_employees=active,
        inactive_employees=total - active,
        total_organizations=org_count_q.scalar() or 0,
        total_locations=db.query(func.count(Location.id))
        .filter(Location.is_active.is_(True))
        .scalar()
        or 0,
        total_designations=db.query(func.count(Designation.id))
        .filter(Designation.is_active.is_(True))
        .scalar()
        or 0,
        sanctioned_posts=int(sanctioned),
        occupied_posts=occupied,
        vacant_posts=vacant,
        kyc_not_started=kyc_count(KYCStatus.not_started, KYCStatus.draft),
        kyc_pending=kyc_count(
            KYCStatus.submitted,
            KYCStatus.under_verification,
            KYCStatus.resubmission_required,
        ),
        kyc_verified=kyc_count(KYCStatus.verified),
        kyc_rejected=kyc_count(KYCStatus.rejected),
        submissions_awaiting_review=submission_count(
            SubmissionStatus.submitted,
            SubmissionStatus.under_review,
            SubmissionStatus.resubmission_required,
        ),
        submissions_approved=submission_count(SubmissionStatus.approved),
        submissions_rejected=submission_count(SubmissionStatus.rejected),
        by_location=by_location,
        by_organization=by_organization,
        by_designation=by_designation,
    )


@router.get("/me", response_model=EmployeeDashboard)
def employee_dashboard(
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee),
    user: User = Depends(get_current_user),
):
    manager_id = primary_manager_id(db, emp.id)
    manager = db.get(Employee, manager_id) if manager_id else None
    kyc = db.query(KYC).filter(KYC.employee_id == emp.id).first()

    return EmployeeDashboard(
        hrms_employee_id=emp.hrms_employee_id,
        full_name=emp.full_name,
        designation=emp.designation.name if emp.designation else None,
        organization=emp.org_unit.name if emp.org_unit else None,
        organization_path=org_path(db, emp.org_unit),
        location=emp.location.name if emp.location else None,
        reports_to=manager.full_name if manager else None,
        reports_to_designation=(
            manager.designation.name if manager and manager.designation else None
        ),
        direct_reports_count=len(direct_reports(db, emp.id)),
        kyc_status=kyc.status if kyc else KYCStatus.not_started,
        kyc_remark=kyc.verifier_remark if kyc else "",
        date_of_joining=emp.date_of_joining,
        must_change_password=user.must_change_password,
    )


# ---------------------------------------------------------------------------
# Fixed reports (existing) — now exportable as Excel, never CSV
# ---------------------------------------------------------------------------
def _build_fixed_report(db: Session, report: str, limit: int) -> dict:
    if report == "employees-by-organization":
        rows = (
            db.query(
                OrgUnit.name,
                OrgUnit.kind,
                Location.name,
                func.count(Employee.id),
            )
            .outerjoin(Employee, Employee.org_unit_id == OrgUnit.id)
            .outerjoin(Location, OrgUnit.location_id == Location.id)
            .group_by(OrgUnit.id, Location.name)
            .order_by(func.count(Employee.id).desc())
            .limit(limit)
            .all()
        )
        return {
            "title": "Employees by establishment/department",
            "columns": ["Office", "Kind", "Campus", "Employees"],
            "rows": [[r[0], r[1].value, r[2] or "—", r[3]] for r in rows],
        }

    if report == "posts-and-vacancies":
        occupied = occupied_counts(db)
        posts = (
            db.query(Post)
            .filter(Post.is_active.is_(True))
            .join(Designation, Post.designation_id == Designation.id)
            .order_by(Designation.rank_level)
            .limit(limit)
            .all()
        )
        return {
            "title": "Sanctioned posts and vacancies",
            "columns": [
                "Establishment/Department",
                "Designation",
                "Sanctioned",
                "Occupied",
                "Vacant",
                "Remarks",
            ],
            "rows": [
                [
                    p.org_unit.name,
                    p.designation.name,
                    p.sanctioned_count,
                    occupied.get(p.id, 0),
                    max(p.sanctioned_count - occupied.get(p.id, 0), 0),
                    p.remarks,
                ]
                for p in posts
            ],
        }

    if report == "kyc-status":
        rows = (
            db.query(
                Employee.hrms_employee_id,
                Employee.full_name,
                OrgUnit.name,
                KYC.status,
                KYC.submitted_at,
                KYC.verified_at,
            )
            .join(KYC, KYC.employee_id == Employee.id)
            .outerjoin(OrgUnit, Employee.org_unit_id == OrgUnit.id)
            .order_by(Employee.full_name)
            .limit(limit)
            .all()
        )
        return {
            "title": "KYC / document status",
            "columns": [
                "Employee ID",
                "Name",
                "Establishment/Department",
                "Status",
                "Submitted",
                "Verified",
            ],
            "rows": [
                [
                    r[0],
                    r[1],
                    r[2] or "—",
                    r[3].value,
                    r[4].strftime("%d %b %Y") if r[4] else "—",
                    r[5].strftime("%d %b %Y") if r[5] else "—",
                ]
                for r in rows
            ],
        }

    if report == "employees-by-campus":
        rows = (
            db.query(Location.name, func.count(Employee.id))
            .outerjoin(Employee, Employee.location_id == Location.id)
            .group_by(Location.id)
            .order_by(func.count(Employee.id).desc())
            .all()
        )
        return {
            "title": "Employees by campus",
            "columns": ["Campus / Location", "Employees"],
            "rows": [[r[0], r[1]] for r in rows],
        }

    if report == "reporting-hierarchy":
        rows = (
            db.query(ReportingRelationship)
            .filter(ReportingRelationship.effective_to.is_(None))
            .limit(limit)
            .all()
        )
        return {
            "title": "Reporting hierarchy",
            "columns": ["Employee", "Designation", "Reports to", "Type", "Primary"],
            "rows": [
                [
                    link.employee.full_name if link.employee else "—",
                    link.employee.designation.name
                    if link.employee and link.employee.designation
                    else "—",
                    link.manager.full_name if link.manager else "—",
                    link.relationship_type.value,
                    "Yes" if link.is_primary else "No",
                ]
                for link in rows
            ],
        }

    raise HTTPException(status_code=404, detail=f"Unknown report '{report}'")


@router.get("/reports/{report}")
def report(
    report: str,
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(REPORT_READ)),
):
    """Tabular reports. Each returns {columns, rows} ready for display or export."""
    return _build_fixed_report(db, report, limit)


@router.get("/reports/{report}/export")
def export_fixed_report(
    report: str,
    limit: int = Query(2000, le=5000),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(REPORT_READ)),
):
    data = _build_fixed_report(db, report, limit)
    return xlsx_response(data["title"], data["columns"], data["rows"], report)


@router.get("/reports")
def available_reports(user: User = Depends(require_perm(REPORT_READ))):
    return [
        {"key": "employees-by-organization", "title": "Employees by establishment/department"},
        {"key": "employees-by-campus", "title": "Employees by campus"},
        {"key": "posts-and-vacancies", "title": "Sanctioned posts and vacancies"},
        {"key": "kyc-status", "title": "KYC / document status"},
        {"key": "reporting-hierarchy", "title": "Reporting hierarchy"},
    ]


# ---------------------------------------------------------------------------
# Filterable employee report (Section 13/14) — combinable filters + Excel
# ---------------------------------------------------------------------------
def _filtered_employees(
    db: Session,
    user: User,
    *,
    establishment_id: int | None,
    organization_id: int | None,
    location_id: int | None,
    pay_scale: str | None,
    employment_status: EmploymentStatus | None,
    joined_from: date | None,
    joined_to: date | None,
    promoted_from: date | None,
    promoted_to: date | None,
):
    from app.models.models import PositionHistory, PositionEventType

    query = db.query(Employee)

    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(Employee.org_unit_id.in_(scope))

    for unit_filter in (establishment_id, organization_id):
        if unit_filter is not None:
            ids = org_descendant_ids(db, unit_filter)
            if scope is not None:
                ids = ids & scope
            query = query.filter(Employee.org_unit_id.in_(ids))

    if location_id is not None:
        query = query.filter(Employee.location_id == location_id)
    if pay_scale:
        query = query.filter(Employee.pay_scale == pay_scale)
    if employment_status is not None:
        query = query.filter(Employee.employment_status == employment_status)
    if joined_from is not None:
        query = query.filter(Employee.date_of_joining >= joined_from)
    if joined_to is not None:
        query = query.filter(Employee.date_of_joining <= joined_to)

    if promoted_from is not None or promoted_to is not None:
        promo_q = db.query(PositionHistory.employee_id).filter(
            PositionHistory.event_type.in_(
                [PositionEventType.promotion, PositionEventType.establishment_change]
            )
        )
        if promoted_from is not None:
            promo_q = promo_q.filter(PositionHistory.effective_date >= promoted_from)
        if promoted_to is not None:
            promo_q = promo_q.filter(PositionHistory.effective_date <= promoted_to)
        query = query.filter(Employee.id.in_(promo_q.scalar_subquery()))

    return query.order_by(Employee.full_name).all()


def _employee_report_rows(rows: list[Employee]) -> tuple[list[str], list[list]]:
    columns = [
        "HRMS Employee ID",
        "Name",
        "Designation",
        "Establishment/Department",
        "Campus",
        "Pay Scale",
        "Status",
        "Date of Joining",
        "Phone",
        "Official Email",
    ]
    data = [
        [
            e.hrms_employee_id,
            e.full_name,
            e.designation.name if e.designation else "—",
            e.org_unit.name if e.org_unit else "—",
            e.location.name if e.location else "—",
            e.pay_scale or "—",
            e.employment_status.value,
            e.date_of_joining.strftime("%d %b %Y") if e.date_of_joining else "—",
            e.phone,
            e.official_email,
        ]
        for e in rows
    ]
    return columns, data


@router.get("/reports-employees/filtered")
def filtered_employee_report(
    establishment_id: int | None = None,
    organization_id: int | None = None,
    location_id: int | None = None,
    pay_scale: str | None = None,
    employment_status: EmploymentStatus | None = None,
    joined_from: date | None = None,
    joined_to: date | None = None,
    promoted_from: date | None = None,
    promoted_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(REPORT_READ)),
):
    """The combinable-filter employee report (Section 13). JSON preview."""
    rows = _filtered_employees(
        db,
        user,
        establishment_id=establishment_id,
        organization_id=organization_id,
        location_id=location_id,
        pay_scale=pay_scale,
        employment_status=employment_status,
        joined_from=joined_from,
        joined_to=joined_to,
        promoted_from=promoted_from,
        promoted_to=promoted_to,
    )
    columns, data = _employee_report_rows(rows)
    return {"title": "Employee report", "columns": columns, "rows": data}


@router.get("/reports-employees/filtered/export")
def export_filtered_employee_report(
    establishment_id: int | None = None,
    organization_id: int | None = None,
    location_id: int | None = None,
    pay_scale: str | None = None,
    employment_status: EmploymentStatus | None = None,
    joined_from: date | None = None,
    joined_to: date | None = None,
    promoted_from: date | None = None,
    promoted_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(REPORT_READ)),
):
    """Same filters, downloaded as Excel (.xlsx) — never CSV."""
    rows = _filtered_employees(
        db,
        user,
        establishment_id=establishment_id,
        organization_id=organization_id,
        location_id=location_id,
        pay_scale=pay_scale,
        employment_status=employment_status,
        joined_from=joined_from,
        joined_to=joined_to,
        promoted_from=promoted_from,
        promoted_to=promoted_to,
    )
    columns, data = _employee_report_rows(rows)
    return xlsx_response("Employee report", columns, data, "employee-report")
