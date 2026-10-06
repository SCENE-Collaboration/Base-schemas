"""Register a Session by lab code (+ Deployment + SessionRowMeta)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from base_schemas.core.config import deployment_row_from_settings
from base_schemas.core.db import atomic, lookup_key, new_id
from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.normalization.code import normalize_code
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from base_schemas.ingestion.scene._version import SCENE_WRITER_VERSION
from base_schemas.schemas.provenance.deployment import Deployment
from base_schemas.schemas.provenance.row_meta import SessionRowMeta
from base_schemas.schemas.scene.lab import Lab
from base_schemas.schemas.scene.project import Project
from base_schemas.schemas.scene.session import Experimenter, Session
from base_schemas.schemas.scene.subject import Subject


def session_meta_payload(
    session: dict[str, Any],
    subject_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Non-key session fields + subjects that should affect ``content_hash``."""
    return {
        "session_date": str(session["session_date"]),
        "session_code": session["session_code"],
        "project_name": session.get("project_name"),
        "experimenter_code": session.get("experimenter_code"),
        "subject_ids": sorted(subject_ids),
    }


def _subject_ids(subjects: Sequence[DjKey[Subject]]) -> list[str]:
    """Return the ``subject_id`` of each key; reject repeats or invalid keys."""
    subject_ids = []
    for subject in subjects:
        subject_id = subject.get("subject_id")
        if not isinstance(subject_id, str) or not subject_id:
            raise ValueError(f"subject key {subject!r} has no subject_id")
        if subject_id in subject_ids:
            raise ValueError(f"subject {subject_id!r} is listed more than once")
        subject_ids.append(subject_id)
    return subject_ids


def register_session(
    session_code: str,
    session_date: date,
    *,
    lab: DjKey[Lab],
    subjects: Sequence[DjKey[Subject]] = (),
    project: DjKey[Project] | None = None,
    experimenter: DjKey[Experimenter] | None = None,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Session]:
    """Register a session by its lab code; mint ``session_id`` when new.

    The session is looked up by ``(lab, session_code)``. A new code gets a
    freshly minted ``session_id``; an existing code is handled by ``if_exists``
    against the stored session (its hash covers the linked subjects). Catalog
    keys (``lab``, ``subjects``, ``project``, ``experimenter``) must already exist.
    Runs atomically; joins the caller's transaction when one is open.

    Args:
        session_code: Pseudonymous code, unique within ``lab``; see
            ``normalize_code``. Never a real name.
        session_date: Calendar date of the session.
        lab: Existing lab primary key, e.g. ``{"lab_id": "mlai"}``.
        subjects: Existing subject keys (may be empty).
        project: Optional existing project key.
        experimenter: Optional existing experimenter key; must be of ``lab``.
        deployment: Optional deployment row to stamp with. If omitted, built
            from ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``session_code`` is already registered in
            ``lab``; see ``DuplicatePolicy``. ``OVERWRITE`` also replaces the
            subject links.

    Returns:
        Session primary key ``{lab_id, session_id}``.

    Raises:
        ValueError: If ``session_code`` is not a valid code, a subject key has no
            ``subject_id`` or is listed twice, ``experimenter`` is of another
            lab, ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the
            existing session.
    """
    code = normalize_code(session_code, field="session_code", max_length=128)
    subject_ids = _subject_ids(subjects)
    if experimenter is not None and experimenter["lab_id"] != lab["lab_id"]:
        raise ValueError(f"experimenter {experimenter!r} is not of lab {lab['lab_id']!r}")

    deployment_row = deployment if deployment is not None else deployment_row_from_settings()

    with atomic(Session.connection):
        # insert_tracked_row matches on the primary key, which is minted: resolve an
        # existing code to its stored id first, so if_exists applies to re-registrations.
        existing = lookup_key(Session, {**lab, "session_code": code})
        session = {
            **lab,
            "session_id": existing["session_id"] if existing else new_id(),
            "session_code": code,
            "session_date": session_date,
            **(project or {}),
            **(experimenter or {}),
        }
        return insert_tracked_row(
            SessionRowMeta,
            session,
            payload=session_meta_payload(session, subject_ids),
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=SCENE_WRITER_VERSION,
            parts={Session.Subject: [{"subject_id": sid} for sid in subject_ids]},
        )
