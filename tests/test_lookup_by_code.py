"""Unit tests for subject_key / session_key (no MySQL)."""

from unittest.mock import patch

import pytest
from base_schemas.ingestion.scene import session as session_reg
from base_schemas.ingestion.scene import subject as subject_reg

LAB = {"lab_id": "mlai"}


def test_subject_key_looks_up_normalized_code():
    with patch.object(subject_reg, "lookup_key", return_value={"subject_id": "a" * 32}) as lookup:
        assert subject_reg.subject_key(" Tick ", lab=LAB) == {"subject_id": "a" * 32}
    lookup.assert_called_once_with(subject_reg.Subject, {**LAB, "subject_code": "Tick"})


def test_subject_key_unknown_code_raises():
    with patch.object(subject_reg, "lookup_key", return_value=None):
        with pytest.raises(ValueError, match="no subject 'Tick'"):
            subject_reg.subject_key("Tick", lab=LAB)


def test_session_key_looks_up_normalized_code():
    with patch.object(session_reg, "lookup_key", return_value={"session_id": "b" * 32}) as lookup:
        assert session_reg.session_key(" s1 ", lab=LAB) == {"session_id": "b" * 32}
    lookup.assert_called_once_with(session_reg.Session, {**LAB, "session_code": "s1"})


def test_session_key_unknown_code_raises():
    with patch.object(session_reg, "lookup_key", return_value=None):
        with pytest.raises(ValueError, match="no session 's1'"):
            session_reg.session_key("s1", lab=LAB)


@pytest.mark.parametrize(
    ("module", "helper", "table"),
    [(subject_reg, "subject_key", "Subject"), (session_reg, "session_key", "Session")],
)
def test_lookup_defaults_to_settings_lab(monkeypatch, module, helper, table):
    monkeypatch.setenv("SCENE_LAB_ID", "mlai")
    with patch.object(module, "lookup_key", return_value={"id": 1}) as lookup:
        getattr(module, helper)("Tick")
    assert lookup.call_args.args[0] is getattr(module, table)
    assert lookup.call_args.args[1]["lab_id"] == "mlai"


@pytest.mark.parametrize("helper", [subject_reg.subject_key, session_reg.session_key])
def test_lookup_without_lab_or_setting_raises(monkeypatch, helper):
    monkeypatch.delenv("SCENE_LAB_ID", raising=False)
    with pytest.raises(ValueError, match="SCENE_LAB_ID"):
        helper("Tick")
