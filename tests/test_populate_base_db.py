import datetime as dt
import json

import numpy as np
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


def _write_payload(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_npy_payload(path, payload):
    np.save(path, payload, allow_pickle=True)


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


@pytest.fixture
def inserted_two_sessions(inserted_session):
    Session = inserted_session["Session"]
    Session.insert1(
        {
            **_session_row(),
            "day": 10,
            "doe": dt.date(2025, 1, 10),
            "session_increment": 2,
        },
        skip_duplicates=True,
    )
    return inserted_session


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
    _write_payload(payload_path, payload)

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


def test_populate_base_inserts_multiple_files_in_sorted_order(inserted_session, tmp_path):
    Session = inserted_session["Session"]

    first_payload = {
        **_populate_payload(),
        "doe": "2025-01-03",
        "doc": "2025-01-03",
        "day": 3,
        "session_increment": 2,
    }
    second_payload = {
        **_populate_payload(),
        "doe": "2025-01-03",
        "doc": "2025-01-03",
        "attempt": "2",
        "day": 3,
        "session_increment": 3,
    }
    third_payload = {
        **_populate_payload(),
        "doe": "2025-01-04",
        "doc": "2025-01-04",
        "day": 4,
        "session_increment": 4,
    }

    _write_payload(tmp_path / "TestMouse_2025-01-04_1.json", third_payload)
    _write_payload(tmp_path / "TestMouse_2025-01-03_2.json", second_payload)
    _write_payload(tmp_path / "TestMouse_2025-01-03_1.json", first_payload)

    populate_base(path_to_basemeta=tmp_path, fix_dates=False)

    inserted_rows = (Session & {"mouse_name": "TestMouse"} & "day > 1").to_dicts(
        order_by=["doe ASC", "attempt ASC"]
    )
    assert [(row["doe"], row["attempt"], row["session_increment"]) for row in inserted_rows] == [
        (dt.date(2025, 1, 3), 1, 2),
        (dt.date(2025, 1, 3), 2, 3),
        (dt.date(2025, 1, 4), 1, 4),
    ]


def test_populate_base_rejects_session_before_latest_existing(inserted_two_sessions, tmp_path):
    Session = inserted_two_sessions["Session"]
    payload = {
        **_populate_payload(),
        "doe": "2025-01-05",
        "doc": "2025-01-05",
        "day": 5,
        "session_increment": 3,
    }
    _write_payload(tmp_path / "TestMouse_2025-01-05_1.json", payload)

    with pytest.raises(ValueError, match="latest existing session date"):
        populate_base(path_to_basemeta=tmp_path, fix_dates=False)

    assert len(Session()) == 2


def test_populate_base_suppress_errors_continues_after_invalid_file(inserted_session, tmp_path):
    Session = inserted_session["Session"]

    valid_payload = {
        **_populate_payload(),
        "doe": "2025-01-03",
        "doc": "2025-01-03",
        "day": 3,
        "session_increment": 2,
    }
    invalid_payload = {
        **_populate_payload(),
        "mouse_name": "OtherMouse",
        "doe": "2025-01-04",
        "doc": "2025-01-04",
        "day": 4,
        "session_increment": 3,
    }

    _write_payload(tmp_path / "TestMouse_2025-01-03_1.json", valid_payload)
    _write_payload(tmp_path / "TestMouse_2025-01-04_1.json", invalid_payload)

    populate_base(path_to_basemeta=tmp_path, suppress_errors=True, fix_dates=False)

    inserted_rows = (Session & {"mouse_name": "TestMouse"}).to_dicts(
        order_by=["doe ASC", "attempt ASC"]
    )
    assert len(inserted_rows) == 2
    assert inserted_rows[-1]["doe"] == dt.date(2025, 1, 3)
    assert inserted_rows[-1]["session_increment"] == 2


def test_populate_base_inserts_npy_payload(inserted_session, tmp_path):
    Session = inserted_session["Session"]
    SessionScoreSheet = inserted_session["SessionScoreSheet"]
    MouseScoreSheet = inserted_session["MouseScoreSheet"]
    MouseScoreSheet_WaterRestriction = inserted_session["MouseScoreSheet_WaterRestriction"]

    payload = {
        **_populate_payload(),
        "doe": "2025-01-03",
        "doc": "2025-01-03",
        "day": 3,
        "session_increment": 2,
    }
    _write_npy_payload(tmp_path / "TestMouse_2025-01-03_1.npy", payload)

    populate_base(path_to_basemeta=tmp_path, fix_dates=False)

    inserted_row = (Session & {"mouse_name": "TestMouse", "day": 3, "attempt": 1}).fetch1()
    assert inserted_row["doe"] == dt.date(2025, 1, 3)
    assert inserted_row["session_increment"] == 2
    assert len(SessionScoreSheet()) == 1
    assert len(MouseScoreSheet()) == 1
    assert len(MouseScoreSheet_WaterRestriction()) == 1


def test_populate_base_fix_dates_true_computes_missing_day_and_increment_for_multiple_files(
    inserted_session, tmp_path
):
    Session = inserted_session["Session"]

    first_payload = _populate_payload()
    first_payload.update(
        {
            "doe": "2025-01-03",
            "doc": "2025-01-03",
        }
    )
    first_payload.pop("day")
    first_payload.pop("session_increment")

    second_payload = _populate_payload()
    second_payload.update(
        {
            "doe": "2025-01-03",
            "doc": "2025-01-03",
            "attempt": "2",
        }
    )
    second_payload.pop("day")
    second_payload.pop("session_increment")

    _write_payload(tmp_path / "TestMouse_2025-01-03_2.json", second_payload)
    _write_payload(tmp_path / "TestMouse_2025-01-03_1.json", first_payload)

    populate_base(path_to_basemeta=tmp_path, fix_dates=True)

    inserted_rows = (Session & {"mouse_name": "TestMouse"} & "day > 1").to_dicts(
        order_by=["doe ASC", "attempt ASC"]
    )
    assert [(row["day"], row["attempt"], row["session_increment"]) for row in inserted_rows] == [
        (3, 1, 2),
        (3, 2, 3),
    ]


def test_populate_base_rejects_missing_day_without_fix_dates(inserted_session, tmp_path):
    Session = inserted_session["Session"]

    payload = _populate_payload()
    payload.update(
        {
            "doe": "2025-01-03",
            "doc": "2025-01-03",
            "session_increment": 2,
        }
    )
    payload.pop("day")

    _write_payload(tmp_path / "TestMouse_2025-01-03_1.json", payload)

    with pytest.raises(ValueError, match="Payload must include day"):
        populate_base(path_to_basemeta=tmp_path, fix_dates=False)

    assert len(Session()) == 1


def test_populate_base_rejects_wrong_day_without_fix_dates(inserted_session, tmp_path):
    Session = inserted_session["Session"]

    payload = {
        **_populate_payload(),
        "doe": "2025-01-03",
        "doc": "2025-01-03",
        "day": 99,
        "session_increment": 2,
    }

    _write_payload(tmp_path / "TestMouse_2025-01-03_1.json", payload)

    with pytest.raises(ValueError, match="Payload day 99 does not match computed day 3"):
        populate_base(path_to_basemeta=tmp_path, fix_dates=False)

    assert len(Session()) == 1
