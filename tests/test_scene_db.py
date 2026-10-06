"""Live-DB smoke tests for scene Lab / Session placeholders."""

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
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.session import Session

    lab_key = {"lab_id": "testlab"}
    Lab.insert1(
        {**lab_key, "lab_name": "Test Lab", "institution": "Test U"},
        skip_duplicates=True,
    )
    session_id = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    Session.insert1(
        {
            **lab_key,
            "session_id": session_id,
            "session_code": "test-session",
            "session_date": dt.date(2026, 1, 15),
        },
        skip_duplicates=True,
    )

    assert (Lab & lab_key).fetch1("lab_name") == "Test Lab"
    assert (
        Session
        & {
            **lab_key,
            "session_id": session_id,
        }
    ).fetch1("session_date") == dt.date(2026, 1, 15)


def test_subject_project_and_multi_subject_session(dj_connection):
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.project import Project
    from base_schemas.schemas.scene.session import Experimenter, Session
    from base_schemas.schemas.scene.subject import Subject, SubjectKind

    lab_key = {"lab_id": "spine"}
    Lab.insert1(
        {**lab_key, "lab_name": "Spine Lab", "institution": "Test U"},
        skip_duplicates=True,
    )
    assert len(SubjectKind()) >= 1

    for sid, name in (("1" * 32, "spine-1"), ("2" * 32, "spine-2")):
        Subject.insert1(
            {"subject_id": sid, **lab_key, "subject_code": name, "subject_kind": "mouse"},
            skip_duplicates=True,
        )
    Project.insert1(
        {"project_name": "gaze_v1", "project_title": "Gaze tracking"},
        skip_duplicates=True,
    )
    Experimenter.insert1({**lab_key, "experimenter_code": "jdoe"}, skip_duplicates=True)

    session_key = {**lab_key, "session_id": "f0e1d2c3b4a5968778695a4b3c2d1e0f"}
    subject_ids = [
        "11111111111111111111111111111111",
        "22222222222222222222222222222222",
    ]
    session = {
        **session_key,
        "session_code": "multi-subject-run",
        "session_date": dt.date(2026, 6, 1),
        "project_name": "gaze_v1",
        "experimenter_code": "jdoe",
    }
    with Session.connection.transaction:
        Session.insert1(session, skip_duplicates=True)
        Session.Subject.insert(
            [{**session_key, "subject_id": sid} for sid in subject_ids],
            skip_duplicates=True,
        )

    row = (Session & session_key).fetch1()
    assert row["project_name"] == "gaze_v1"
    assert row["experimenter_code"] == "jdoe"
    assert set((Session.Subject & session_key).fetch("subject_id")) == set(subject_ids)


def test_session_links_only_an_experimenter_of_its_own_lab(dj_connection):
    import datajoint as dj
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.session import Experimenter, Session

    own, other = {"lab_id": "exp_lab_16_chars"}, {"lab_id": "exp_other"}
    Lab.insert([own, other], skip_duplicates=True)
    Experimenter.insert1({**other, "experimenter_code": "bob"}, skip_duplicates=True)

    session = {**own, "session_id": "e" * 32, "session_code": "exp-1", "session_date": "2026-01-01"}
    with pytest.raises(dj.errors.IntegrityError):
        Session.insert1({**session, "experimenter_code": "bob"})

    Session.insert1(session)  # the link is optional
    assert (Session & own).fetch1("experimenter_code") is None


