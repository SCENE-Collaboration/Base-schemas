"""Unit tests for core content_hash / DjKey / DjRow (no DataJoint / MySQL)."""

from datetime import date

from base_schemas.core.hash import content_hash


def test_content_hash_stable():
    payload = {"a": 1, "b": ["x", "y"], "c": None}
    assert content_hash(payload) == content_hash(payload)
    assert len(content_hash(payload)) == 64


def test_content_hash_key_order_independent():
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})


def test_content_hash_changes_with_payload():
    base = {
        "session_date": str(date(2026, 1, 15)),
        "task_name": "gaze",
        "subject_ids": ["kccl-00001"],
    }
    assert content_hash(base) != content_hash({**base, "task_name": "reach"})
    assert content_hash(base) != content_hash({**base, "subject_ids": ["kccl-00002"]})


def test_content_hash_default_str_for_non_json_types():
    """dates and similar use default=str so hashing does not raise."""
    h = content_hash({"session_date": date(2026, 1, 15)})
    assert len(h) == 64
    assert h == content_hash({"session_date": "2026-01-15"})
