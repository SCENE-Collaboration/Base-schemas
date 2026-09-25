"""Unit tests for subject-id normalization."""

import pytest
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


def test_normalize_subject_ids_requires_at_least_one():
    with pytest.raises(ValueError, match="at least one subject_id"):
        normalize_subject_ids(["", "  "])
