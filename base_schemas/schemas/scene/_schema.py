"""Shared DataJoint schema object and DDL version for scene tables."""

from base_schemas.core import SCENE_REGISTRY
from base_schemas.core.versioning import SchemaVersionTable

schema = SCENE_REGISTRY.make_schema("scene")

SCENE_SCHEMA_VERSION = "0.0.2"


@schema
class SchemaVersion(SchemaVersionTable):
    """Definition versions applied to this scene database (see ``SchemaVersionTable``)."""

    code_version = SCENE_SCHEMA_VERSION
