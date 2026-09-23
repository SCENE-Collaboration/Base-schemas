"""Live-DB smoke tests for experiment Lab / Session placeholders."""

import datetime as dt
import os

import pytest

_TRUTHY = frozenset({"1", "true", "yes", "on"})

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.getenv("DJ_HOST"),
        reason="requires DataJoint DB (set DJ_HOST)",
    ),
    pytest.mark.skipif(
        (os.getenv("AUTO_ACTIVATE") or "").strip().lower() not in _TRUTHY,
        reason="tables are unbound unless AUTO_ACTIVATE is set",
    ),
]


def test_lab_session_insert_roundtrip(dj_connection):
    from base_schemas.schemas.experiment.lab import Lab
    from base_schemas.schemas.experiment.session import Session

    lab_key = {"lab_id": "testlab"}
    Lab.insert1(
        {**lab_key, "lab_name": "Test Lab", "institution": "Test U"},
        skip_duplicates=True,
    )
    Session.insert1(
        {
            **lab_key,
            "session_id": "s1",
            "session_date": dt.date(2026, 1, 15),
        },
        skip_duplicates=True,
    )

    assert (Lab & lab_key).fetch1("lab_name") == "Test Lab"
    assert (Session & {**lab_key, "session_id": "s1"}).fetch1("session_date") == dt.date(
        2026, 1, 15
    )
