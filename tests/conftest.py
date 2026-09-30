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


# Tests always run under their own prefix, never the DJ_SCHEMA_PREFIX of the
# environment (e.g. ``dev_`` exported from .env). Override with TEST_SCHEMA_PREFIX.
TEST_SCHEMA_PREFIX = os.environ.get("TEST_SCHEMA_PREFIX") or f"test_{uuid.uuid4().hex[:8]}_"
if not TEST_SCHEMA_PREFIX.startswith("test_"):
    raise pytest.UsageError(
        f"TEST_SCHEMA_PREFIX {TEST_SCHEMA_PREFIX!r} must start with 'test_' "
        "so tests never write into a dev or production schema"
    )
os.environ["DJ_SCHEMA_PREFIX"] = TEST_SCHEMA_PREFIX


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
