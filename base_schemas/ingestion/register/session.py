"""Register a Session (+ Lab + Deployment)."""

from __future__ import annotations

import uuid
from datetime import date

from base_schemas.core.config import load_settings
from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.register.session_meta import upsert_session_row_meta
from base_schemas.schemas.experiment.deployment import Deployment
from base_schemas.schemas.experiment.lab import Lab
from base_schemas.schemas.experiment.session import Session


def new_session_id() -> str:
    """Return a new opaque ``session_id`` (UUID4 hex, 32 chars)."""
    return uuid.uuid4().hex


def _resolve_deployment(
    deployment: DjRow[Deployment] | None,
) -> DjRow[Deployment]:
    """Use ``deployment`` if given; otherwise build a row from Settings."""
    if deployment is not None:
        return deployment
    settings = load_settings()
    if not settings.deployment_id:
        raise ValueError("deployment is required: pass deployment={...} or set SCENE_DEPLOYMENT_ID")
    return {
        "deployment_id": settings.deployment_id,
        "label": settings.deployment_label,
    }


def register_session(
    session_name: str,
    session_date: date,
    *,
    lab: DjRow[Lab],
    deployment: DjRow[Deployment] | None = None,
) -> DjKey[Session]:
    """Insert ``Lab`` / ``Deployment`` (if needed) + ``Session`` + ``SessionRowMeta``.

    Args:
        session_name: User-facing session label (non-empty).
        session_date: Calendar date of the session.
        lab: Lab row dict including all ``Lab`` primary-key fields (and any
            attributes to set on create). Existing labs are left in place
            (``insert1(..., skip_duplicates=True)``).
        deployment: Optional Deployment row dict. If omitted, uses
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL`` from settings.

    Returns:
        Session primary key (Lab primary key fields plus ``session_id``).

    Raises:
        ValueError: If ``session_name`` is empty, or deployment is unset and
            ``SCENE_DEPLOYMENT_ID`` is missing.
    """
    name = session_name.strip()
    if not name:
        raise ValueError("session_name must be a non-empty string")

    Lab.insert1(lab, skip_duplicates=True)
    lab_key: DjKey[Lab] = {k: lab[k] for k in Lab.primary_key}

    deployment_row = _resolve_deployment(deployment)
    Deployment.insert1(deployment_row, skip_duplicates=True)
    deployment_key: DjKey[Deployment] = {k: deployment_row[k] for k in Deployment.primary_key}

    session_id = new_session_id()
    session = {
        **lab_key,
        "session_id": session_id,
        "session_name": name,
        "session_date": session_date,
    }
    Session.insert1(session)
    session_key: DjKey[Session] = {**lab_key, "session_id": session_id}
    upsert_session_row_meta(session_key, session, deployment_key=deployment_key)
    return session_key
