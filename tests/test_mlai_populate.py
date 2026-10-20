"""Unit tests for reading the transfer GUI's metadata files (no database)."""

import json

import numpy as np
import pytest

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

    assert [(e["session_date"], e["attempt"]) for e in manifest] == [
        ("2026-02-11", 2),
        ("2026-02-12", 1),
    ]
    assert manifest[0]["score_sheet"] is None
    assert manifest[1]["score_sheet"] == SCORE_SHEET
    assert manifest[1]["anesthesia_name"] == "awake"  # default
    assert manifest[1]["source"] == "Tick_2026-02-12_1.json"


def test_scan_directory_accepts_datetime_doe(tmp_path):
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata(doe="2026-02-12 09:15")))
    assert scan_directory(tmp_path)[0]["session_date"] == "2026-02-12"


def test_scan_directory_rejects_name_content_mismatch(tmp_path):
    (tmp_path / "Tick_2026-02-12_2.json").write_text(json.dumps(_metadata(attempt=1)))
    with pytest.raises(ValueError, match="attempt differs"):
        scan_directory(tmp_path)


def test_scan_directory_rejects_incomplete_score_sheet(tmp_path):
    partial = {"license": "N/A", "body_condition": "BodyCondition3"}
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata(**partial)))
    with pytest.raises(ValueError, match="incomplete score sheet"):
        scan_directory(tmp_path)


def test_scan_directory_suppress_errors_skips_bad_files(tmp_path):
    (tmp_path / "Tick_2026-02-12_1.json").write_text(json.dumps(_metadata()))
    (tmp_path / "Tick_2026-02-12_2.json").write_text(json.dumps(_metadata(attempt=1)))
    manifest = scan_directory(tmp_path, suppress_errors=True)
    assert [e["source"] for e in manifest] == ["Tick_2026-02-12_1.json"]
