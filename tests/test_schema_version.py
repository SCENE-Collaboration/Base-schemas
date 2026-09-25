"""Tests for core schema-version helpers (DataJoint I/O mocked, no MySQL)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from base_schemas.core import versioning as sv
from base_schemas.schemas.experiment._schema import EXPERIMENT_SCHEMA_VERSION


class TestSchemaVersionStatus:
    def test_compatible(self):
        status = sv.SchemaVersionStatus("0.1.0", "0.1.0")
        assert status.is_compatible
        assert not status.is_unset

    def test_unset(self):
        status = sv.SchemaVersionStatus("0.1.0", None)
        assert status.is_unset
        assert not status.is_compatible

    def test_mismatch(self):
        status = sv.SchemaVersionStatus("0.2.0", "0.1.0")
        assert not status.is_compatible
        assert status.db_version == "0.1.0"


def test_experiment_schema_version_constant():
    assert isinstance(EXPERIMENT_SCHEMA_VERSION, str)
    assert EXPERIMENT_SCHEMA_VERSION


def test_get_db_schema_version_none():
    table = MagicMock()
    table.fetch.return_value = []
    assert sv.get_db_schema_version(table) is None
    table.fetch.assert_called_once_with(order_by="applied_at DESC", limit=1, as_dict=True)


def test_get_db_schema_version_latest():
    table = MagicMock()
    table.fetch.return_value = [{"version": "0.2.0", "applied_at": "x"}]
    assert sv.get_db_schema_version(table) == "0.2.0"


def test_get_db_schema_version_uses_first_ordered_row():
    """Latest policy: fetch asks DESC + limit 1; we take rows[0]."""
    table = MagicMock()
    table.fetch.return_value = [
        {"version": "0.2.0", "applied_at": "newer"},
        {"version": "0.1.0", "applied_at": "older"},
    ]
    assert sv.get_db_schema_version(table) == "0.2.0"
    table.fetch.assert_called_once_with(order_by="applied_at DESC", limit=1, as_dict=True)


def test_ensure_then_assert_end_to_end_without_patching_check():
    """Exercise real ensure → assert chain; only table I/O is mocked."""
    table = MagicMock()
    table.fetch.return_value = []
    assert sv.ensure_schema_version("0.1.0", table, notes="init") == "0.1.0"
    table.insert1.assert_called_once()
    assert table.insert1.call_args.args[0]["version"] == "0.1.0"

    table.fetch.return_value = [{"version": "0.1.0", "applied_at": "t"}]
    assert sv.assert_schema_compatible("0.1.0", table) == "0.1.0"


def test_assert_end_to_end_mismatch_without_patching_check():
    table = MagicMock()
    table.fetch.return_value = [{"version": "0.0.0", "applied_at": "t"}]
    with pytest.raises(sv.SchemaVersionError, match="mismatch"):
        sv.assert_schema_compatible("0.1.0", table)


def test_ensure_end_to_end_mismatch_without_patching_check():
    table = MagicMock()
    table.fetch.return_value = [{"version": "0.0.0", "applied_at": "t"}]
    with pytest.raises(sv.SchemaVersionError, match="mismatch"):
        sv.ensure_schema_version("0.1.0", table)
    table.insert1.assert_not_called()


def test_assert_schema_compatible_ok():
    table = MagicMock()
    status = sv.SchemaVersionStatus(EXPERIMENT_SCHEMA_VERSION, EXPERIMENT_SCHEMA_VERSION)
    with patch.object(sv, "check_schema_version", return_value=status):
        assert sv.assert_schema_compatible(EXPERIMENT_SCHEMA_VERSION, table) == (
            EXPERIMENT_SCHEMA_VERSION
        )


def test_assert_schema_compatible_unset():
    table = MagicMock()
    with patch.object(
        sv,
        "check_schema_version",
        return_value=sv.SchemaVersionStatus(EXPERIMENT_SCHEMA_VERSION, None),
    ):
        with pytest.raises(sv.SchemaVersionError, match="not recorded"):
            sv.assert_schema_compatible(EXPERIMENT_SCHEMA_VERSION, table)


def test_assert_schema_compatible_mismatch():
    table = MagicMock()
    with patch.object(
        sv,
        "check_schema_version",
        return_value=sv.SchemaVersionStatus(EXPERIMENT_SCHEMA_VERSION, "0.0.0"),
    ):
        with pytest.raises(sv.SchemaVersionError, match="mismatch"):
            sv.assert_schema_compatible(EXPERIMENT_SCHEMA_VERSION, table)


def test_ensure_ok_no_insert():
    table = MagicMock()
    status = sv.SchemaVersionStatus(EXPERIMENT_SCHEMA_VERSION, EXPERIMENT_SCHEMA_VERSION)
    with patch.object(sv, "check_schema_version", return_value=status):
        assert sv.ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, table) == (
            EXPERIMENT_SCHEMA_VERSION
        )
        table.insert1.assert_not_called()


def test_ensure_seeds_when_unset():
    table = MagicMock()
    with patch.object(
        sv,
        "check_schema_version",
        return_value=sv.SchemaVersionStatus(EXPERIMENT_SCHEMA_VERSION, None),
    ):
        assert (
            sv.ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, table, notes="init")
            == EXPERIMENT_SCHEMA_VERSION
        )
        table.insert1.assert_called_once()
        row = table.insert1.call_args.args[0]
        assert row["version"] == EXPERIMENT_SCHEMA_VERSION
        assert row["notes"] == "init"
        assert "applied_at" in row


def test_ensure_mismatch_raises():
    table = MagicMock()
    with patch.object(
        sv,
        "check_schema_version",
        return_value=sv.SchemaVersionStatus(EXPERIMENT_SCHEMA_VERSION, "0.0.0"),
    ):
        with pytest.raises(sv.SchemaVersionError, match="mismatch"):
            sv.ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, table)
        table.insert1.assert_not_called()
