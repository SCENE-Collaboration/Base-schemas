"""Shared DataJoint schema object and DDL version for scene tables."""

import datajoint as dj

from base_schemas.core import SCENE_REGISTRY

schema = SCENE_REGISTRY.make_schema("scene")

SCENE_SCHEMA_VERSION = "0.0.2"


@schema
class SchemaVersion(dj.Manual):
    """Definition versions applied to this scene database.

    Append a row when a migration has been applied. The latest ``applied_at``
    row is treated as the current DB version.
    """

    definition = """
    version: varchar(32)  # e.g. 0.2.0 — see ``SCENE_SCHEMA_VERSION``
    ---
    applied_at: datetime
    notes='': varchar(512)
    """
