"""Supported write path for SCENE base schemas (register helpers)."""

from base_schemas.ingestion.register import register_session
from base_schemas.ingestion.register.session_meta import EXPERIMENT_WRITER_VERSION

__all__ = ["EXPERIMENT_WRITER_VERSION", "register_session"]
