"""Unit tests for reading the transfer GUI's metadata files (no database)."""

import datetime as dt
import json

import numpy as np
import pytest

from base_schemas.ingestion.manifest import SessionManifestEntry
from base_schemas.ingestion.populate import scan_directory

SCORE_SHEET = {
    "license": "N/A",
    "body_condition": "BodyCondition3",
    "general_assay": "Assay5",
    "housing_assay": "Yes",
    "weight_percentage": "2.5",
}


def _metadata(**overrides):
    return {
        "mouse_name": "Tick",
        "doe": "2026-02-12",
        "attempt": 1,
        "experimenter_name": "jdoe",
        "rig_id": 1,
        "task_name": "AR_visual_discrimination",
        **overrides,
    }


def test_scan_directory_reads_json_and_npy(tmp_path):
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata(**SCORE_SHEET)))
    np.save(tmp_path / "Tick_2026-02-11_2.npy", _metadata(doe="2026-02-11", attempt=2))
    (tmp_path / "notes.json").write_text("{}")  # other names are ignored

    manifest = scan_directory(tmp_path)

    assert [(e.session_date, e.attempt) for e in manifest] == [
        (dt.date(2026, 2, 11), 2),
        (dt.date(2026, 2, 12), 1),
    ]
    assert manifest[0].score_sheet is None
    assert manifest[1].score_sheet.model_dump() == {**SCORE_SHEET, "doc": None}  # session date
    assert manifest[1].anesthesia_name == "awake"  # default
    assert manifest[1].source == "Tick_2026-02-12_1.json"


def test_scan_directory_accepts_datetime_doe(tmp_path):
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata(doe="2026-02-12 09:15")))
    assert scan_directory(tmp_path)[0].session_date == dt.date(2026, 2, 12)


def test_scan_directory_rejects_name_content_mismatch(tmp_path):
    (tmp_path / "Tick_2026-02-12_2.json").write_text(json.dumps(_metadata(attempt=1)))
    with pytest.raises(ValueError, match="attempt differs"):
        scan_directory(tmp_path)


def test_scan_directory_rejects_incomplete_score_sheet(tmp_path):
    partial = {"license": "N/A", "body_condition": "BodyCondition3"}
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata(**partial)))
    with pytest.raises(ValueError, match=r"score_sheet\.general_assay\n\s+Field required"):
        scan_directory(tmp_path)


def test_scan_directory_suppress_errors_skips_bad_files(tmp_path):
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata()))
    (tmp_path / "Tick_2026-02-12_2.json").write_text(json.dumps(_metadata(attempt=1)))
    manifest = scan_directory(tmp_path, suppress_errors=True)
    assert [e.source for e in manifest] == ["Tick_2026-02-12_1.json"]


@pytest.mark.parametrize("field", ["experimenter_name", "mouse_name", "rig_id"])
def test_entry_rejects_null_required_field(field):
    with pytest.raises(ValueError, match=field):
        SessionManifestEntry.from_gui_flat_dict(_metadata(**{field: None}))


@pytest.mark.parametrize("field", ["attempt", "task_name"])
def test_entry_missing_field_names_the_field(field):
    raw = _metadata()
    del raw[field]
    with pytest.raises(ValueError, match=field):
        SessionManifestEntry.from_gui_flat_dict(raw)


def test_entry_rejects_non_iso_doe():
    with pytest.raises(ValueError, match=r"session_date\n.*Invalid isoformat"):
        SessionManifestEntry.from_gui_flat_dict(_metadata(doe="12/02/2026"))


def test_entry_null_optional_fields_take_defaults():
    entry = SessionManifestEntry.from_gui_flat_dict(_metadata(session_notes=None, opto_name=None))
    assert (entry.session_notes, entry.opto_name) == ("", "none")


def test_entry_accepts_numpy_values_and_numeric_weight():
    raw = _metadata(attempt=np.int64(2), doe=np.datetime64("2026-02-12T09:15"))
    raw = {**raw, **SCORE_SHEET, "weight_percentage": 2.5}
    entry = SessionManifestEntry.from_gui_flat_dict(raw)
    assert (entry.attempt, entry.session_date) == (2, dt.date(2026, 2, 12))
    assert entry.score_sheet.weight_percentage == "2.5"


def test_manifest_round_trips_through_json():
    entry = SessionManifestEntry.from_gui_flat_dict(_metadata(**SCORE_SHEET), source="x.json")
    loaded = json.loads(json.dumps(entry.model_dump(mode="json")))
    assert SessionManifestEntry.model_validate(loaded) == entry
    assert "source" not in entry.register_kwargs()
    assert entry.register_kwargs()["score_sheet"] == {**SCORE_SHEET, "doc": None}


def test_canonical_entry_rejects_flat_fields():
    canonical = SessionManifestEntry.from_gui_flat_dict(_metadata()).model_dump()
    with pytest.raises(ValueError, match=r"license\n\s+Extra inputs are not permitted"):
        SessionManifestEntry.model_validate({**canonical, "license": "N/A"})


def test_score_sheet_keeps_the_date_of_the_check():
    entry = SessionManifestEntry.from_gui_flat_dict(_metadata(**SCORE_SHEET, doc="2026-02-13"))
    assert entry.score_sheet.doc == dt.date(2026, 2, 13)  # not the session date
    assert entry.register_kwargs()["score_sheet"]["doc"] == dt.date(2026, 2, 13)


def test_date_of_check_alone_is_no_score_sheet():
    assert SessionManifestEntry.from_gui_flat_dict(_metadata(doc="2026-02-13")).score_sheet is None
