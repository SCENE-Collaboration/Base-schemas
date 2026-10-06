"""Unit tests for insert_tracked_row / DuplicatePolicy (no MySQL)."""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from base_schemas.core.hash import content_hash
from base_schemas.ingestion.provenance import row_meta as row_meta_mod
from base_schemas.ingestion.provenance.ingestion_version import SCENE_WRITER_VERSION
from base_schemas.ingestion.provenance.row_meta import DuplicatePolicy, insert_tracked_row

_DEPLOYMENT = {"deployment_id": "dep1", "label": "Dep"}
_LAB = {"lab_id": "mlai", "lab_name": "Mathis Lab", "institution": "EPFL"}
_LAB_KEY = {"lab_id": "mlai"}
_PAYLOAD = {"lab_name": "Mathis Lab", "institution": "EPFL"}


class _Restriction:
    def __init__(self, table, key):
        self._row = table.rows.get(table.key_of(key))

    def __bool__(self):
        return self._row is not None

    def fetch1(self, attr):
        return self._row[attr]


class _FakeConnection:
    """Tracks transaction nesting the way dj.Connection does (no nesting allowed)."""

    def __init__(self):
        self.in_transaction = False
        self.transactions = 0

    @property
    @contextmanager
    def transaction(self):
        assert not self.in_transaction, "nested transaction"
        self.in_transaction = True
        self.transactions += 1
        try:
            yield
        finally:
            self.in_transaction = False


class _FakeTable:
    """In-memory stand-in for the DataJoint table surface used by insert_tracked_row."""

    def __init__(self, name, primary_key, rows=(), connection=None, secondary=()):
        self.__name__ = name
        self.primary_key = list(primary_key)
        self.heading = SimpleNamespace(secondary_attributes=list(secondary))
        self.rows = {self.key_of(row): dict(row) for row in rows}
        self.calls = []
        self.connection = connection or _FakeConnection()
        self.database = "fake_db"

    def key_of(self, row):
        return tuple(row[name] for name in self.primary_key)

    def __and__(self, key):
        return _Restriction(self, key)

    def insert1(self, row, **kwargs):
        self.calls.append(("insert1", dict(row)))
        key = self.key_of(row)
        if key in self.rows:
            if kwargs.get("skip_duplicates"):
                return
            raise AssertionError(f"duplicate insert into {self.__name__}: {row}")
        self.rows[key] = dict(row)

    def update1(self, row):
        self.calls.append(("update1", dict(row)))
        self.rows[self.key_of(row)].update(row)


class _FakeMeta(_FakeTable):
    def __init__(self, tracked, rows=()):
        super().__init__(f"{tracked.__name__}RowMeta", tracked.primary_key, rows)
        self.tracked_table = tracked

    def tracked_key(self, row):
        return {name: row[name] for name in self.tracked_table.primary_key}


class _FakePart:
    """Part table stand-in keyed by (lab_id, member); records the statements it receives."""

    primary_key = ["lab_id", "member"]

    def __init__(self, rows=(), secondary=()):
        self.heading = SimpleNamespace(secondary_attributes=list(secondary))
        self.rows = [dict(row) for row in rows]
        self.calls = []

    def insert(self, rows):
        rows = [dict(row) for row in rows]
        self.calls.append(("insert", rows))
        self.rows.extend(rows)

    def update1(self, row):
        self.calls.append(("update1", dict(row)))
        stored = next(r for r in self.rows if all(r[k] == row[k] for k in self.primary_key))
        stored.update(row)

    def __and__(self, key):
        part = self

        def matches(row):
            return all(row[k] == v for k, v in key.items())

        class _Restricted:
            def keys(self):
                return [{k: r[k] for k in part.primary_key} for r in part.rows if matches(r)]

            def delete_quick(self):
                part.calls.append(("delete_quick", dict(key)))
                part.rows = [r for r in part.rows if not matches(r)]

        return _Restricted()


def _stamp(payload=_PAYLOAD, **overrides):
    return {
        **_LAB_KEY,
        "deployment_id": "old-dep",
        "ingestion_version": "0.0.0",
        "content_hash": content_hash(payload),
        **overrides,
    }


@pytest.fixture(autouse=True)
def no_version_check(monkeypatch):
    """The fake tables have no database; the version check is tested in test_schema_version."""
    monkeypatch.setattr(row_meta_mod, "assert_database_compatible", lambda database: None)


@pytest.fixture
def deployment_table():
    table = _FakeTable("Deployment", ["deployment_id"])
    with patch.object(row_meta_mod, "Deployment", table):
        yield table


def _tables(*, lab_exists: bool, stamp: dict | None = None):
    lab = _FakeTable(
        "Lab", ["lab_id"], [_LAB] if lab_exists else (), secondary=["lab_name", "institution"]
    )
    meta = _FakeMeta(lab, [stamp] if stamp else ())
    return lab, meta


