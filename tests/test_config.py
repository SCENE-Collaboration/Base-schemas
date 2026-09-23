"""Unit tests for core config (no database)."""

import pytest
from base_schemas.core import load_settings


def test_load_settings_default(monkeypatch):
    monkeypatch.delenv("DJ_SCHEMA_PREFIX", raising=False)
    monkeypatch.delenv("USE_LAZY_SCHEMA", raising=False)
    settings = load_settings()
    assert settings.prefix == ""
    assert settings.lazy is False


def test_load_settings_prefix_and_lazy(monkeypatch):
    monkeypatch.setenv("DJ_SCHEMA_PREFIX", "dev_")
    monkeypatch.setenv("USE_LAZY_SCHEMA", "true")
    settings = load_settings()
    assert settings.prefix == "dev_"
    assert settings.lazy is True
    assert settings.db_name("experiment") == "dev_experiment"


def test_schema_prefix_rejects_invalid(monkeypatch):
    monkeypatch.setenv("DJ_SCHEMA_PREFIX", "bad-prefix!")
    with pytest.raises(ValueError, match="Invalid DJ_SCHEMA_PREFIX"):
        load_settings()


def test_db_name_rejects_empty_suffix(monkeypatch):
    monkeypatch.delenv("DJ_SCHEMA_PREFIX", raising=False)
    with pytest.raises(ValueError, match="non-empty"):
        load_settings().db_name("")
