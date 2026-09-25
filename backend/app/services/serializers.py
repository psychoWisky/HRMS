"""Model -> schema conversion shared across routers."""
from sqlalchemy.orm import Session

from app.models.models import Employee, OrgUnit, OrgUnitKind, Post
from app.schemas.schemas import EmployeeSummary, OrgUnitOut, PostOut
from app.services.hierarchy import primary_manager_id
from app.services.org import (
    nearest_of_kind,
    org_path,
    org_unit_descendant_ids,
)


def _college_or_university_name(
    db: Session, unit: OrgUnit | None, college: OrgUnit | None
) -> str | None:
    """Display name for the "College / University" field: the nearest
    College, or the University for central offices that sit under no
    College. (``college_id`` stays college-only — filters depend on it.)"""
    if college:
        return college.name
    university = nearest_of_kind(db, unit, OrgUnitKind.university) if unit else None
    return university.name if university else None


def org_unit_out(
    db: Session,
    unit: OrgUnit,
    emp_counts: dict[int, int],
    sanctioned_counts: dict[int, int] | None = None,
) -> OrgUnitOut:
    descendants = org_unit_descendant_ids(db, unit.id)
    college = nearest_of_kind(db, unit, OrgUnitKind.college)
    sanctioned_counts = sanctioned_counts or {}
    return OrgUnitOut(
        id=unit.id,
        kind=unit.kind,
        sub_kind=unit.sub_kind,
        parent_id=unit.parent_id,
        parent_name=unit.parent.name if unit.parent else None,
        college_id=college.id if college else None,
        college_name=_college_or_university_name(db, unit, college),
        name=unit.name,
        short_code=unit.short_code,
        code=unit.code,
        location_id=unit.location_id,
        location_name=unit.location.name if unit.location else None,
        sort_order=unit.sort_order,
        is_active=unit.is_active,
        path=org_path(db, unit),
        head_employee_id=unit.head_employee_id,
        head_name=unit.head.full_name if unit.head else None,
        reporting_authority_text=unit.reporting_authority_text,
        hrms_contact_name=unit.hrms_contact_name,
        hrms_contact_designation=unit.hrms_contact_designation,
        hrms_contact_phone=unit.hrms_contact_phone,
        hrms_contact_email=unit.hrms_contact_email,
        office_email=unit.office_email,
        description=unit.description,
        officer_in_charge_employee_id=unit.officer_in_charge_employee_id,
        officer_in_charge_name=(
            unit.officer_in_charge.full_name if unit.officer_in_charge else None
        ),
        headcount_note=unit.headcount_note,
        direct_employee_count=emp_counts.get(unit.id, 0),
        employee_count=sum(emp_counts.get(i, 0) for i in descendants),
        sanctioned_count=sum(sanctioned_counts.get(i, 0) for i in descendants),
        child_count=len(unit.children),
    )


def employee_summary(
    db: Session, emp: Employee, *, include_manager: bool = True
) -> EmployeeSummary:
    manager_name = None
    manager_id = None
    if include_manager:
        manager_id = primary_manager_id(db, emp.id)
        if manager_id:
            manager = db.get(Employee, manager_id)
            manager_name = manager.full_name if manager else None

    unit = emp.org_unit
    college = nearest_of_kind(db, unit, OrgUnitKind.college) if unit else None
    establishment = (
        nearest_of_kind(db, unit, OrgUnitKind.establishment) if unit else None
    )
    department = nearest_of_kind(db, unit, OrgUnitKind.department) if unit else None

    return EmployeeSummary(
        id=emp.id,
        hrms_employee_id=emp.hrms_employee_id,
        full_name=emp.full_name,
        college=_college_or_university_name(db, unit, college),
        college_id=college.id if college else None,
        department=department.name if department else None,
        department_id=department.id if department else None,
        establishment=establishment.name if establishment else None,
        establishment_id=establishment.id if establishment else None,
        designation=emp.designation.name if emp.designation else None,
        designation_id=emp.designation_id,
        organization=unit.name if unit else None,
        organization_id=emp.org_unit_id,
        org_unit_id=emp.org_unit_id,
        org_unit_kind=unit.kind if unit else None,
        organization_path=org_path(db, unit),
        location=emp.location.name if emp.location else None,
        official_email=emp.official_email,
        phone=emp.phone,
        photo_url=emp.photo_url,
        reports_to=manager_name,
        reports_to_id=manager_id,
        employment_status=emp.employment_status,
        is_active=emp.is_active,
    )


def post_out(post: Post, occupied: int) -> PostOut:
    return PostOut(
        id=post.id,
        org_unit_id=post.org_unit_id,
        org_unit_name=post.org_unit.name if post.org_unit else "",
        designation_id=post.designation_id,
        designation_name=post.designation.name if post.designation else "",
        level_no=post.level_no,
        sanctioned_count=post.sanctioned_count,
        occupied_count=occupied,
        vacant_count=max(post.sanctioned_count - occupied, 0),
        over_strength_count=max(occupied - post.sanctioned_count, 0),
        reported_vacant_count=post.reported_vacant_count,
        level_label=post.level_label,
        reports_to_note=post.reports_to_note,
        reports_to_designation_id=post.reports_to_designation_id,
        reports_to_designation_name=(
            post.reports_to_designation.name if post.reports_to_designation else None
        ),
        remarks=post.remarks,
        is_active=post.is_active,
    )
