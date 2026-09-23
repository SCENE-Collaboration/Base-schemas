"""Live-DB smoke tests for experiment Lab / Session placeholders."""

import datetime as dt
import os

import pytest

pytestmark = pytest.mark.skipif(
    bool(os.getenv("USE_LAZY_SCHEMA")),
    reason="tables are unbound when USE_LAZY_SCHEMA is set",
)


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
