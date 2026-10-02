"""Admin helper: ensure a Project catalog row exists."""

from __future__ import annotations

from typing import Any

from base_schemas.core.config import deployment_row_from_settings
from base_schemas.core.types import DjKey, DjRow
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row
from base_schemas.schemas.provenance.deployment import Deployment
from base_schemas.schemas.provenance.row_meta import ProjectRowMeta
from base_schemas.schemas.scene.project import Project


def project_meta_payload(row: dict[str, Any]) -> dict[str, str]:
    """Non-key ``Project`` fields. A missing title hashes as an empty string."""
    return {"project_title": row.get("project_title") or ""}


def ensure_project(
    project: DjRow[Project],
    *,
    deployment: DjRow[Deployment] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.REJECT,
) -> DjKey[Project]:
    """Insert a project row and stamp the deployment that registered it.

    Runs atomically; joins the caller's transaction when one is open.

    Args:
        project: Full project insert dict (``project_name``, optional ``project_title``, …).
        deployment: Optional deployment row. If omitted, built from
            ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.
        if_exists: Policy when ``project_name`` is already stored; see ``DuplicatePolicy``.

    Returns:
        Project primary key ``{project_name: ...}``.

    Raises:
        ValueError: If ``deployment`` is omitted and ``SCENE_DEPLOYMENT_ID``
            is unset, or ``if_exists`` rejects the existing row.
    """
    return insert_tracked_row(
        ProjectRowMeta,
        project,
        payload=project_meta_payload(project),
        deployment=deployment if deployment is not None else deployment_row_from_settings(),
        if_exists=if_exists,
    )
