"""One-off cleanup: retire the legacy "AVFU" college org-unit row.

Before this HRMS's org-unit seed data was changed to make CVSc, CFSc and
LCVSc top-level colleges, "AVFU" itself was seeded as a fourth, root-level
college that everything else (the central university offices, and possibly
some employees) reported into. That seed change does not touch a database
that was already populated, so a database seeded before the change still has
this row.

This script:
  1. Finds the org_units row with kind="college" and code/short_code "AVFU"
     (or name containing "Assam Veterinary and Fishery University").
  2. Re-parents all of its direct children onto CVSc (College of Veterinary
     Science, Khanapara) — the same target the updated seed data uses for
     the central university offices.
  3. Moves any employees directly attached to the AVFU unit itself onto CVSc.
  4. Hard-deletes the now-empty AVFU row.

Idempotent: if the AVFU row is already gone, it does nothing and exits
cleanly. Run with --dry-run first to see what it would do without changing
anything.

Usage (from backend/):
    python scripts/remove_avfu_org_unit.py --dry-run
    python scripts/remove_avfu_org_unit.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.models import Employee, OrgUnit, OrgUnitKind


def find_avfu_unit(db) -> OrgUnit | None:
    candidates = (
        db.query(OrgUnit)
        .filter(OrgUnit.kind == OrgUnitKind.college)
        .filter(
            (OrgUnit.code.ilike("avfu"))
            | (OrgUnit.short_code.ilike("avfu"))
            | (OrgUnit.name.ilike("%Assam Veterinary and Fishery University%"))
        )
        .all()
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        raise SystemExit(
            f"Found {len(candidates)} candidate AVFU rows — expected exactly one. "
            f"IDs: {[c.id for c in candidates]}. Aborting; resolve manually."
        )
    return candidates[0]


def find_cvsc_unit(db) -> OrgUnit:
    cvsc = (
        db.query(OrgUnit)
        .filter(OrgUnit.kind == OrgUnitKind.college)
        .filter((OrgUnit.code.ilike("cvsc")) | (OrgUnit.short_code.ilike("cvsc")))
        .first()
    )
    if cvsc is None:
        raise SystemExit(
            "Could not find the CVSc college row to re-parent onto. Aborting."
        )
    return cvsc


def main(dry_run: bool) -> None:
    db = SessionLocal()
    try:
        avfu = find_avfu_unit(db)
        if avfu is None:
            print("No AVFU org-unit row found — nothing to do.")
            return

        cvsc = find_cvsc_unit(db)
        if avfu.id == cvsc.id:
            raise SystemExit("AVFU and CVSc resolved to the same row — aborting.")

        children = db.query(OrgUnit).filter(OrgUnit.parent_id == avfu.id).all()
        employees = db.query(Employee).filter(Employee.org_unit_id == avfu.id).all()

        print(f"AVFU row: id={avfu.id} name={avfu.name!r} code={avfu.code!r}")
        print(f"CVSc row (re-parent target): id={cvsc.id} name={cvsc.name!r}")
        print(f"Direct child org-units to move: {len(children)}")
        for c in children:
            print(f"  - id={c.id} kind={c.kind.value} name={c.name!r}")
        print(f"Employees directly on the AVFU unit to move: {len(employees)}")
        for e in employees:
            print(f"  - id={e.id} hrms_employee_id={e.hrms_employee_id} name={e.full_name!r}")

        if dry_run:
            print("\n--dry-run: no changes made.")
            return

        for c in children:
            c.parent_id = cvsc.id
        for e in employees:
            e.org_unit_id = cvsc.id
        db.flush()

        remaining_children = (
            db.query(OrgUnit).filter(OrgUnit.parent_id == avfu.id).count()
        )
        remaining_staff = (
            db.query(Employee).filter(Employee.org_unit_id == avfu.id).count()
        )
        if remaining_children or remaining_staff:
            raise SystemExit(
                f"Re-parenting incomplete: {remaining_children} child unit(s), "
                f"{remaining_staff} employee(s) still attached. Aborting before delete."
            )

        db.delete(avfu)
        db.commit()
        print(f"\nDone: re-parented {len(children)} unit(s) and {len(employees)} "
              f"employee(s) onto CVSc, then deleted the AVFU row (id={avfu.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change, without changing it"
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
