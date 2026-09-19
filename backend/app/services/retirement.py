"""Expected date of retirement: 65 for Professor & above, 60 for everyone else."""
from datetime import date

# Professor & above (rank_level <= this) retire at 65; everyone else at 60.
PROFESSOR_RANK_LEVEL = 15


def calc_retirement_date(dob: date | None, rank_level: int | None) -> date | None:
    if dob is None:
        return None
    age = 65 if rank_level is not None and rank_level <= PROFESSOR_RANK_LEVEL else 60
    try:
        return dob.replace(year=dob.year + age)
    except ValueError:
        # Feb 29 birthdays on a non-leap retirement year.
        return dob.replace(year=dob.year + age, day=28)