def test_register_session_mints_id_and_stores_name(dj_connection, monkeypatch):
    from base_schemas.core.hash import content_hash
    from base_schemas.ingestion import SCENE_WRITER_VERSION, register_session
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.ingestion.scene.session import session_meta_payload
    from base_schemas.schemas.provenance.row_meta import SessionRowMeta
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.project import Project
    from base_schemas.schemas.scene.session import Experimenter, Session
    from base_schemas.schemas.scene.subject import Subject

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")

    lab_key = {"lab_id": "reglab"}
    Lab.insert1(
        {**lab_key, "lab_name": "Register Lab", "institution": "Test U"},
        skip_duplicates=True,
    )
    subject_id = "33333333333333333333333333333333"
    Subject.insert1(
        {"subject_id": subject_id, **lab_key, "subject_code": "reg-1", "subject_kind": "mouse"},
        skip_duplicates=True,
    )
    Project.insert1(
        {"project_name": "reg_project", "project_title": "Register project"},
        skip_duplicates=True,
    )
    Experimenter.insert1({**lab_key, "experimenter_code": "reg_user"}, skip_duplicates=True)

    session_date = dt.date(2026, 5, 1)
    key = register_session(
        "morning-run",
        session_date,
        lab=lab_key,
        subjects=[{"subject_id": subject_id}],
        project={"project_name": "reg_project"},
        experimenter={**lab_key, "experimenter_code": "reg_user"},
    )
    assert key["lab_id"] == "reglab"
    assert len(key["session_id"]) == 32
    row = (Session & key).fetch1()
    assert row["session_code"] == "morning-run"
    assert row["session_date"] == session_date
    assert row["project_name"] == "reg_project"
    assert row["experimenter_code"] == "reg_user"
    assert list((Session.Subject & key).fetch("subject_id")) == [subject_id]
    meta = (SessionRowMeta & key).fetch1()
    assert meta["ingestion_version"] == SCENE_WRITER_VERSION
    assert meta["content_hash"] == content_hash(session_meta_payload(row, [subject_id]))
    assert meta["deployment_id"] == os.environ["SCENE_DEPLOYMENT_ID"]

    # Same name + same content: VERIFY (default) returns the stored session.
    again = register_session(
        "morning-run",
        session_date,
        lab=lab_key,
        subjects=[{"subject_id": subject_id}],
        project={"project_name": "reg_project"},
        experimenter={**lab_key, "experimenter_code": "reg_user"},
    )
    assert again == key
    assert len(Session & {**lab_key, "session_code": "morning-run"}) == 1
    with pytest.raises(ValueError, match="different content hash"):
        register_session("morning-run", dt.date(2026, 5, 2), lab=lab_key)

    # OVERWRITE keeps the id, rewrites the row and stamp, and replaces the subject links.
    with pytest.warns(UserWarning, match="content hash changed"):
        updated = register_session(
            "morning-run",
            dt.date(2026, 5, 2),
            lab=lab_key,
            if_exists=DuplicatePolicy.OVERWRITE,
        )
    assert updated == key
    assert (Session & key).fetch1("session_date") == dt.date(2026, 5, 2)
    assert len(Session.Subject & key) == 0
    assert (SessionRowMeta & key).fetch1("content_hash") == content_hash(
        session_meta_payload((Session & key).fetch1(), [])
    )


def test_ensure_lab_duplicate_policy_roundtrip(dj_connection, monkeypatch):
    from base_schemas.core.hash import content_hash
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.ingestion.scene.admin import ensure_lab
    from base_schemas.ingestion.scene.admin.lab import lab_meta_payload
    from base_schemas.schemas.provenance.row_meta import LabRowMeta
    from base_schemas.schemas.scene.lab import Lab

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "policy-dep")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "policy")
    lab_key = {"lab_id": "pol_lab"}
    (LabRowMeta & lab_key).delete_quick()
    (Lab & lab_key).delete_quick()
    lab = {**lab_key, "lab_name": "Policy Lab", "institution": "Test U"}

    # First write inserts row + stamp (and the Deployment row it references).
    assert ensure_lab(lab) == lab_key
    assert (Lab & lab_key).fetch1("lab_name") == "Policy Lab"
    assert (LabRowMeta & lab_key).fetch1("content_hash") == content_hash(lab_meta_payload(lab))
    assert (LabRowMeta & lab_key).fetch1("deployment_id") == "policy-dep"

    with pytest.raises(ValueError, match="already registered"):
        ensure_lab(lab)
    assert ensure_lab(lab, if_exists=DuplicatePolicy.VERIFY) == lab_key

    renamed = {**lab, "lab_name": "Renamed Lab"}
    with pytest.raises(ValueError, match="different content hash"):
        ensure_lab(renamed, if_exists=DuplicatePolicy.VERIFY)
    assert ensure_lab(renamed, if_exists=DuplicatePolicy.SKIP) == lab_key
    assert (Lab & lab_key).fetch1("lab_name") == "Policy Lab"

    # OVERWRITE must go through update1: REPLACE INTO would trip the LabRowMeta -> Lab FK.
    with pytest.warns(UserWarning, match="content hash changed"):
        ensure_lab(renamed, if_exists=DuplicatePolicy.OVERWRITE)
    assert (Lab & lab_key).fetch1("lab_name") == "Renamed Lab"
    assert (LabRowMeta & lab_key).fetch1("content_hash") == content_hash(lab_meta_payload(renamed))
    assert len(LabRowMeta & lab_key) == 1


