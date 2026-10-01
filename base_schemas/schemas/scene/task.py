"""SCENE-shared task catalog (protocol identity only)."""

import datajoint as dj

from base_schemas.core.access_markers import mark_admin_write
from base_schemas.schemas.scene._schema import schema


@mark_admin_write
@schema
class Task(dj.Manual):
    """Admin-only insertion: Shared protocol/paradigm catalog."""

    definition = """
    task_name: varchar(100)  # stable id, e.g. visual_discrim_v2
    ---
    task_title='': varchar(255)  # human-readable label
    """
