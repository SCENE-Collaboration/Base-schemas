"""Unit tests for subject-id normalization."""

from base_schemas.ingestion.normalization import normalize_subject_ids


def test_normalize_subject_ids_single_string():
    assert normalize_subject_ids("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") == [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]


def test_normalize_subject_ids_dedupes_and_strips():
    assert normalize_subject_ids(["  aaa  ", "bbb", "aaa", "", "  ", "ccc"]) == [
        "aaa",
        "bbb",
        "ccc",
    ]


def test_normalize_subject_ids_allows_empty():
    assert normalize_subject_ids([]) == []
    assert normalize_subject_ids(["", "  "]) == []
