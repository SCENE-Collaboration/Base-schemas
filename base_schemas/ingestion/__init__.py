"""Supported write path for SCENE base schemas (register helpers)."""

from base_schemas.ingestion.scene import (
    SCENE_WRITER_VERSION,
    register_session,
    register_subject,
)

__all__ = [
    "SCENE_WRITER_VERSION",
    "register_session",
    "register_subject",
]