def test_register_subjects_and_session_in_one_transaction(dj_connection, monkeypatch):
    from base_schemas.core.db import atomic
    from base_schemas.ingestion import register_session, register_subject
    from base_schemas.schemas.provenance.row_meta import SessionRowMeta, SubjectRowMeta
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.session import Session
    from base_schemas.schemas.scene.subject import Subject

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    lab_key = {"lab_id": "txnlab"}
    Lab.insert1({**lab_key, "lab_name": "Txn Lab", "institution": "Test U"}, skip_duplicates=True)

    def register_all(session_code: str):
        with atomic(Session.connection):
            subjects = [register_subject(code, "mouse", lab=lab_key) for code in ("txn-1", "txn-2")]
            return register_session(
                session_code, dt.date(2026, 8, 1), lab=lab_key, subjects=subjects
            )

    key = register_all("nested-txn")

    subject_ids = set((Subject & lab_key).fetch("subject_id"))
    assert len(subject_ids) == 2
    assert set((Session.Subject & key).fetch("subject_id")) == subject_ids
    assert len(SessionRowMeta & key) == 1
    for sid in subject_ids:
        assert len(SubjectRowMeta & {"subject_id": sid}) == 1
    assert not Session.connection.in_transaction

    # Re-running the same registration reuses every minted id.
    assert register_all("nested-txn") == key
    assert len(Subject & lab_key) == 2

    # A failure inside the block rolls back the subjects registered before it.
    with pytest.raises(ValueError, match="session_code"), atomic(Session.connection):
        register_subject("txn-3", "mouse", lab=lab_key)
        register_session("not a code", dt.date(2026, 8, 1), lab=lab_key)
    assert not (Subject & {**lab_key, "subject_code": "txn-3"})


def test_overwrite_keeps_subject_links_that_a_lab_table_references(dj_connection, monkeypatch):
    """OVERWRITE rewrites only the subject links that differ (FKs are ON DELETE RESTRICT)."""
    import datajoint as dj
    from base_schemas.core.config import load_settings
    from base_schemas.ingestion import register_session, register_subject
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.session import Session

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    lab_key = {"lab_id": "reflab"}
    Lab.insert1({**lab_key, "lab_name": "Ref Lab"}, skip_duplicates=True)

    lab_schema = dj.Schema(load_settings().db_name("reflab"), connection=dj_connection)

    @lab_schema
    class SubjectNote(dj.Manual):
        """Stands in for a lab table that hangs data off a session's subject."""

        definition = """
        -> Session.Subject
        ---
        note: varchar(64)
        """

    noted, other = (register_subject(code, "mouse", lab=lab_key) for code in ("ref-1", "ref-2"))
    key = register_session("ref-run", dt.date(2026, 9, 1), lab=lab_key, subjects=[noted, other])
    SubjectNote.insert1({**key, **noted, "note": "kept"})

    def overwrite(session_date, subjects):
        with pytest.warns(UserWarning, match="content hash changed"):
            return register_session(
                "ref-run",
                session_date,
                lab=lab_key,
                subjects=subjects,
                if_exists=DuplicatePolicy.OVERWRITE,
            )

    def linked():
        return {row["subject_id"] for row in (Session.Subject & key).keys()}

    # Same subjects, other date: the referenced link is left in place.
    assert overwrite(dt.date(2026, 9, 2), [other, noted]) == key
    assert (Session & key).fetch1("session_date") == dt.date(2026, 9, 2)
    assert linked() == {noted["subject_id"], other["subject_id"]}
    assert (SubjectNote & key).fetch1("note") == "kept"

    # An unreferenced link can be removed.
    overwrite(dt.date(2026, 9, 2), [noted])
    assert linked() == {noted["subject_id"]}

    # Removing the referenced link is refused, and the whole overwrite rolls back.
    with pytest.raises(dj.errors.IntegrityError):
        register_session(
            "ref-run",
            dt.date(2026, 9, 3),
            lab=lab_key,
            subjects=[other],
            if_exists=DuplicatePolicy.OVERWRITE,
        )
    assert linked() == {noted["subject_id"]}
    assert (Session & key).fetch1("session_date") == dt.date(2026, 9, 2)


