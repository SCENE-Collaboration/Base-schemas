"""Shared DataJoint schema object and DDL version for experiment tables."""

from base_schemas.core import SCENE_REGISTRY
from base_schemas.core.versioning import SchemaVersionTable

schema = SCENE_REGISTRY.make_schema("experiment")

EXPERIMENT_SCHEMA_VERSION = "0.0.2"


@schema
class SchemaVersion(SchemaVersionTable):
    """Definition versions applied to this experiment database (see ``SchemaVersionTable``)."""

    code_version = EXPERIMENT_SCHEMA_VERSION
