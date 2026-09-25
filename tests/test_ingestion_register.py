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


def test_resolve_deployment_requires_env_or_arg(monkeypatch):
    monkeypatch.delenv("SCENE_DEPLOYMENT_ID", raising=False)
    with pytest.raises(ValueError, match="SCENE_DEPLOYMENT_ID"):
        session_reg._resolve_deployment(None)


def test_resolve_deployment_from_settings(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "from-env")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "Env label")
    assert session_reg._resolve_deployment(None) == {
        "deployment_id": "from-env",
        "label": "Env label",
    }


def test_resolve_deployment_prefers_explicit_arg(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "from-env")
    explicit = {"deployment_id": "override", "label": "x"}
    assert session_reg._resolve_deployment(explicit) is explicit


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


def test_upsert_session_row_meta_writes_version_hash_and_deployment():
    key = {"lab_id": "mlai", "session_id": "abc" * 10 + "ab"}
    session = {
        **key,
        "session_name": "morning run",
        "session_date": date(2026, 5, 1),
    }
    deployment_key = {"deployment_id": "dep1"}
    with patch.object(meta_reg.SessionRowMeta, "insert1") as ins:
        meta_reg.upsert_session_row_meta(key, session, deployment_key=deployment_key)

    row = ins.call_args.args[0]
    assert row["lab_id"] == "mlai"
    assert row["session_id"] == key["session_id"]
    assert row["deployment_id"] == "dep1"
    assert row["ingestion_version"] == meta_reg.EXPERIMENT_WRITER_VERSION
    assert row["content_hash"] == content_hash(meta_reg.session_etag_payload(session))
    assert "updated_at" in row
    assert ins.call_args.kwargs["replace"] is True


def test_upsert_session_row_meta_honors_writer_version_override():
    key = {"lab_id": "mlai", "session_id": "x" * 32}
    session = {**key, "session_name": "s", "session_date": date(2026, 1, 1)}
    with patch.object(meta_reg.SessionRowMeta, "insert1") as ins:
        meta_reg.upsert_session_row_meta(
            key,
            session,
            deployment_key={"deployment_id": "dep1"},
            writer_version="9.9.9",
        )
    assert ins.call_args.args[0]["ingestion_version"] == "9.9.9"


def test_register_session_rejects_empty_name(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "local")
    with pytest.raises(ValueError, match="session_name"):
        session_reg.register_session(
            "  ",
            date(2026, 1, 1),
            lab={"lab_id": "mlai"},
        )


def test_register_session_uses_settings_deployment(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "from-env")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "Env")
    lab = {"lab_id": "mlai", "lab_name": "Mathis Lab"}
    lab_table = MagicMock()
    lab_table.primary_key = ["lab_id"]
    dep_table = MagicMock()
    dep_table.primary_key = ["deployment_id"]
    with patch.object(session_reg, "Lab", lab_table), patch.object(
        session_reg, "Deployment", dep_table
    ), patch.object(session_reg.Session, "insert1") as sess_ins, patch.object(
        session_reg, "new_session_id", return_value="abc" * 10 + "ab"
    ), patch.object(session_reg, "upsert_session_row_meta") as upsert_meta:
        key = session_reg.register_session(
            " morning run ",
            date(2026, 5, 1),
            lab=lab,
        )

    assert key == {"lab_id": "mlai", "session_id": "abc" * 10 + "ab"}
    lab_table.insert1.assert_called_once_with(lab, skip_duplicates=True)
    dep_table.insert1.assert_called_once_with(
        {"deployment_id": "from-env", "label": "Env"},
        skip_duplicates=True,
    )
    row = sess_ins.call_args.args[0]
    assert row["session_name"] == "morning run"
    upsert_meta.assert_called_once_with(key, row, deployment_key={"deployment_id": "from-env"})


def test_register_session_explicit_deployment_overrides_settings(monkeypatch):
    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "from-env")
    lab = {"lab_id": "mlai"}
    deployment = {"deployment_id": "override", "label": "x"}
    lab_table = MagicMock()
    lab_table.primary_key = ["lab_id"]
    dep_table = MagicMock()
    dep_table.primary_key = ["deployment_id"]
    with patch.object(session_reg, "Lab", lab_table), patch.object(
        session_reg, "Deployment", dep_table
    ), patch.object(session_reg.Session, "insert1"), patch.object(
        session_reg, "new_session_id", return_value="x" * 32
    ), patch.object(session_reg, "upsert_session_row_meta") as upsert_meta:
        session_reg.register_session(
            "s",
            date(2026, 1, 1),
            lab=lab,
            deployment=deployment,
        )
    dep_table.insert1.assert_called_once_with(deployment, skip_duplicates=True)
    assert upsert_meta.call_args.kwargs["deployment_key"] == {"deployment_id": "override"}
