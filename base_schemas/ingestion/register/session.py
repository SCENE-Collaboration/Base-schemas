"""Register a Session (+ Lab)."""

from __future__ import annotations

import uuid
from datetime import date

from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.register.session_meta import upsert_session_row_meta
from base_schemas.schemas.experiment.lab import Lab
from base_schemas.schemas.experiment.session import Session


def new_session_id() -> str:
    """Return a new opaque ``session_id`` (UUID4 hex, 32 chars)."""
    return uuid.uuid4().hex


def register_session(
    session_name: str,
    session_date: date,
    *,
    lab: DjRow[Lab],
) -> DjKey[Session]:
    """Insert ``Lab`` (if needed) + ``Session`` + ``SessionRowMeta``.

    Args:
        session_name: User-facing session label (non-empty).
        session_date: Calendar date of the session.
        lab: Lab row dict including all ``Lab`` primary-key fields (and any
            attributes to set on create). Existing labs are left in place
            (``insert1(..., skip_duplicates=True)``).

    Returns:
        Session primary key (Lab primary key fields plus ``session_id``).

    Raises:
        ValueError: If ``session_name`` is empty or whitespace-only.
    """
    name = session_name.strip()
    if not name:
        raise ValueError("session_name must be a non-empty string")

    # Create lab record if it doesn't exist
    Lab.insert1(lab, skip_duplicates=True)
    lab_key: DjKey[Lab] = {k: lab[k] for k in Lab.primary_key}

    # Create session record
    session_id = new_session_id()
    session = {
        **lab_key,
        "session_id": session_id,
        "session_name": name,
        "session_date": session_date,
    }
    Session.insert1(session)
    session_key: DjKey[Session] = {**lab_key, "session_id": session_id}
    upsert_session_row_meta(session_key, session)
    return session_key
