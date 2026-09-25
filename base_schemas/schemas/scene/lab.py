"""SCENE-shared lab provenance.

Placeholder — table definitions are subject to change.
"""

import datajoint as dj

from base_schemas.schemas.scene._schema import schema


@schema
class Lab(dj.Manual):
    """Lab / group that collected the data (shared provenance)."""

    definition = """
    lab_id: varchar(8)  # short stable token, e.g. mlai — never renamed
    ---
    lab_name='': varchar(255)  # human-readable name
    institution='': varchar(255)
    """
