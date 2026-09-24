"""SCENE experiment spine (Lab, Deployment, Session, SessionRowMeta, SchemaVersion, …).

Placeholder scientific tables — definitions are subject to change.

DDL: ``EXPERIMENT_SCHEMA_VERSION`` / ``SchemaVersion``.
Row write provenance: ``EXPERIMENT_WRITER_VERSION`` on ``SessionRowMeta``
(defined in ``base_schemas.ingestion``), stamped with ``Deployment``.
"""

from base_schemas.schemas.experiment._schema import EXPERIMENT_SCHEMA_VERSION

__all__ = ["EXPERIMENT_SCHEMA_VERSION"]
