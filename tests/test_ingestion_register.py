"""Unit tests for register_session (no MySQL)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from base_schemas.ingestion.register import session as session_reg


def test_new_session_id_is_uuid4_hex():
    sid = session_reg.new_session_id()
    assert len(sid) == 32
    assert sid != session_reg.new_session_id()
    int(sid, 16)  # valid hex


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
    ) as sess_ins, patch.object(session_reg, "new_session_id", return_value="abc" * 10 + "ab"):
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
