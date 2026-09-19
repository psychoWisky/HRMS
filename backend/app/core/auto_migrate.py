"""Bring an already-existing database's schema in line with the models.

``Base.metadata.create_all`` only creates missing *tables* — it never alters
one that already exists, so a plain model change (a new column, or a new
value added to a Python enum used as a Postgres native enum type) never
reaches a database that was seeded before that change. There is no Alembic
in this project, so this runs once at startup, after ``create_all``, and:

  * adds any Postgres enum value that a model's ``Enum(...)`` column can
    produce but the database's enum type doesn't have yet (must run before
    the column sync below, since a column can't be added/used with a value
    the enum type doesn't recognise), and
  * adds any column that exists on a model but not yet in that table.

Both only ever add — never drop or alter an existing column/value — so this
is safe to run on every startup, including against SQLite in tests (enum
sync is a no-op there; SQLite has no native enum type to alter).
"""
from sqlalchemy import Enum, inspect, text
from sqlalchemy.engine import Engine


def sync_enum_types(engine: Engine, base) -> None:
    if engine.dialect.name != "postgresql":
        return  # SQLite/others store enums as plain CHECK-less strings

    with engine.begin() as conn:
        seen_enum_names: set[str] = set()
        for table in base.metadata.sorted_tables:
            for column in table.columns:
                col_type = column.type
                if not isinstance(col_type, Enum) or col_type.enum_class is None:
                    continue
                pg_enum_name = col_type.name
                if pg_enum_name in seen_enum_names:
                    continue
                seen_enum_names.add(pg_enum_name)

                exists = conn.execute(
                    text("SELECT 1 FROM pg_type WHERE typname = :name"),
                    {"name": pg_enum_name},
                ).first()
                if not exists:
                    continue  # create_all will create this enum type fresh

                current_values = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT enumlabel FROM pg_enum "
                            "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                            "WHERE pg_type.typname = :name"
                        ),
                        {"name": pg_enum_name},
                    )
                }
                model_values = {member.value for member in col_type.enum_class}
                for missing in model_values - current_values:
                    conn.execute(
                        text(
                            f'ALTER TYPE "{pg_enum_name}" ADD VALUE IF NOT EXISTS :val'.replace(
                                ":val", f"'{missing}'"
                            )
                        )
                    )


def sync_missing_columns(engine: Engine, base) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # a brand-new table; create_all already added it
            existing_columns = {
                col["name"] for col in inspector.get_columns(table.name)
            }
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                ddl_type = column.type.compile(dialect=engine.dialect)
                nullable = "" if column.nullable else " NOT NULL"
                conn.execute(
                    text(
                        f'ALTER TABLE "{table.name}" '
                        f'ADD COLUMN "{column.name}" {ddl_type}{nullable}'
                    )
                )
