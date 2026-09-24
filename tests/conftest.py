"""Shared pytest fixtures for base_schemas unit tests."""

import os
import sys
import uuid
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

    connection = dj.conn()
    yield connection
