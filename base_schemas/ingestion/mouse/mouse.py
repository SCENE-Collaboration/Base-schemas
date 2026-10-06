"""Register a Mouse together with its Subject (everyday pipeline write).

Not exported from ``base_schemas.ingestion``: importing this module registers
the mouse schema, which labs without mice do not need.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from base_schemas.core.config import deployment_row_from_settings
from base_schemas.core.db import atomic, lookup_key
from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.mouse._version import MOUSE_WRITER_VERSION
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from base_schemas.ingestion.scene.subject import register_subject
from base_schemas.schemas.mouse.mouse import Mouse, Strain
from base_schemas.schemas.mouse.row_meta import MouseRowMeta
from base_schemas.schemas.provenance.deployment import Deployment
from base_schemas.schemas.scene.lab import Lab
from base_schemas.schemas.scene.subject import Subject

MOUSE_KIND = "mouse"


def mouse_meta_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Non-key ``Mouse`` fields."""
    date_of_birth = row.get("date_of_birth")
    return {
        "sex": row["sex"],
        "date_of_birth": None if date_of_birth is None else str(date_of_birth),
        "strain_name": row.get("strain_name"),
        "genotype": row.get("genotype") or "",
    }


def register_mouse(
    subject_code: str,
    sex: str,
    *,
    lab: DjKey[Lab],
    date_of_birth: date | None = None,
    strain: DjKey[Strain] | None = None,
    genotype: str = "",
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Mouse]:
    """Register a mouse by its lab code: the ``Subject`` and its ``Mouse`` row.

    Args:
        subject_code: Pseudonymous code, unique within ``lab``.
        sex: ``"M"``, ``"F"`` or ``"U"`` (unknown).
        lab: Existing lab primary key, e.g. ``{"lab_id": "mlai"}``.
        date_of_birth: Optional date of birth.
        strain: Optional existing ``Strain`` key (background strain), e.g.
            ``{"strain_name": "C57BL/6J"}``; add a new one first with ``ensure_strain``.
        genotype: Optional free-text genotype (transgenic lines, zygosity).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy applied to the subject and to the mouse row when
            already registered; see ``DuplicatePolicy``.

    Returns:
        Mouse primary key ``{subject_id: ...}`` (same as the subject's).

    Raises:
        ValueError: If ``subject_code`` is not a valid code, the code belongs
            to a subject of another kind, ``strain`` does not exist,
            ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects an
            existing subject or mouse.
    """
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()
    strain_name = None
    if strain is not None:
        stored_strain = lookup_key(Strain, strain)
        if stored_strain is None:
            raise ValueError(f"unknown strain {strain['strain_name']!r}; add it with ensure_strain")
        strain_name = stored_strain[
            "strain_name"
        ]  # stored spelling (names match case-insensitively)

    with atomic(Mouse.connection):
        subject = register_subject(
            subject_code, MOUSE_KIND, lab=lab, deployment=deployment_row, if_exists=if_exists
        )
        kind = (Subject & subject).fetch1("subject_kind")
        if kind != MOUSE_KIND:
            raise ValueError(f"subject {subject_code!r} is registered as {kind!r}, not a mouse")
        row = {
            **subject,
            "sex": sex,
            "date_of_birth": date_of_birth,
            "strain_name": strain_name,
            "genotype": genotype,
        }
        return insert_tracked_row(
            MouseRowMeta,
            row,
            payload=mouse_meta_payload(row),
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=MOUSE_WRITER_VERSION,
        )
