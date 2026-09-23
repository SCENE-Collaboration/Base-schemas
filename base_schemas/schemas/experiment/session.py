"""SCENE-shared session spine.

Placeholder — table definitions are subject to change.
"""

import datajoint as dj

from base_schemas.core import load_settings
from base_schemas.schemas.experiment.lab import Lab  # noqa: F401  # FK: Session -> Lab

_settings = load_settings()
if _settings.lazy:
    schema = dj.Schema()  # does not require a database connection
else:
    schema = dj.Schema(_settings.db_name("experiment"), locals(), create_tables=True)


@schema
class Session(dj.Manual):
    """One data-collection session within a lab."""

    definition = """
    -> Lab
    session_id: varchar(64)
    ---
    session_date: date
    """
