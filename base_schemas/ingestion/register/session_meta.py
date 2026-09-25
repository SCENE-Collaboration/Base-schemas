"""SessionRowMeta write helpers (etag payload + upsert)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from base_schemas.core.hash import content_hash
from base_schemas.core.types import DjKey
from base_schemas.schemas.experiment.session import Session
from base_schemas.schemas.provenance.deployment import Deployment
from base_schemas.schemas.provenance.row_meta import SessionRowMeta

EXPERIMENT_WRITER_VERSION = "0.0.1"


def session_etag_payload(session: dict[str, Any]) -> dict[str, Any]:
    """Non-key session fields that should affect ``SessionRowMeta.content_hash``."""
    return {
        "session_date": str(session["session_date"]),
        "session_name": session["session_name"],
    }


def upsert_session_row_meta(
    session_key: DjKey[Session],
    session: dict[str, Any],
    *,
    deployment_key: DjKey[Deployment],
    writer_version: str | None = None,
) -> None:
    """Insert or replace ``SessionRowMeta`` for a session."""
    SessionRowMeta.insert1(
        {
            **session_key,
            **deployment_key,
            "ingestion_version": writer_version or EXPERIMENT_WRITER_VERSION,
            "content_hash": content_hash(session_etag_payload(session)),
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
        },
        replace=True,
    )
