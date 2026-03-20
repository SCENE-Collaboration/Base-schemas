import os
import sys
import uuid
from importlib import import_module, reload
from pathlib import Path

import datajoint as dj
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TEST_SCHEMA_PREFIX = os.environ.setdefault(
    "DJ_SCHEMA_PREFIX",
    f"test_{uuid.uuid4().hex[:8]}_",
)


@pytest.fixture(scope="session")
def dj_connection():
    """Configure and return DataJoint connection for the test session."""
    dj.config["database.host"] = os.environ["DJ_HOST"]
    dj.config["database.port"] = int(os.environ.get("DJ_PORT", "3306"))
    dj.config["database.user"] = os.environ["DJ_USER"]
    dj.config["database.password"] = os.environ["DJ_PASS"]
    dj.config["database.use_tls"] = os.environ.get("DJ_USE_TLS", "false").lower() == "true"
    backend = os.environ.get("DJ_BACKEND")
    if backend:
        dj.config["database.backend"] = backend

    # Verify connection works
    connection = dj.conn()

    yield connection


@pytest.fixture
def base_schema_context(dj_connection):
    """Import test-prefixed schemas and drop them after each test."""
    mice_module = import_module("base_schemas.schemas.mice")
    mice_module = reload(mice_module)

    exp_module = import_module("base_schemas.schemas.exp")
    exp_module = reload(exp_module)

    yield {
        "Mouse": mice_module.Mouse,
        "Session": exp_module.Session,
        "SessionScoreSheet": exp_module.SessionScoreSheet,
        "MouseScoreSheet": mice_module.MouseScoreSheet,
        "MouseScoreSheet_WaterRestriction": mice_module.MouseScoreSheet_WaterRestriction,
        "schema_mouse": mice_module.schema,
        "schema_exp": exp_module.schema,
    }

    exp_module.schema.drop(prompt=False)
    mice_module.schema.drop(prompt=False)
