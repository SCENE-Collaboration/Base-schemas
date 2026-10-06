"""SCENE provenance (Deployment, row-meta tables, SchemaVersion).

Not part of the scientific graph. Row-meta tables FK scientific masters
(e.g. ``Session``, ``Lab``, ``Project``, ``Subject``) and stamp ``Deployment`` plus a
content hash and the writer version of the ingestion package.
"""

from base_schemas.schemas.provenance._schema import PROVENANCE_SCHEMA_VERSION

__all__ = ["PROVENANCE_SCHEMA_VERSION"]
