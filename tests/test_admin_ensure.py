"""Unit tests for admin ensure_* helpers (no MySQL)."""

from unittest.mock import patch

import pytest
from base_schemas.ingestion.admin import lab as lab_admin
from base_schemas.ingestion.admin import project as project_admin
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy


def test_ensure_lab_delegates_to_insert_tracked_row(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "from-env")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "Env")
    row = {"lab_id": "mlai", "lab_name": "Mathis Lab"}
    with patch.object(lab_admin, "insert_tracked_row", return_value={"lab_id": "mlai"}) as write:
        key = lab_admin.ensure_lab(row)

    assert key == {"lab_id": "mlai"}
    write.assert_called_once_with(
        lab_admin.LabRowMeta,
        row,
        payload={"lab_name": "Mathis Lab", "institution": ""},
        deployment={"deployment_id": "from-env", "label": "Env"},
        if_exists=DuplicatePolicy.REJECT,
    )


def test_ensure_lab_forwards_policy_and_deployment():
    deployment = {"deployment_id": "explicit", "label": ""}
    with patch.object(lab_admin, "insert_tracked_row") as write:
        lab_admin.ensure_lab(
            {"lab_id": "mlai"}, deployment=deployment, if_exists=DuplicatePolicy.VERIFY
        )
    assert write.call_args.kwargs["deployment"] == deployment
    assert write.call_args.kwargs["if_exists"] is DuplicatePolicy.VERIFY


def test_ensure_lab_requires_deployment(monkeypatch):
    monkeypatch.delenv("SCENE_DEPLOYMENT_ID", raising=False)
    with pytest.raises(ValueError, match="SCENE_DEPLOYMENT_ID"):
        lab_admin.ensure_lab({"lab_id": "mlai"})


def test_ensure_project_delegates_to_insert_tracked_row(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "from-env")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "Env")
    row = {"project_name": "gaze_v1", "project_title": "Gaze"}
    with patch.object(
        project_admin, "insert_tracked_row", return_value={"project_name": "gaze_v1"}
    ) as write:
        key = project_admin.ensure_project(row)

    assert key == {"project_name": "gaze_v1"}
    write.assert_called_once_with(
        project_admin.ProjectRowMeta,
        row,
        payload={"project_title": "Gaze"},
        deployment={"deployment_id": "from-env", "label": "Env"},
        if_exists=DuplicatePolicy.REJECT,
    )
