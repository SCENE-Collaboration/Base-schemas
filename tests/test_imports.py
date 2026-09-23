import importlib


def test_import_lab_module(dj_connection):
    module = importlib.import_module("base_schemas.schemas.experiment.lab")
    assert module is not None


def test_import_session_module(dj_connection):
    module = importlib.import_module("base_schemas.schemas.experiment.session")
    assert module is not None
