"""Live-DB tests for the MLAI example's write helpers."""

import os
from pathlib import Path

import pytest

_TRUTHY = frozenset({"1", "true", "yes", "on"})

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
    pytest.mark.skipif(
        (os.getenv("AUTO_ACTIVATE") or "").strip().lower() not in _TRUTHY,
        reason="tables are unbound unless AUTO_ACTIVATE is set",
    ),
]

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "mlai_mouse_ar"


@pytest.fixture
def mlai(dj_connection, monkeypatch):
    """The example's ``ingestion`` module, with the MLAI lab registered."""
    monkeypatch.syspath_prepend(str(EXAMPLE_DIR))
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.ingestion.scene import admin
    from mlai_ingestion import ingestion

    admin.ensure_lab(ingestion.MLAI_LAB, if_exists=DuplicatePolicy.VERIFY)
    return ingestion


@pytest.mark.xfail(
    strict=True,
    raises=pytest.fail.Exception,  # only "DID NOT RAISE"; setup errors still fail
    reason="skip_duplicates silently skips the unique-index clash on MouseInfo.mouse_id",
)
def test_register_mlai_mouse_taken_facility_id_raises(mlai):
    import datajoint as dj
    from base_schemas.schemas.scene.subject import Subject

    mlai.register_mlai_mouse("clash-1", "F", mouse_id=90001)
    with pytest.raises(dj.errors.DuplicateError):
        mlai.register_mlai_mouse("clash-2", "M", mouse_id=90001)
    assert not (Subject & {**mlai.MLAI_LAB_KEY, "subject_code": "clash-2"})  # rolled back
