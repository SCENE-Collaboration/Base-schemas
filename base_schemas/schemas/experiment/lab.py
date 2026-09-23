"""SCENE-shared lab provenance.

Placeholder — table definitions are subject to change.
"""

import datajoint as dj

from base_schemas.core import load_settings

_settings = load_settings()
if _settings.lazy:
    schema = dj.Schema()  # does not require a database connection
else:
    schema = dj.Schema(_settings.db_name("experiment"), locals(), create_tables=True)


@schema
class Lab(dj.Manual):
    """Lab / group that collected the data (shared provenance)."""

    definition = """
    lab_id: varchar(8)  # short stable token, e.g. mlai — never renamed
    ---
    lab_name='': varchar(255)  # human-readable name
    institution='': varchar(255)
    """
