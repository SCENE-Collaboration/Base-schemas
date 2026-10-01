"""SCENE experiment spine (Lab, Session, SchemaVersion, …).

Placeholder scientific tables — definitions are subject to change.

DDL: ``EXPERIMENT_SCHEMA_VERSION`` / ``SchemaVersion``.
Row write provenance lives in ``base_schemas.schemas.provenance``
(``Deployment``, ``SessionRowMeta``).
"""

from base_schemas.schemas.experiment._schema import EXPERIMENT_SCHEMA_VERSION

__all__ = ["EXPERIMENT_SCHEMA_VERSION"]