def _insert(meta, policy, row=_LAB, payload=_PAYLOAD, **kwargs):
    return insert_tracked_row(
        meta, row, payload=payload, deployment=_DEPLOYMENT, if_exists=policy, **kwargs
    )


@pytest.mark.parametrize("policy", list(DuplicatePolicy))
def test_new_key_is_inserted_and_stamped(deployment_table, policy):
    lab, meta = _tables(lab_exists=False)

    assert _insert(meta, policy) == _LAB_KEY

    assert lab.rows[("mlai",)] == _LAB
    stamp = meta.rows[("mlai",)]
    assert stamp["deployment_id"] == "dep1"
    assert stamp["ingestion_version"] == SCENE_WRITER_VERSION
    assert stamp["content_hash"] == content_hash(_PAYLOAD)
    assert "updated_at" in stamp
    assert deployment_table.rows[("dep1",)] == _DEPLOYMENT


def test_opens_own_transaction_when_none_is_open(deployment_table):
    lab, meta = _tables(lab_exists=False)
    _insert(meta, DuplicatePolicy.REJECT)
    assert lab.connection.transactions == 1
    assert lab.connection.in_transaction is False


def test_joins_open_transaction(deployment_table):
    lab, meta = _tables(lab_exists=False)
    with lab.connection.transaction:
        _insert(meta, DuplicatePolicy.REJECT)
        assert lab.connection.in_transaction is True
    assert lab.connection.transactions == 1


def test_writer_version_override(deployment_table):
    _, meta = _tables(lab_exists=False)
    _insert(meta, DuplicatePolicy.REJECT, writer_version="9.9.9")
    assert meta.rows[("mlai",)]["ingestion_version"] == "9.9.9"


def test_reject_raises_for_existing_key(deployment_table):
    lab, meta = _tables(lab_exists=True, stamp=_stamp())
    with pytest.raises(ValueError, match="Lab row .* is already registered"):
        _insert(meta, DuplicatePolicy.REJECT)
    assert lab.calls == [] and meta.calls == []


@pytest.mark.parametrize("stamp", [None, _stamp(), _stamp({"lab_name": "other"})])
def test_skip_leaves_row_and_stamp_untouched(deployment_table, stamp):
    lab, meta = _tables(lab_exists=True, stamp=stamp)
    new_row = {**_LAB, "lab_name": "Renamed"}

    assert _insert(meta, DuplicatePolicy.SKIP, row=new_row) == _LAB_KEY

    assert lab.rows[("mlai",)] == _LAB
    assert lab.calls == [] and meta.calls == []
    assert deployment_table.rows == {}


def test_verify_accepts_matching_hash(deployment_table):
    lab, meta = _tables(lab_exists=True, stamp=_stamp())
    assert _insert(meta, DuplicatePolicy.VERIFY) == _LAB_KEY
    assert lab.calls == [] and meta.calls == []


def test_verify_raises_when_hash_differs(deployment_table):
    _, meta = _tables(lab_exists=True, stamp=_stamp({"lab_name": "other"}))
    with pytest.raises(ValueError, match="different content hash"):
        _insert(meta, DuplicatePolicy.VERIFY)


def test_verify_raises_when_stamp_is_missing(deployment_table):
    _, meta = _tables(lab_exists=True)
    with pytest.raises(ValueError, match="no provenance stamp"):
        _insert(meta, DuplicatePolicy.VERIFY)


def test_overwrite_updates_row_and_stamp_without_warning_when_hash_matches(deployment_table):
    lab, meta = _tables(lab_exists=True, stamp=_stamp())

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        assert _insert(meta, DuplicatePolicy.OVERWRITE) == _LAB_KEY

    assert [name for name, _ in lab.calls] == ["update1"]
    assert [name for name, _ in meta.calls] == ["update1"]
    stamp = meta.rows[("mlai",)]
    assert stamp["deployment_id"] == "dep1"
    assert stamp["ingestion_version"] == SCENE_WRITER_VERSION
    assert deployment_table.rows[("dep1",)] == _DEPLOYMENT


def test_overwrite_warns_and_updates_when_hash_differs(deployment_table):
    lab, meta = _tables(lab_exists=True, stamp=_stamp())
    new_row = {**_LAB, "lab_name": "Renamed"}
    new_payload = {**_PAYLOAD, "lab_name": "Renamed"}

    with pytest.warns(UserWarning, match="content hash changed"):
        _insert(meta, DuplicatePolicy.OVERWRITE, row=new_row, payload=new_payload)

    assert lab.rows[("mlai",)]["lab_name"] == "Renamed"
    assert meta.rows[("mlai",)]["content_hash"] == content_hash(new_payload)


