"""HRMS Employee ID generation.

Format: ``AVFU/<EstShort>/<DeptShort|GEN>/<serial>``

  * ``EstShort``   the ``short_code`` of the nearest Establishment at or
                   above the employee's org unit.
  * ``DeptShort``  the ``short_code`` of the nearest Department at or above
                   the org unit, or the literal ``GEN`` when the employee
                   is not in any department.
  * ``serial``     a 4-digit, zero-padded running number, unique **per
                   establishment** (i.e. across every ``AVFU/<EstShort>/...``).

Serials never restart and are never reused. On promotion within the same
establishment the ID is kept; on a move to a different establishment a new
ID is minted and the old one is preserved in ``PositionHistory``.
"""
import re

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Employee, OrgUnit, OrgUnitKind
from app.services.org import nearest_of_kind

PREFIX = "AVFU"
GEN = "GEN"
_SERIAL_RE = re.compile(r"/(\d+)\s*$")


def resolve_id_segments(db: Session, unit: OrgUnit | None) -> tuple[str, str]:
    """Return ``(est_short, dept_short_or_GEN)`` for an org unit.

    Fallbacks: if the chain has a Department but no Establishment (a
    department sitting directly under a College), the department's own
    ``short_code`` fills the establishment slot and the dept slot is GEN.
    """
    if unit is None:
        raise HTTPException(
            status_code=400,
            detail="An org unit is required to generate an HRMS Employee ID",
        )

    est = nearest_of_kind(db, unit, OrgUnitKind.establishment)
    dept = nearest_of_kind(db, unit, OrgUnitKind.department)

    est_short = (est.short_code if est else "").strip().upper()
    dept_short = (dept.short_code if dept else "").strip().upper()

    if not est_short:
        # No establishment above this unit — use the department, or the unit itself.
        est_short = dept_short or (unit.short_code or "").strip().upper()
        dept_short = ""

    if not est_short:
        raise HTTPException(
            status_code=400,
            detail=(
                "The chosen office has no short code set — an Establishment "
                "(or its parent) needs a short code before an HRMS Employee "
                "ID can be generated."
            ),
        )

    return est_short, (dept_short or GEN)


def next_employee_id(db: Session, unit: OrgUnit | None) -> str:
    est_short, dept_short = resolve_id_segments(db, unit)
    est_prefix = f"{PREFIX}/{est_short}/"

    highest = 0
    rows = (
        db.query(Employee.hrms_employee_id)
        .filter(Employee.hrms_employee_id.like(f"{est_prefix}%"))
        .all()
    )
    for (code,) in rows:
        m = _SERIAL_RE.search(code or "")
        if m:
            highest = max(highest, int(m.group(1)))

    return f"{est_prefix}{dept_short}/{highest + 1:04d}"
