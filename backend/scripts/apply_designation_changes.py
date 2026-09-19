"""One-off: apply the designation add/remove list directly to the database.

Removes: Chancellor, Prof & I/C Head cum Director, Principal Scientist
Adds: Senior Extension Specialist, Extension Specialist, Finance Officer
(Senior Scientist, Scientist, Assistant Professor, Deputy Comptroller,
Assistant Comptroller already exist and are left as-is.)

If someone is still assigned to a designation being removed, that person's
designation is cleared (set to none) so the designation can be safely
deactivated — matching "if user exist remove that user too" (their
designation assignment is removed; the employee record itself is untouched).

Run directly, no API endpoint and no UI button:
    python scripts/apply_designation_changes.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.data import avfu_master_data as md
from app.models.models import Designation, Employee, Post


def main() -> None:
    db = SessionLocal()
    try:
        master_names = {name for name, *_ in md.DESIGNATIONS}
        master_by_name = {name: (short, cat, rank) for name, short, cat, rank in md.DESIGNATIONS}

        existing = db.query(Designation).all()
        existing_by_name = {d.name: d for d in existing}

        for d in existing:
            if d.name in master_names or not d.is_active:
                continue

            posts = db.query(Post).filter(Post.designation_id == d.id).all()
            staff = db.query(Employee).filter(Employee.designation_id == d.id).all()

            for p in posts:
                p.is_active = False
            for e in staff:
                e.designation_id = None

            d.is_active = False
            print(
                f"Removed designation '{d.name}': deactivated {len(posts)} post(s), "
                f"cleared it from {len(staff)} employee(s)."
            )

        for name, (short, cat, rank) in master_by_name.items():
            if name in existing_by_name:
                continue
            db.add(Designation(name=name, short_name=short, category=cat, rank_level=rank))
            print(f"Added designation '{name}'.")

        db.commit()
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
