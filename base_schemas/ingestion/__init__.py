"""MLAI write helpers on the shared SCENE layer.

- ``ingestion``: register an experimenter, a mouse or a session (shared row + lab row)
- ``manifest``: ``SessionManifestEntry``, one validated session to register
- ``populate``: register sessions from the transfer GUI's metadata files (cron job)
"""

from base_schemas.ingestion.ingestion import (
    MLAI_LAB,
    MLAI_LAB_KEY,
    ensure_mlai_experimenter,
    register_mlai_mouse,
    register_mlai_session,
    session_code,
)
from base_schemas.ingestion.manifest import SessionManifestEntry
from base_schemas.ingestion.populate import populate_base, register_from_manifest, scan_directory

__all__ = [
    "MLAI_LAB",
    "MLAI_LAB_KEY",
    "SessionManifestEntry",
    "ensure_mlai_experimenter",
    "populate_base",
    "register_from_manifest",
    "register_mlai_mouse",
    "register_mlai_session",
    "scan_directory",
    "session_code",
]