def test_ensure_schema_version_idempotent_then_assert(dj_connection):
    from base_schemas.core.versioning import assert_schema_compatible, ensure_schema_version
    from base_schemas.schemas.scene._schema import (
        SCENE_SCHEMA_VERSION,
        SchemaVersion,
    )

    _clear_schema_version_test_rows(SchemaVersion)
    # Creating the table recorded the code's version (SchemaVersionTable.declare).
    stored = SchemaVersion & {"version": SCENE_SCHEMA_VERSION}
    assert stored.fetch1("notes") == "recorded on creation"
    assert (
        ensure_schema_version(SCENE_SCHEMA_VERSION, SchemaVersion, notes="test-init")
        == SCENE_SCHEMA_VERSION
    )
    # Second call must not insert again or raise when already compatible.
    assert ensure_schema_version(SCENE_SCHEMA_VERSION, SchemaVersion) == (SCENE_SCHEMA_VERSION)
    assert assert_schema_compatible(SCENE_SCHEMA_VERSION, SchemaVersion) == (SCENE_SCHEMA_VERSION)


def test_assert_schema_compatible_mismatch_against_live_db(dj_connection, monkeypatch):
    from base_schemas.core import versioning
    from base_schemas.core.versioning import (
        SchemaVersionError,
        assert_schema_compatible,
        ensure_schema_version,
    )
    from base_schemas.ingestion.scene.admin import ensure_lab
    from base_schemas.schemas.scene._schema import (
        SCENE_SCHEMA_VERSION,
        SchemaVersion,
    )
    from base_schemas.schemas.scene.lab import Lab

    _clear_schema_version_test_rows(SchemaVersion)
    ensure_schema_version(SCENE_SCHEMA_VERSION, SchemaVersion, notes="test-init")
    try:
        # Newer applied_at wins as "current" DB version → deliberate mismatch.
        # applied_at has 1 s resolution: insert strictly later than the stored row.
        stored_at = (SchemaVersion & {"version": SCENE_SCHEMA_VERSION}).fetch1("applied_at")
        SchemaVersion.insert1(
            {
                "version": _TEST_MISMATCH_VERSION,
                "applied_at": stored_at + dt.timedelta(seconds=1),
                "notes": "force mismatch for test",
            },
            skip_duplicates=True,
        )
        with pytest.raises(SchemaVersionError, match="mismatch"):
            assert_schema_compatible(SCENE_SCHEMA_VERSION, SchemaVersion)

        # The write path refuses to write into a database with another version
        # (the per-process check cache is reset so this test does not depend on order).
        monkeypatch.setattr(versioning, "_COMPATIBLE_DATABASES", set())
        monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
        with pytest.raises(SchemaVersionError, match="mismatch"):
            ensure_lab({"lab_id": "verlab", "lab_name": "Version Lab"})
        assert not (Lab & {"lab_id": "verlab"})
    finally:
        _clear_schema_version_test_rows(SchemaVersion)
