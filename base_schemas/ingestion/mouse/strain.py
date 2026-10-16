"""Add a Strain to the shared mouse vocabulary (everyday pipeline write).

Any lab adds the strains it uses; no admin role is needed. Names follow the
official mouse strain nomenclature, so every lab spells a strain the same way.

Not exported from ``base_schemas.ingestion``: importing this module registers
the mouse schema, which labs without mice do not need.
"""

from __future__ import annotations

from typing import Any

from base_schemas.core.config import deployment_row_from_settings
from base_schemas.core.db import atomic, lookup_key
from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.mouse._version import MOUSE_WRITER_VERSION
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from base_schemas.schemas.mouse.mouse import Strain
from base_schemas.schemas.mouse.row_meta import StrainRowMeta
from base_schemas.schemas.provenance.deployment import Deployment

RRID_PREFIX = "RRID:"


def strain_meta_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Non-key ``Strain`` fields."""
    return {"rrid": row.get("rrid")}


def _validate_text(value: str, *, field: str, max_length: int) -> None:
    """Reject an empty, padded or overlong ``value``."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters")


def ensure_strain(
    strain: DjRow[Strain],
    *,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
) -> DjKey[Strain]:
    """Insert a strain row and stamp the deployment that registered it.

    Args:
        strain: Full strain insert dict: ``strain_name`` in official
            nomenclature (e.g. ``C57BL/6J``, not ``B6``) and optional ``rrid``.
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``strain_name`` is already stored; see ``DuplicatePolicy``.

    Returns:
        Strain primary key ``{strain_name: ...}``.

    Raises:
        ValueError: If ``strain_name`` or ``rrid`` is malformed, the name is
            stored under another spelling, the ``rrid`` already belongs to
            another strain, ``deployment`` is omitted and
            ``SCENE_DEPLOYMENT_ID`` is unset, or ``if_exists`` rejects the
            existing row.
    """
    name = strain["strain_name"]
    _validate_text(name, field="strain_name", max_length=128)
    rrid = strain.get("rrid")
    if rrid is not None:
        _validate_text(rrid, field="rrid", max_length=64)
        if not rrid.startswith(RRID_PREFIX) or any(char.isspace() for char in rrid):
            raise ValueError(f"rrid {rrid!r} must look like 'RRID:IMSR_JAX:000664'")
    deployment_row = deployment if deployment is not None else deployment_row_from_settings()

    with atomic(Strain.connection):
        stored = lookup_key(Strain, {"strain_name": name})
        if stored is not None and stored["strain_name"] != name:
            raise ValueError(
                f"strain {name!r} is already stored as {stored['strain_name']!r}; use that spelling"
            )
        same_rrid = lookup_key(Strain, {"rrid": rrid}) if rrid is not None else None
        if same_rrid is not None and same_rrid != stored:
            raise ValueError(
                f"{rrid} is already registered as strain {same_rrid['strain_name']!r}; "
                f"use that strain"
            )
        row = {"strain_name": name, "rrid": rrid}
        return insert_tracked_row(
            StrainRowMeta,
            row,
            payload=strain_meta_payload(row),
            deployment=deployment_row,
            if_exists=if_exists,
            writer_version=MOUSE_WRITER_VERSION,
        )
