"""SCENE-shared session spine.

Placeholder — table definitions are subject to change.
"""

import os

import datajoint as dj

from base_schemas.schemas.experiment.lab import Lab  # noqa: F401  # FK: Session -> Lab

if os.getenv("USE_LAZY_SCHEMA"):
    schema = dj.Schema()  # does not require a database connection
else:
    PREFIX = os.getenv("DJ_SCHEMA_PREFIX", "")
    schema = dj.Schema(f"{PREFIX}experiment", locals(), create_tables=True)


@schema
class Session(dj.Manual):
    """One data-collection session within a lab."""

    definition = """
    -> Lab
    session_id: varchar(64)
    ---
    session_date: date
    """
