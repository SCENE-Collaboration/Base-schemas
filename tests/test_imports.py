"""Import smoke tests (need DB config via dj_connection)."""

import importlib
import os

import pytest

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
]


def test_import_lab_module(dj_connection):
    module = importlib.import_module("base_schemas.schemas.experiment.lab")
    assert module is not None


def test_import_session_module(dj_connection):
    module = importlib.import_module("base_schemas.schemas.experiment.session")
    assert module is not None