def test_overwrite_resets_omitted_fields_to_their_default(deployment_table):
    """OVERWRITE stores the row as an insert would: update1 resets None to the default."""
    lab, meta = _tables(lab_exists=True, stamp=_stamp())
    _insert(meta, DuplicatePolicy.OVERWRITE, row={"lab_id": "mlai", "lab_name": "Mathis Lab"})
    assert lab.calls == [
        ("update1", {"lab_id": "mlai", "lab_name": "Mathis Lab", "institution": None})
    ]


def test_overwrite_inserts_stamp_when_missing(deployment_table):
    lab, meta = _tables(lab_exists=True)

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _insert(meta, DuplicatePolicy.OVERWRITE)

    assert [name for name, _ in lab.calls] == ["update1"]
    assert [name for name, _ in meta.calls] == ["insert1"]
    assert meta.rows[("mlai",)]["content_hash"] == content_hash(_PAYLOAD)


def test_unknown_policy_is_rejected(deployment_table):
    _, meta = _tables(lab_exists=True)
    with pytest.raises(ValueError, match="unknown DuplicatePolicy"):
        _insert(meta, "bogus")


def test_parts_are_inserted_with_a_new_row(deployment_table):
    _, meta = _tables(lab_exists=False)
    part = _FakePart()
    _insert(meta, DuplicatePolicy.REJECT, parts={part: [{"member": "a"}, {"member": "b"}]})
    assert part.rows == [{**_LAB_KEY, "member": "a"}, {**_LAB_KEY, "member": "b"}]


def test_overwrite_replaces_parts_of_this_row_only(deployment_table):
    _, meta = _tables(lab_exists=True, stamp=_stamp())
    other = {"lab_id": "other", "member": "x"}
    part = _FakePart([{**_LAB_KEY, "member": "old"}, other])
    _insert(meta, DuplicatePolicy.OVERWRITE, parts={part: [{"member": "new"}]})
    assert part.rows == [other, {**_LAB_KEY, "member": "new"}]


def test_overwrite_touches_only_the_parts_that_differ(deployment_table):
    """A part row that stays is not deleted: another table may reference it."""
    _, meta = _tables(lab_exists=True, stamp=_stamp())
    part = _FakePart([{**_LAB_KEY, "member": "kept"}, {**_LAB_KEY, "member": "gone"}])
    _insert(meta, DuplicatePolicy.OVERWRITE, parts={part: [{"member": "kept"}, {"member": "new"}]})
    assert part.calls == [
        ("delete_quick", {**_LAB_KEY, "member": "gone"}),
        ("insert", [{**_LAB_KEY, "member": "new"}]),
    ]
    assert part.rows == [{**_LAB_KEY, "member": "kept"}, {**_LAB_KEY, "member": "new"}]


def test_overwrite_with_unchanged_parts_writes_no_part_rows(deployment_table):
    _, meta = _tables(lab_exists=True, stamp=_stamp())
    part = _FakePart([{**_LAB_KEY, "member": "kept"}])
    _insert(meta, DuplicatePolicy.OVERWRITE, parts={part: [{"member": "kept"}]})
    assert part.calls == []


def test_overwrite_updates_the_fields_of_a_part_that_stays(deployment_table):
    _, meta = _tables(lab_exists=True, stamp=_stamp())
    part = _FakePart([{**_LAB_KEY, "member": "kept", "role": "old"}], secondary=["role", "note"])
    _insert(meta, DuplicatePolicy.OVERWRITE, parts={part: [{"member": "kept", "role": "new"}]})
    assert part.calls == [("update1", {**_LAB_KEY, "member": "kept", "role": "new", "note": None})]


@pytest.mark.parametrize("policy", [DuplicatePolicy.SKIP, DuplicatePolicy.VERIFY])
def test_parts_untouched_when_row_is_kept(deployment_table, policy):
    _, meta = _tables(lab_exists=True, stamp=_stamp())
    part = _FakePart([{**_LAB_KEY, "member": "old"}])
    _insert(meta, policy, parts={part: [{"member": "new"}]})
    assert part.rows == [{**_LAB_KEY, "member": "old"}]


def test_existing_deployment_with_same_label_is_left_alone(deployment_table):
    deployment_table.rows[("dep1",)] = dict(_DEPLOYMENT)
    _, meta = _tables(lab_exists=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _insert(meta, DuplicatePolicy.REJECT)
    assert [name for name, _ in deployment_table.calls] == []


def test_existing_deployment_with_other_label_warns_and_keeps_label(deployment_table):
    deployment_table.rows[("dep1",)] = {**_DEPLOYMENT, "label": "Old label"}
    _, meta = _tables(lab_exists=False)
    with pytest.warns(UserWarning, match="keeps its stored label 'Old label'"):
        _insert(meta, DuplicatePolicy.REJECT)
    assert deployment_table.rows[("dep1",)]["label"] == "Old label"
