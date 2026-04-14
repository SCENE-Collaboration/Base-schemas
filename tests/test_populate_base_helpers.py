import datetime as dt
import json
from pathlib import Path

import numpy as np
import pytest

from base_schemas.scripts.populate_base import (
    _compute_session_fields,
    _discover_candidate_files,
    _load_payload,
    _normalize_payload,
    _parse_candidate_path,
)


class FakeMouseRelation:
    def __init__(self, starting_date, next_increment, latest_session_date=None):
        self._starting_date = starting_date
        self._next_increment = next_increment
        self._latest_session_date = latest_session_date

    def get_starting_date(self):
        return self._starting_date

    def get_session_increment(self):
        return self._next_increment

    def get_latest_session_date(self):
        return self._latest_session_date


def _example_payload():
    return {
        "mouse_name": "TestMouse",
        "doe": "2025-11-06",
        "attempt": "2",
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
    }


def test_parse_candidate_path():
    metadata = _parse_candidate_path(Path("TestMouse_2025-11-06_2.json"))

    assert metadata == {
        "mouse_name": "TestMouse",
        "doe": dt.date(2025, 11, 6),
        "attempt": 2,
    }


def test_parse_candidate_path_rejects_invalid_name():
    with pytest.raises(ValueError, match="File name bad-name.json must match"):
        _parse_candidate_path(Path("bad-name.json"))


def test_load_payload_json(tmp_path):
    payload_path = tmp_path / "TestMouse_2025-11-06_1.json"
    expected = _example_payload()
    payload_path.write_text(json.dumps(expected), encoding="utf-8")

    assert _load_payload(payload_path) == expected


def test_load_payload_npy(tmp_path):
    payload_path = tmp_path / "TestMouse_2025-11-06_1.npy"
    expected = _example_payload()
    np.save(payload_path, expected, allow_pickle=True)

    assert _load_payload(payload_path) == expected


def test_discover_candidate_files_sorts_by_date_then_attempt(tmp_path):
    ordered_names = [
        "TestMouse_2025-11-05_2.json",
        "TestMouse_2025-11-06_1.npy",
        "TestMouse_2025-11-06_2.json",
    ]
    for file_name in reversed(ordered_names):
        (tmp_path / file_name).write_text("{}", encoding="utf-8")

    discovered = _discover_candidate_files(tmp_path)

    assert [path.name for path in discovered] == ordered_names


def test_normalize_payload_coerces_types():
    payload = _normalize_payload(_example_payload())

    assert payload["doe"] == dt.date(2025, 11, 6)
    assert payload["doc"] == dt.date(2025, 11, 6)
    assert payload["attempt"] == 2
    assert payload["rig_id"] == 1
    assert payload["session_notes"] == ""


def test_compute_session_fields_for_first_session():
    mouse_relation = FakeMouseRelation(starting_date=None, next_increment=0)
    payload = {"mouse_name": "TestMouse", "day": 1, "session_increment": 1}

    day, session_increment = _compute_session_fields(
        mouse_relation,
        dt.date(2025, 11, 6),
        payload,
        fix_dates=False,
    )

    assert day == 1
    assert session_increment == 1


def test_compute_session_fields_for_existing_mouse():
    mouse_relation = FakeMouseRelation(
        starting_date=dt.date(2025, 11, 1),
        next_increment=5,
        latest_session_date=dt.date(2025, 11, 5),
    )
    payload = {"mouse_name": "TestMouse", "day": 6, "session_increment": 5}

    day, session_increment = _compute_session_fields(
        mouse_relation,
        dt.date(2025, 11, 6),
        payload,
        fix_dates=False,
    )

    assert day == 6
    assert session_increment == 5


def test_compute_session_fields_rejects_payload_mismatch_without_fix_dates():
    mouse_relation = FakeMouseRelation(
        starting_date=dt.date(2025, 11, 1),
        next_increment=5,
        latest_session_date=dt.date(2025, 11, 5),
    )
    payload = {"mouse_name": "TestMouse", "day": 1}

    with pytest.raises(ValueError, match="Payload day"):
        _compute_session_fields(
            mouse_relation,
            dt.date(2025, 11, 6),
            payload,
            fix_dates=False,
        )


def test_compute_session_fields_rejects_missing_day_without_fix_dates():
    mouse_relation = FakeMouseRelation(
        starting_date=dt.date(2025, 11, 1),
        next_increment=5,
        latest_session_date=dt.date(2025, 11, 5),
    )
    payload = {"mouse_name": "TestMouse", "session_increment": 5}

    with pytest.raises(ValueError, match="Payload must include day"):
        _compute_session_fields(
            mouse_relation,
            dt.date(2025, 11, 6),
            payload,
            fix_dates=False,
        )


def test_compute_session_fields_allows_payload_mismatch_with_fix_dates():
    mouse_relation = FakeMouseRelation(
        starting_date=dt.date(2025, 11, 1),
        next_increment=5,
        latest_session_date=dt.date(2025, 11, 5),
    )
    payload = {"mouse_name": "TestMouse", "day": 1, "session_increment": 1}

    day, session_increment = _compute_session_fields(
        mouse_relation,
        dt.date(2025, 11, 6),
        payload,
        fix_dates=True,
    )

    assert day == 6
    assert session_increment == 5


def test_compute_session_fields_rejects_session_that_would_be_squeezed_in():
    mouse_relation = FakeMouseRelation(
        starting_date=dt.date(2025, 11, 1),
        next_increment=5,
        latest_session_date=dt.date(2025, 11, 6),
    )
    payload = {"mouse_name": "TestMouse"}

    with pytest.raises(ValueError, match="latest existing session date"):
        _compute_session_fields(
            mouse_relation,
            dt.date(2025, 11, 5),
            payload,
            fix_dates=False,
        )
