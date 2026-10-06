"""Live-DB smoke tests for the shared mouse tables."""

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


def test_mouse_extends_subject_roundtrip(dj_connection):
    from base_schemas.schemas.mouse.mouse import Mouse, Strain
    from base_schemas.schemas.scene.lab import Lab
    from base_schemas.schemas.scene.subject import Subject

    lab_key = {"lab_id": "mouselab"}
    Lab.insert1({**lab_key, "lab_name": "Mouse Lab"}, skip_duplicates=True)
    Strain.insert1({"strain_name": "C57BL/6J", "stock_number": "000664"}, skip_duplicates=True)

    full, minimal = {"subject_id": "a" * 32}, {"subject_id": "b" * 32}
    Subject.insert(
        [
            {**full, **lab_key, "subject_code": "mouse-1", "subject_kind": "mouse"},
            {**minimal, **lab_key, "subject_code": "mouse-2", "subject_kind": "mouse"},
        ],
        skip_duplicates=True,
    )
    Mouse.insert1(
        {**full, "sex": "F", "date_of_birth": dt.date(2026, 1, 15), "strain_name": "C57BL/6J"},
        skip_duplicates=True,
    )
    Mouse.insert1({**minimal, "sex": "U"}, skip_duplicates=True)  # only sex is required

    assert Mouse.primary_key == Subject.primary_key
    row = (Subject * Mouse * Strain & full).fetch1()
    assert row["subject_code"] == "mouse-1"
    assert row["stock_number"] == "000664"
    assert (Mouse & minimal).fetch1("date_of_birth", "strain_name") == (None, None)


def test_mouse_requires_an_existing_subject(dj_connection):
    import datajoint as dj
    from base_schemas.schemas.mouse.mouse import Mouse

    with pytest.raises(dj.errors.IntegrityError):
        Mouse.insert1({"subject_id": "c" * 32, "sex": "M"})
