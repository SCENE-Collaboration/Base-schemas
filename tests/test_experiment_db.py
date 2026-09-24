"""Live-DB smoke tests for experiment Lab / Session placeholders."""

import datetime as dt
import os

import pytest

_TRUTHY = frozenset({"1", "true", "yes", "on"})
# Deliberate mismatch row inserted by version tests; must not linger across runs.
_TEST_MISMATCH_VERSION = "0.0.0-test-mismatch"

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
    pytest.mark.skipif(
        (os.getenv("AUTO_ACTIVATE") or "").strip().lower() not in _TRUTHY,
        reason="tables are unbound unless AUTO_ACTIVATE is set",
    ),
]


def _clear_schema_version_test_rows(SchemaVersion):
    """Remove leftover mismatch rows (e.g. after a previous interrupted test)."""
    (SchemaVersion & {"version": _TEST_MISMATCH_VERSION}).delete(prompt=False)


def test_lab_session_insert_roundtrip(dj_connection):
    from base_schemas.schemas.experiment.lab import Lab
    from base_schemas.schemas.experiment.session import Session

    lab_key = {"lab_id": "testlab"}
    Lab.insert1(
        {**lab_key, "lab_name": "Test Lab", "institution": "Test U"},
        skip_duplicates=True,
    )
    Session.insert1(
        {
            **lab_key,
            "session_id": "s1",
            "session_name": "test session",
            "session_date": dt.date(2026, 1, 15),
        },
        skip_duplicates=True,
    )

    assert (Lab & lab_key).fetch1("lab_name") == "Test Lab"
    assert (Session & {**lab_key, "session_id": "s1"}).fetch1("session_date") == dt.date(
        2026, 1, 15
    )


def test_register_session_mints_id_and_stores_name(dj_connection):
    from base_schemas.ingestion import register_session
    from base_schemas.schemas.experiment.lab import Lab
    from base_schemas.schemas.experiment.session import Session

    session_date = dt.date(2026, 5, 1)
    key = register_session(
        "Morning run",
        session_date,
        lab={"lab_id": "reglab", "lab_name": "Register Lab", "institution": "Test U"},
    )
    assert key["lab_id"] == "reglab"
    assert len(key["session_id"]) == 32
    assert (Lab & {"lab_id": "reglab"}).fetch1("lab_name") == "Register Lab"
    row = (Session & key).fetch1()
    assert row["session_name"] == "Morning run"
    assert row["session_date"] == session_date


def test_ensure_schema_version_idempotent_then_assert(dj_connection):
    from base_schemas.core.versioning import assert_schema_compatible, ensure_schema_version
    from base_schemas.schemas.experiment._schema import (
        EXPERIMENT_SCHEMA_VERSION,
        SchemaVersion,
    )

    _clear_schema_version_test_rows(SchemaVersion)
    assert (
        ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, SchemaVersion, notes="test-init")
        == EXPERIMENT_SCHEMA_VERSION
    )
    # Second call must not insert again or raise when already compatible.
    assert ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, SchemaVersion) == (
        EXPERIMENT_SCHEMA_VERSION
    )
    assert assert_schema_compatible(EXPERIMENT_SCHEMA_VERSION, SchemaVersion) == (
        EXPERIMENT_SCHEMA_VERSION
    )


def test_assert_schema_compatible_mismatch_against_live_db(dj_connection):
    from datetime import datetime, timezone

    from base_schemas.core.versioning import (
        SchemaVersionError,
        assert_schema_compatible,
        ensure_schema_version,
    )
    from base_schemas.schemas.experiment._schema import (
        EXPERIMENT_SCHEMA_VERSION,
        SchemaVersion,
    )

    _clear_schema_version_test_rows(SchemaVersion)
    ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, SchemaVersion, notes="test-init")
    try:
        # Newer applied_at wins as "current" DB version → deliberate mismatch.
        SchemaVersion.insert1(
            {
                "version": _TEST_MISMATCH_VERSION,
                "applied_at": datetime.now(timezone.utc).replace(tzinfo=None),
                "notes": "force mismatch for test",
            },
            skip_duplicates=True,
        )
        with pytest.raises(SchemaVersionError, match="mismatch"):
            assert_schema_compatible(EXPERIMENT_SCHEMA_VERSION, SchemaVersion)
    finally:
        _clear_schema_version_test_rows(SchemaVersion)
