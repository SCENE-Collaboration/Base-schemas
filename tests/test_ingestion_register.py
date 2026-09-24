"""Unit tests for register_session / SessionRowMeta writers (no MySQL)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from base_schemas.core.hash import content_hash
from base_schemas.ingestion.register import session as session_reg
from base_schemas.ingestion.register import session_meta as meta_reg


def test_new_session_id_is_uuid4_hex():
    sid = session_reg.new_session_id()
    assert len(sid) == 32
    assert sid != session_reg.new_session_id()
    int(sid, 16)  # valid hex


def test_session_etag_payload_is_name_and_date_only():
    session = {
        "lab_id": "mlai",
        "session_id": "deadbeef" * 4,
        "session_name": "morning run",
        "session_date": date(2026, 5, 1),
    }
    payload = meta_reg.session_etag_payload(session)
    assert payload == {
        "session_date": "2026-05-01",
        "session_name": "morning run",
    }
    assert content_hash(payload) != content_hash({**payload, "session_name": "evening run"})


def test_upsert_session_row_meta_writes_version_hash_and_timestamp():
    key = {"lab_id": "mlai", "session_id": "abc" * 10 + "ab"}
    session = {
        **key,
        "session_name": "morning run",
        "session_date": date(2026, 5, 1),
    }
    with patch.object(meta_reg.SessionRowMeta, "insert1") as ins:
        meta_reg.upsert_session_row_meta(key, session)

    row = ins.call_args.args[0]
    assert row["lab_id"] == "mlai"
    assert row["session_id"] == key["session_id"]
    assert row["ingestion_version"] == meta_reg.EXPERIMENT_WRITER_VERSION
    assert row["content_hash"] == content_hash(meta_reg.session_etag_payload(session))
    assert "updated_at" in row
    assert ins.call_args.kwargs["replace"] is True


def test_upsert_session_row_meta_honors_writer_version_override():
    key = {"lab_id": "mlai", "session_id": "x" * 32}
    session = {**key, "session_name": "s", "session_date": date(2026, 1, 1)}
    with patch.object(meta_reg.SessionRowMeta, "insert1") as ins:
        meta_reg.upsert_session_row_meta(key, session, writer_version="9.9.9")
    assert ins.call_args.args[0]["ingestion_version"] == "9.9.9"


def test_register_session_rejects_empty_name():
    with pytest.raises(ValueError, match="session_name"):
        session_reg.register_session(
            "  ",
            date(2026, 1, 1),
            lab={"lab_id": "mlai"},
        )


def test_register_session_inserts_lab_and_session_with_minted_id():
    lab = {"lab_id": "mlai", "lab_name": "Mathis Lab"}
    lab_table = MagicMock()
    lab_table.primary_key = ["lab_id"]
    with patch.object(session_reg, "Lab", lab_table), patch.object(
        session_reg.Session, "insert1"
    ) as sess_ins, patch.object(
        session_reg, "new_session_id", return_value="abc" * 10 + "ab"
    ), patch.object(session_reg, "upsert_session_row_meta") as upsert_meta:
        key = session_reg.register_session(
            " morning run ",
            date(2026, 5, 1),
            lab=lab,
        )

    assert key == {"lab_id": "mlai", "session_id": "abc" * 10 + "ab"}
    lab_table.insert1.assert_called_once_with(lab, skip_duplicates=True)
    row = sess_ins.call_args.args[0]
    assert row["lab_id"] == "mlai"
    assert row["session_name"] == "morning run"
    assert row["session_date"] == date(2026, 5, 1)
    assert row["session_id"] == key["session_id"]
    upsert_meta.assert_called_once_with(key, row)
