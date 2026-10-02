"""Live-DB tests for the row stamps' content_hash."""

import datetime as dt
import os

import pytest

_TRUTHY = frozenset({"1", "true", "yes", "on"})

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


def test_overwrite_resets_omitted_nullable_field_and_stamp_matches(dj_connection):
    """OVERWRITE stores the row as an insert would, so the stamp matches the stored row."""
    from base_schemas.core.hash import content_hash
    from base_schemas.ingestion.provenance import DuplicatePolicy, insert_tracked_row
    from base_schemas.ingestion.register.session import session_meta_payload
    from base_schemas.schemas.provenance.row_meta import SessionRowMeta
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.session import Session
    from base_schemas.schemas.scene.task import Task

    deployment = {"deployment_id": "test-local", "label": "test"}
    Lab.insert1({"lab_id": "nul_lab"}, skip_duplicates=True)
    Task.insert1({"task_name": "nul_task"}, skip_duplicates=True)
    key = {"lab_id": "nul_lab", "session_id": "n" * 32}
    session = {**key, "session_code": "nul-1", "session_date": dt.date(2026, 1, 1)}

    with_task = {**session, "task_name": "nul_task"}
    insert_tracked_row(
        SessionRowMeta,
        with_task,
        payload=session_meta_payload(with_task),
        deployment=deployment,
        if_exists=DuplicatePolicy.REJECT,
    )
    with pytest.warns(UserWarning, match="content hash changed"):
        insert_tracked_row(
            SessionRowMeta,
            session,  # task_name omitted
            payload=session_meta_payload(session),
            deployment=deployment,
            if_exists=DuplicatePolicy.OVERWRITE,
        )

    stored = (Session & key).fetch1()
    assert stored["task_name"] is None
    assert (SessionRowMeta & key).fetch1("content_hash") == content_hash(
        session_meta_payload(stored)
    )


# --- Known hashing issues (FIXME). The stamp's content_hash is computed from the
# insert dict, not from the row as stored.


_PRE_COERCION = (
    "FIXME: VERIFY hashes the insert dict before database coercion, so a value the "
    "database stores identically still counts as different content"
)


@pytest.mark.xfail(strict=True, raises=ValueError, reason=_PRE_COERCION)
def test_verify_accepts_datetime_for_stored_date(dj_connection, monkeypatch):
    from base_schemas.ingestion import register_session
    from base_schemas.schemas.scene.lab import Lab

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    Lab.insert1({"lab_id": "coe_lab"}, skip_duplicates=True)

    key = register_session("coerce-1", dt.date(2026, 5, 1), lab={"lab_id": "coe_lab"})
    assert register_session("coerce-1", dt.datetime(2026, 5, 1), lab={"lab_id": "coe_lab"}) == key


@pytest.mark.xfail(strict=True, raises=ValueError, reason=_PRE_COERCION)
def test_verify_accepts_int_for_stored_varchar(dj_connection, monkeypatch):
    from base_schemas.ingestion.admin import ensure_lab
    from base_schemas.ingestion.provenance import DuplicatePolicy

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")

    ensure_lab({"lab_id": "int_lab", "lab_name": "8"})
    ensure_lab({"lab_id": "int_lab", "lab_name": 8}, if_exists=DuplicatePolicy.VERIFY)
