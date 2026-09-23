"""SCENE-shared lab provenance.

Placeholder — table definitions are subject to change.
"""

import os

import datajoint as dj

if os.getenv("USE_LAZY_SCHEMA"):
    schema = dj.Schema()  # does not require a database connection
else:
    PREFIX = os.getenv("DJ_SCHEMA_PREFIX", "")
    schema = dj.Schema(f"{PREFIX}experiment", locals(), create_tables=True)


@schema
class Lab(dj.Manual):
    """Lab / group that collected the data (shared provenance)."""

    definition = """
    lab_id: varchar(8)  # short stable token, e.g. mlai — never renamed
    ---
    lab_name='': varchar(255)  # human-readable name
    institution='': varchar(255)
    """
