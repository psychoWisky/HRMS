"""Reporting-chain and post-vacancy helpers.

Org-unit tree traversal and Department-Head scoping now live in
``app.services.org`` — this module keeps only the employee-to-employee
reporting hierarchy and sanctioned-post math.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Employee, Post, ReportingRelationship

# Guards against a cycle introduced by bad data making traversal run forever.
MAX_CHAIN_DEPTH = 50


# ---------------------------------------------------------------------------
# Reporting hierarchy
# ---------------------------------------------------------------------------
def primary_manager_id(db: Session, employee_id: int) -> int | None:
    link = (
        db.query(ReportingRelationship)
        .filter(
            ReportingRelationship.employee_id == employee_id,
            ReportingRelationship.is_primary.is_(True),
            ReportingRelationship.effective_to.is_(None),
        )
        .first()
    )
    return link.reports_to_id if link else None


def reporting_chain(db: Session, employee_id: int) -> list[Employee]:
    """The employee's managers, nearest first, up to the top of the university."""
    chain: list[Employee] = []
    seen: set[int] = {employee_id}
    current = employee_id
    for _ in range(MAX_CHAIN_DEPTH):
        manager_id = primary_manager_id(db, current)
        if manager_id is None or manager_id in seen:
            break
        manager = db.get(Employee, manager_id)
        if manager is None:
            break
        chain.append(manager)
        seen.add(manager_id)
        current = manager_id
    return chain


def direct_reports(db: Session, employee_id: int) -> list[Employee]:
    return (
        db.query(Employee)
        .join(
            ReportingRelationship,
            ReportingRelationship.employee_id == Employee.id,
        )
        .filter(
            ReportingRelationship.reports_to_id == employee_id,
            ReportingRelationship.effective_to.is_(None),
            Employee.is_active.is_(True),
        )
        .order_by(Employee.full_name)
        .all()
    )


def would_create_reporting_cycle(
    db: Session, employee_id: int, manager_id: int
) -> bool:
    """True when making `manager_id` the manager of `employee_id` loops back."""
    if employee_id == manager_id:
        return True
    current = manager_id
    seen: set[int] = {manager_id}
    for _ in range(MAX_CHAIN_DEPTH):
        parent = primary_manager_id(db, current)
        if parent is None:
            return False
        if parent == employee_id:
            return True
        if parent in seen:
            return False
        seen.add(parent)
        current = parent
    return False


# ---------------------------------------------------------------------------
# Posts & vacancies
# ---------------------------------------------------------------------------
def occupied_counts(db: Session) -> dict[int, int]:
    """post_id -> number of active employees currently holding that post."""
    rows = (
        db.query(Employee.post_id, func.count(Employee.id))
        .filter(Employee.post_id.isnot(None), Employee.is_active.is_(True))
        .group_by(Employee.post_id)
        .all()
    )
    return {post_id: count for post_id, count in rows}


def post_vacancy(post: Post, occupied: int) -> int:
    return max(post.sanctioned_count - occupied, 0)
