"""Shared DataJoint schema object and DDL version for mouse tables."""

from base_schemas.core import SCENE_REGISTRY
from base_schemas.core.versioning import SchemaVersionTable

schema = SCENE_REGISTRY.make_schema("mouse")

MOUSE_SCHEMA_VERSION = "0.0.1"


@schema
class SchemaVersion(SchemaVersionTable):
    """Definition versions applied to this mouse database (see ``SchemaVersionTable``)."""

    code_version = MOUSE_SCHEMA_VERSION
