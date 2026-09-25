"""Register a Subject (everyday pipeline write)."""

from __future__ import annotations

import uuid

from base_schemas.core.types import DjKey, DjRow
from base_schemas.schemas.scene.subject import Subject


def new_subject_id() -> str:
    """Return a new opaque ``subject_id`` (UUID4 hex, 32 chars)."""
    return uuid.uuid4().hex


def register_subject(
    subject: DjRow[Subject],
    *,
    skip_duplicates: bool = True,
) -> DjKey[Subject]:
    """Insert a subject row and return its primary key.

    Args:
        subject: Full subject insert dict (``subject_id``, ``subject_kind``, …).
        skip_duplicates: Forwarded to DataJoint ``insert1``. If a row with the
            same primary key exists, it is left unchanged.

    Returns:
        Subject primary key ``{subject_id: ...}``.
    """
    Subject.insert1(subject, skip_duplicates=skip_duplicates)
    return {k: subject[k] for k in Subject.primary_key}
