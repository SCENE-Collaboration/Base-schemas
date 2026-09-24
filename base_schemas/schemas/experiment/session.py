"""SCENE-shared session spine.

Placeholder — table definitions are subject to change.
"""

import datajoint as dj

from base_schemas.schemas.experiment._schema import schema
from base_schemas.schemas.experiment.lab import Lab  # noqa: F401  # FK: Session -> Lab


@schema
class Session(dj.Manual):
    """One data-collection session within a lab."""

    definition = """
    -> Lab
    session_id: varchar(64)  # stable token; never renamed
    ---
    session_name: varchar(128)  # user-facing label
    session_date: date
    """
