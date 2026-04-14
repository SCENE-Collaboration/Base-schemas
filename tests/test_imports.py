import importlib


def test_import_mice_module(dj_connection):
    module = importlib.import_module("base_schemas.schemas.mice")
    assert module is not None


def test_import_exp_module(dj_connection):
    module = importlib.import_module("base_schemas.schemas.exp")
    assert module is not None
