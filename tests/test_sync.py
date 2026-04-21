"""Unit tests for base_schemas.scripts.sync.

These tests mock out dj.Instance and FreeTable. They verify argument plumbing
and the sync loop logic without needing two live MySQL servers.
"""

from unittest.mock import MagicMock, patch

import pytest

from base_schemas.scripts import sync


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeFreeTable:
    """Minimal FreeTable double. Holds rows in a list keyed by dict tuple."""

    def __init__(self, name, rows=None):
        self.full_table_name = name
        self._rows = list(rows or [])
        self._last_restriction = None
        self.connection = MagicMock()
        self.connection.transaction = FakeTransaction()

    def __and__(self, restriction):
        self._last_restriction = restriction
        return self

    def fetch(self, as_dict=False):
        assert as_dict is True
        return list(self._rows)

    def __len__(self):
        return len(self._rows)

    def insert(self, rows, skip_duplicates=True, ignore_extra_fields=True):
        assert skip_duplicates is True
        assert ignore_extra_fields is True
        # crude de-dup by tuple of sorted items
        existing = {tuple(sorted(r.items())) for r in self._rows}
        for r in rows:
            key = tuple(sorted(r.items()))
            if key not in existing:
                self._rows.append(r)
                existing.add(key)


class FakeInstance:
    def __init__(self, tables):
        # tables: dict full_name -> FakeFreeTable
        self._tables = tables

    def FreeTable(self, full_name):
        return self._tables[full_name]


def _fake_table_class(full_name):
    cls = MagicMock()
    cls.full_table_name = full_name
    return cls


@pytest.fixture
def patch_instance_api():
    """Ensure sync._require_instance_api passes even on older datajoint."""
    with patch.object(sync.dj, "Instance", create=True) as _:
        yield


def test_sync_inserts_missing_rows(patch_instance_api):
    Mouse = _fake_table_class("`mice`.`mouse`")
    src_rows = [
        {"mouse_name": "A", "mouse_id": 1},
        {"mouse_name": "B", "mouse_id": 2},
    ]
    source_mouse = FakeFreeTable("`mice`.`mouse`", rows=src_rows)
    target_mouse = FakeFreeTable("`mice`.`mouse`", rows=[{"mouse_name": "A", "mouse_id": 1}])

    source_instance = FakeInstance({"`mice`.`mouse`": source_mouse})
    target_instance = FakeInstance({"`mice`.`mouse`": target_mouse})

    with patch.object(sync, "_build_instance", side_effect=[source_instance, target_instance]):
        results = sync.sync_tables(
            {"host": "src", "user": "u", "password": "p"},
            {"host": "tgt", "user": "u", "password": "p"},
            tables=[Mouse],
        )

    assert results["`mice`.`mouse`"] == {"fetched": 2, "inserted": 1}
    assert len(target_mouse) == 2


def test_sync_is_idempotent(patch_instance_api):
    Mouse = _fake_table_class("`mice`.`mouse`")
    rows = [{"mouse_name": "A", "mouse_id": 1}]
    source_mouse = FakeFreeTable("`mice`.`mouse`", rows=rows)
    target_mouse = FakeFreeTable("`mice`.`mouse`", rows=list(rows))

    source_instance = FakeInstance({"`mice`.`mouse`": source_mouse})
    target_instance = FakeInstance({"`mice`.`mouse`": target_mouse})

    with patch.object(sync, "_build_instance", side_effect=[source_instance, target_instance]):
        results = sync.sync_tables(
            {"host": "src", "user": "u", "password": "p"},
            {"host": "tgt", "user": "u", "password": "p"},
            tables=[Mouse],
        )

    assert results["`mice`.`mouse`"] == {"fetched": 1, "inserted": 0}


def test_sync_applies_restriction(patch_instance_api):
    Session = _fake_table_class("`exp`.`session`")
    source_session = FakeFreeTable("`exp`.`session`", rows=[{"mouse_name": "A", "doe": "2026-01-01"}])
    target_session = FakeFreeTable("`exp`.`session`")

    source_instance = FakeInstance({"`exp`.`session`": source_session})
    target_instance = FakeInstance({"`exp`.`session`": target_session})

    with patch.object(sync, "_build_instance", side_effect=[source_instance, target_instance]):
        sync.sync_tables(
            {"host": "src", "user": "u", "password": "p"},
            {"host": "tgt", "user": "u", "password": "p"},
            tables=[Session],
            restrictions={Session: "doe >= '2026-01-01'"},
        )

    assert source_session._last_restriction == "doe >= '2026-01-01'"


def test_sync_processes_tables_in_order(patch_instance_api):
    Mouse = _fake_table_class("`mice`.`mouse`")
    Session = _fake_table_class("`exp`.`session`")
    calls = []

    class OrderTrackingTable(FakeFreeTable):
        def fetch(self, as_dict=False):
            calls.append(("fetch", self.full_table_name))
            return super().fetch(as_dict=as_dict)

    source_instance = FakeInstance({
        "`mice`.`mouse`": OrderTrackingTable("`mice`.`mouse`"),
        "`exp`.`session`": OrderTrackingTable("`exp`.`session`"),
    })
    target_instance = FakeInstance({
        "`mice`.`mouse`": FakeFreeTable("`mice`.`mouse`"),
        "`exp`.`session`": FakeFreeTable("`exp`.`session`"),
    })

    with patch.object(sync, "_build_instance", side_effect=[source_instance, target_instance]):
        sync.sync_tables(
            {"host": "src", "user": "u", "password": "p"},
            {"host": "tgt", "user": "u", "password": "p"},
            tables=[Mouse, Session],
        )

    assert [c[1] for c in calls] == ["`mice`.`mouse`", "`exp`.`session`"]


def test_build_instance_forwards_optional_keys():
    captured = {}

    def fake_ctor(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    with patch.object(sync.dj, "Instance", side_effect=fake_ctor, create=True):
        sync._build_instance({
            "host": "h",
            "user": "u",
            "password": "p",
            "port": 3307,
            "use_tls": False,
        })

    assert captured == {"host": "h", "user": "u", "password": "p", "port": 3307, "use_tls": False}


def test_require_instance_api_raises_when_missing(monkeypatch):
    if hasattr(sync.dj, "Instance"):
        monkeypatch.delattr(sync.dj, "Instance")
    with pytest.raises(ImportError, match="datajoint>=2.2"):
        sync._require_instance_api()
