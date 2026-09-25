"""SCENE shared identity + session graph (Lab, Session, SchemaVersion, …).

Placeholder scientific tables — definitions are subject to change.

DDL: ``SCENE_SCHEMA_VERSION`` / ``SchemaVersion``.
Row write provenance lives in ``base_schemas.schemas.provenance``
(``Deployment``, ``SessionRowMeta``).
"""

from base_schemas.schemas.scene._schema import SCENE_SCHEMA_VERSION

__all__ = ["SCENE_SCHEMA_VERSION"]
