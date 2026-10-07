"""DataJoint schema object and lab constants for the MLAI tables."""

from base_schemas.core import SCENE_REGISTRY

# Registered like the shared schemas: unbound on import, and activating it
# activates the shared schemas it references first.
schema = SCENE_REGISTRY.make_schema("mlai")

MLAI_LAB = {"lab_id": "mlai"}
