"""DataJoint schema object and DDL version for the MLAI tables."""

from base_schemas.core import SCENE_REGISTRY
from base_schemas.core.versioning import SchemaVersionTable

# Registered like the shared schemas: unbound on import, and activating it
# activates the shared schemas it references first.
schema = SCENE_REGISTRY.make_schema("mlai")

# First versioned layout; the legacy ``mice`` / ``exp`` tables (``legacy/``) carry no version.
MLAI_SCHEMA_VERSION = "0.0.1"


@schema
class SchemaVersion(SchemaVersionTable):
    """Definition versions applied to this MLAI database (see ``SchemaVersionTable``)."""

    code_version = MLAI_SCHEMA_VERSION
