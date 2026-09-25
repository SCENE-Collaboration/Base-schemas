"""SCENE provenance (Deployment, row-meta tables, SchemaVersion).

Not part of the scientific graph. Row-meta tables FK scientific masters
(e.g. ``Session``) and stamp ``Deployment`` + writer version + content hash.
"""

from base_schemas.schemas.provenance._schema import PROVENANCE_SCHEMA_VERSION

__all__ = ["PROVENANCE_SCHEMA_VERSION"]
