"""Supported write path for SCENE base schemas (register helpers)."""

from base_schemas.ingestion.register import register_session
from base_schemas.ingestion.register.session_meta import SCENE_WRITER_VERSION

__all__ = ["SCENE_WRITER_VERSION", "register_session"]
