import datetime as dt
import json

import pytest

from base_schemas.scripts.populate_base import populate_base


def _mouse_row():
    return {
        "mouse_name": "TestMouse",
        "mouse_id": 42,
        "strain": "N/A",
        "sex": "U",
        "dob": dt.date(2025, 1, 1),
    }


def _session_row():
    return {
        "mouse_name": "TestMouse",
        "day": 1,
        "attempt": 1,
        "doe": dt.date(2025, 1, 1),
        "session_increment": 1,
        "rig_id": 1,
        "experimenter_name": "user",
        "anesthesia_name": "awake",
        "opto_name": "none",
        "task_name": "AR_visual_discrimination",
    }


def _fullmeta_row():
    return {
        **_session_row(),
        "doc": dt.date(2025, 1, 1),
        "housing_assay": "Yes",
        "general_assay": "Assay5",
        "body_condition": "BodyCondition3",
        "license": "N/A",
        "weight_percentage": "5",
    }


def _populate_payload():
    return {
        "mouse_name": "TestMouse",
        "doe": "2025-11-06",
        "attempt": "1",
        "experimenter_name": "user",
        "rig_id": "1",
        "anesthesia_name": "awake",
        "opto_name": "none",
        "task_name": "AR_visual_discrimination",
        "doc": "2025-11-06",
        "housing_assay": "Yes",
        "general_assay": "Assay5",
        "body_condition": "BodyCondition3",
        "license": "N/A",
        "weight_percentage": "5",
        "day": 1,
        "session_increment": 1,
    }


@pytest.fixture
def inserted_mouse(base_schema_context):
    Mouse = base_schema_context["Mouse"]
    Mouse.insert1(_mouse_row(), skip_duplicates=True)
    return base_schema_context


@pytest.fixture
def inserted_session(inserted_mouse):
    Session = inserted_mouse["Session"]
    Session.insert1(_session_row(), skip_duplicates=True)
    return inserted_mouse


def test_mouse_insertion(inserted_mouse):
    Mouse = inserted_mouse["Mouse"]

    assert len(Mouse()) == 1


def test_session_insertion(inserted_session):
    Session = inserted_session["Session"]

    assert len(Session()) == 1


def test_fullmeta_insertion(inserted_session):
    Session = inserted_session["Session"]
    SessionScoreSheet = inserted_session["SessionScoreSheet"]
    MouseScoreSheet = inserted_session["MouseScoreSheet"]
    MouseScoreSheet_WaterRestriction = inserted_session["MouseScoreSheet_WaterRestriction"]

    test_meta = _fullmeta_row()

    MouseScoreSheet.insert1(test_meta, skip_duplicates=True, ignore_extra_fields=True)
    MouseScoreSheet_WaterRestriction.insert1(
        test_meta,
        skip_duplicates=True,
        ignore_extra_fields=True,
    )
    SessionScoreSheet.insert1(test_meta, skip_duplicates=True, ignore_extra_fields=True)

    assert len(Session()) == 1


def test_populate_base_integration_respects_fix_dates(inserted_session, tmp_path):
    Session = inserted_session["Session"]
    SessionScoreSheet = inserted_session["SessionScoreSheet"]
    MouseScoreSheet = inserted_session["MouseScoreSheet"]
    MouseScoreSheet_WaterRestriction = inserted_session["MouseScoreSheet_WaterRestriction"]

    payload = _populate_payload()
    payload_path = tmp_path / "TestMouse_2025-11-06_1.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Payload day"):
        populate_base(path_to_basemeta=tmp_path, fix_dates=False)

    assert len(Session()) == 1
    assert len(SessionScoreSheet()) == 0
    assert len(MouseScoreSheet()) == 0
    assert len(MouseScoreSheet_WaterRestriction()) == 0

    populate_base(path_to_basemeta=tmp_path, fix_dates=True)

    assert len(Session()) == 2
    assert len(SessionScoreSheet()) == 1
    assert len(MouseScoreSheet()) == 1
    assert len(MouseScoreSheet_WaterRestriction()) == 1

    inserted_row = (Session & {"mouse_name": "TestMouse", "day": 310, "attempt": 1}).fetch1()
    assert inserted_row["doe"] == dt.date(2025, 11, 6)
    assert inserted_row["session_increment"] == 2

    populate_base(path_to_basemeta=tmp_path, fix_dates=True)

    assert len(Session()) == 2
    assert len(MouseScoreSheet()) == 1
    assert len(MouseScoreSheet_WaterRestriction()) == 1
    assert len(SessionScoreSheet()) == 1
