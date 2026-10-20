import importlib


def test_import_mice_module(dj_connection):
    module = importlib.import_module("base_schemas.legacy.mice")
    assert module is not None


def test_import_exp_module(dj_connection):
    module = importlib.import_module("base_schemas.legacy.exp")
    assert module is not None


def test_import_mlai_modules_without_db():
    for name in ("base_schemas.schemas.session", "base_schemas.ingestion"):
        assert importlib.import_module(name) is not None
