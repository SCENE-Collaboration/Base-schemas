"""SCENE-shared task catalog (protocol identity only)."""

import datajoint as dj

from base_schemas.schemas.scene._schema import schema


@schema
class Task(dj.Manual):
    """Shared protocol/paradigm catalog (name + light label only)."""

    definition = """
    task_name: varchar(100)  # stable id, e.g. visual_discrim_v2
    ---
    task_title='': varchar(255)  # human-readable label
    """
