"""Register a Subject (everyday pipeline write)."""

from __future__ import annotations

from typing import Any

from base_schemas.core.config import deployment_row_from_settings, lab_key_from_settings
from base_schemas.core.db import atomic, lookup_key, new_id
from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.normalization.code import normalize_code
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from base_schemas.ingestion.scene._version import SCENE_WRITER_VERSION
from base_schemas.schemas.provenance.deployment import Deployment
from base_schemas.schemas.provenance.row_meta import SubjectRowMeta
from base_schemas.schemas.scene.lab import Lab
from base_schemas.schemas.scene.subject import Subject, SubjectKind


def subject_meta_payload(row: dict[str, Any]) -> dict[str, str]:
    """Non-key ``Subject`` fields."""
    return {
        "lab_id": row["lab_id"],
        "subject_code": row["subject_code"],
        "subject_kind": row["subject_kind"],
    }


def register_subject(
    subject_code: str,
    subject_kind: DjKey[SubjectKind] | str,
    *,
    lab: DjKey[Lab],
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Subject]:
    """Register a subject by its lab code; mint ``subject_id`` when new.

    The subject is looked up by ``(lab, subject_code)``. A new code gets a
    freshly minted ``subject_id``; an existing code is handled by ``if_exists``
    against the stored subject. Runs atomically; joins the caller's
    transaction when one is open.

    Args:
        subject_code: Pseudonymous code, unique within ``lab``; see
            ``normalize_code``. Never a real name.
        subject_kind: Existing ``SubjectKind`` key or its name, e.g. ``"mouse"``.
        lab: Existing lab primary key, e.g. ``{"lab_id": "mlai"}``.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``subject_code`` is already registered in
            ``lab``; see ``DuplicatePolicy``. The default ``VERIFY`` returns
            the stored key when the content matches and raises otherwise.

    Returns:
        Subject primary key ``{subject_id: ...}``.

    Raises:
        ValueError: If ``subject_kind`` is ``mouse`` (use ``register_mouse``),
            ``subject_code`` is not a valid code, ``deployment`` is omitted
            and ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the
            existing subject.
    """
    kind = subject_kind["subject_kind"] if isinstance(subject_kind, dict) else subject_kind
    if kind == SubjectKind.MOUSE["subject_kind"]:
        raise ValueError("register mouse subjects with register_mouse (writes the Mouse row too)")
    return _register_subject(
        subject_code, kind, lab=lab, deployment=deployment, if_exists=if_exists
    )


def _register_subject(
    subject_code: str,
    kind: str,
    *,
    lab: DjKey[Lab],
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Subject]:
    """``register_subject`` for any kind; can be called by kind-specific helpers."""
    code = normalize_code(subject_code, field="subject_code", max_length=64)
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()

    with atomic(Subject.connection):
        # insert_tracked_row matches on the primary key, which is minted: resolve an
        # existing code to its stored id first, so if_exists applies to re-registrations.
        existing = lookup_key(Subject, {**lab, "subject_code": code})
        stored_kind = _stored_kind(existing) if existing else kind
        if stored_kind != kind:
            raise ValueError(f"subject {code!r} is registered as {stored_kind!r}, not {kind!r}")
        row = {
            "subject_id": existing["subject_id"] if existing else new_id(),
            **lab,
            "subject_code": code,
            "subject_kind": kind,
        }
        return insert_tracked_row(
            SubjectRowMeta,
            row,
            payload=subject_meta_payload(row),
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=SCENE_WRITER_VERSION,
        )


def _stored_kind(key: DjKey[Subject]) -> str:
    """Return the stored ``subject_kind`` of ``key``."""
    return (Subject & key).fetch1("subject_kind")


def subject_key(subject_code: str, *, lab: DjKey[Lab] | None = None) -> DjKey[Subject]:
    """Find a subject by its lab code.

    Args:
        subject_code: Lab code, e.g. ``"Tick"``.
        lab: Lab primary key, e.g. ``{"lab_id": "mlai"}``. If omitted, built
            from ``SCENE_LAB_ID``.

    Returns:
        Subject primary key, e.g. for ``Mouse & subject_key("Tick", lab=lab)``.

    Raises:
        ValueError: If the code is invalid or not registered in ``lab``, or
            ``lab`` is omitted and ``SCENE_LAB_ID`` is unset.
    """
    lab = lab if lab is not None else lab_key_from_settings()
    code = normalize_code(subject_code, field="subject_code", max_length=64)
    key = lookup_key(Subject, {**lab, "subject_code": code})
    if key is None:
        raise ValueError(f"no subject {code!r} in lab {lab['lab_id']!r}")
    return key
