"""Live-DB tests for the MLAI write helpers."""

import datetime as dt
import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DJ_HOST"), reason="requires DataJoint DB (set DJ_HOST)"
)

PROJECT = {"project_name": "mousear", "project_title": "MouseAR test project"}
PROJECT_KEY = {"project_name": PROJECT["project_name"]}


@pytest.fixture
def mlai(dj_connection, monkeypatch):
    """The ``ingestion`` module, with the schemas bound and the MLAI lab registered."""
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    from scene_pipelines.core import SCENE_REGISTRY
    from scene_pipelines.ingestion.provenance import DuplicatePolicy
    from scene_pipelines.ingestion.scene import admin

    from base_schemas.ingestion import ingestion

    SCENE_REGISTRY.activate_all()
    admin.ensure_lab(ingestion.MLAI_LAB, if_exists=DuplicatePolicy.VERIFY)
    admin.ensure_project(PROJECT, if_exists=DuplicatePolicy.VERIFY)
    return ingestion


def test_register_mlai_mouse_taken_facility_id_raises(mlai):
    import datajoint as dj
    from scene_pipelines.schemas.scene.subject import Subject

    mlai.register_mlai_mouse("clash-1", "F", mouse_id=90001)
    with pytest.raises(dj.errors.DuplicateError):
        mlai.register_mlai_mouse("clash-2", "M", mouse_id=90001)
    assert not (Subject & {**mlai.MLAI_LAB_KEY, "subject_code": "clash-2"})  # rolled back


def test_ensure_mlai_experimenter_taken_name_raises(mlai):
    import datajoint as dj
    from scene_pipelines.schemas.scene.session import Experimenter

    key = mlai.ensure_mlai_experimenter("exp-clash-1", "clashname")
    assert mlai.ensure_mlai_experimenter("exp-clash-1", "clashname") == key
    with pytest.raises(dj.errors.DuplicateError):
        mlai.ensure_mlai_experimenter("exp-clash-2", "clashname")
    assert not (Experimenter & {**mlai.MLAI_LAB_KEY, "experimenter_code": "exp-clash-2"})


def test_populate_base_registers_new_sessions_once(mlai, tmp_path):
    from scene_pipelines.schemas.scene.session import Session

    from base_schemas.ingestion import populate_base
    from base_schemas.schemas.session import SessionInfo

    mlai.ensure_mlai_experimenter("E-pop", "popuser")
    mlai.register_mlai_mouse("Pop", "F", mouse_id=90101)
    metadata = {
        "mouse_name": "Pop",
        "doe": "2026-02-12",
        "attempt": 1,
        "experimenter_name": "popuser",
        "rig_id": 1,
        "task_name": "AR_visual_discrimination",
    }
    (tmp_path / "Pop_2026-02-12_1.json").write_text(json.dumps(metadata))
    (tmp_path / "Unknown_2026-02-12_1.json").write_text(
        json.dumps({**metadata, "mouse_name": "Unknown"})
    )

    new = populate_base(tmp_path, project=PROJECT_KEY)

    assert list((Session & new).to_arrays("session_code")) == ["Pop_2026-02-12_1"]
    assert (Session & new).fetch1("session_date") == dt.date(2026, 2, 12)
    assert (SessionInfo & new).fetch1("attempt") == 1
    assert populate_base(tmp_path, project=PROJECT_KEY) == []  # nothing new on a re-run


def test_mlai_mice_and_available_mice(mlai):
    from base_schemas.queries import available_mice, mlai_mice
    from base_schemas.schemas.mouse import Breed, Sacrificed

    for name, mouse_id in (("Avail", 90201), ("Gone", 90202), ("Breeder", 90203)):
        mlai.register_mlai_mouse(name, "F", mouse_id=mouse_id)
    gone, breeder = mlai_mice("Gone").keys()[0], mlai_mice("Breeder").keys()[0]
    Sacrificed.insert1({**gone, "date_of_sacrifice": "2026-02-12", "reason": "test"})
    Breed.insert1(breeder)

    assert mlai_mice("Avail").fetch1("mouse_id") == 90201
    assert len(mlai_mice("Avail", "Gone")) == 2
    available = set(available_mice().to_arrays("subject_code"))
    assert "Avail" in available and not available & {"Gone", "Breeder"}
