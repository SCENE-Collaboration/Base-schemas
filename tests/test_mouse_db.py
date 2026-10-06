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


def test_mouse_extends_subject_roundtrip(dj_connection, monkeypatch):
    from base_schemas.ingestion.mouse.mouse import register_mouse
    from base_schemas.ingestion.mouse.strain import ensure_strain
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.ingestion.scene.admin import ensure_lab
    from base_schemas.schemas.mouse.mouse import Mouse, Strain
    from base_schemas.schemas.scene.subject import Subject

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    lab_key = ensure_lab(
        {"lab_id": "mouselab", "lab_name": "Mouse Lab"}, if_exists=DuplicatePolicy.VERIFY
    )
    balb = ensure_strain({"strain_name": "BALB/cJ", "rrid": "RRID:IMSR_JAX:000651"})

    full = register_mouse(
        "mouse-1",
        "F",
        lab=lab_key,
        date_of_birth=dt.date(2026, 1, 15),
        strain=balb,
        genotype="Cux2-CreERT2/wt",
    )
    minimal = register_mouse("mouse-2", "U", lab=lab_key)  # only sex is required

    assert Mouse.primary_key == Subject.primary_key
    row = (Subject * Mouse * Strain & full).fetch1()
    assert row["subject_code"] == "mouse-1"
    assert row["rrid"] == "RRID:IMSR_JAX:000651"
    assert row["genotype"] == "Cux2-CreERT2/wt"
    assert (Mouse & minimal).fetch1("date_of_birth", "strain_name", "genotype") == (None, None, "")


def test_ensure_strain_keeps_one_spelling_and_one_row_per_rrid(dj_connection, monkeypatch):
    from base_schemas.ingestion.mouse.strain import ensure_strain
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.schemas.mouse.mouse import Strain
    from base_schemas.schemas.mouse.row_meta import StrainRowMeta

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")

    # A strain may start without an rrid; OVERWRITE completes it later.
    key = ensure_strain({"strain_name": "DBA/2J"})
    assert key == {"strain_name": "DBA/2J"}
    assert (Strain & key).fetch1("rrid") is None
    assert len(StrainRowMeta & key) == 1
    assert ensure_strain({"strain_name": "DBA/2J"}) == key  # VERIFY is the default
    with pytest.raises(ValueError, match="already registered"):
        ensure_strain({"strain_name": "DBA/2J"}, if_exists=DuplicatePolicy.REJECT)

    dba = {"strain_name": "DBA/2J", "rrid": "RRID:IMSR_JAX:000671"}
    with pytest.raises(ValueError, match="different content hash"):
        ensure_strain(dba)
    with pytest.warns(UserWarning, match="content hash changed"):
        ensure_strain(dba, if_exists=DuplicatePolicy.OVERWRITE)
    assert (Strain & key).fetch1("rrid") == "RRID:IMSR_JAX:000671"
    assert ensure_strain(dba) == key

    # Names match case-insensitively in the database: another spelling is refused.
    with pytest.raises(ValueError, match="already stored as 'DBA/2J'"):
        ensure_strain({"strain_name": "dba/2j"})
    # One rrid, one strain: a second name for the same rrid is refused.
    with pytest.raises(ValueError, match="already registered as strain 'DBA/2J'"):
        ensure_strain({"strain_name": "DBA2", "rrid": "RRID:IMSR_JAX:000671"})
    assert len(Strain & 'strain_name LIKE "DBA%"') == 1

    # Several strains may lack an rrid (the unique index ignores NULL).
    ensure_strain({"strain_name": "in-house-1"})
    ensure_strain({"strain_name": "in-house-2"})

    for bad in ("", " DBA/2J", "DBA/2J "):
        with pytest.raises(ValueError, match="strain_name"):
            ensure_strain({"strain_name": bad})
    for bad in ("000671", "RRID: IMSR_JAX:000671", ""):
        with pytest.raises(ValueError, match="rrid"):
            ensure_strain({"strain_name": "bad-rrid", "rrid": bad})
    assert not (Strain & {"strain_name": "bad-rrid"})


def test_register_mouse_writes_subject_and_mouse_atomically(dj_connection, monkeypatch):
    from base_schemas.ingestion import register_subject
    from base_schemas.ingestion.mouse import MOUSE_WRITER_VERSION
    from base_schemas.ingestion.mouse.mouse import register_mouse
    from base_schemas.ingestion.mouse.strain import ensure_strain
    from base_schemas.ingestion.provenance import DuplicatePolicy
    from base_schemas.ingestion.scene import SCENE_WRITER_VERSION
    from base_schemas.ingestion.scene.admin import ensure_lab
    from base_schemas.schemas.mouse.mouse import Mouse
    from base_schemas.schemas.mouse.row_meta import MouseRowMeta
    from base_schemas.schemas.provenance.row_meta import SubjectRowMeta
    from base_schemas.schemas.scene.subject import Subject

    monkeypatch.setenv("SCENE_DEPLOYMENT_ID", "test-local")
    monkeypatch.setenv("SCENE_DEPLOYMENT_LABEL", "test")
    lab_key = ensure_lab(
        {"lab_id": "regmouse", "lab_name": "Register Mouse Lab"},
        if_exists=DuplicatePolicy.VERIFY,
    )
    c57 = ensure_strain({"strain_name": "C57BL/6J", "rrid": "RRID:IMSR_JAX:000664"})

    born = dt.date(2026, 1, 15)
    mouse = {"lab": lab_key, "date_of_birth": born, "strain": c57, "genotype": "Cux2-CreERT2/wt"}
    key = register_mouse("reg-m1", "F", **mouse)
    assert (Subject & key).fetch1("subject_code", "subject_kind") == ("reg-m1", "mouse")
    stored = (Mouse & key).fetch1()
    assert (stored["sex"], stored["date_of_birth"]) == ("F", born)
    assert (stored["strain_name"], stored["genotype"]) == ("C57BL/6J", "Cux2-CreERT2/wt")
    # Each row is stamped by the package that wrote it.
    assert (SubjectRowMeta & key).fetch1("ingestion_version") == SCENE_WRITER_VERSION
    assert (MouseRowMeta & key).fetch1("ingestion_version") == MOUSE_WRITER_VERSION

    # Same content: VERIFY (default) returns the stored key; changed content raises.
    assert register_mouse("reg-m1", "F", **mouse) == key
    with pytest.raises(ValueError, match="different content hash"):
        register_mouse("reg-m1", "F", **{**mouse, "genotype": "wt"})
    with pytest.warns(UserWarning, match="content hash changed"):
        register_mouse("reg-m1", "M", lab=lab_key, if_exists=DuplicatePolicy.OVERWRITE)
    assert (Mouse & key).fetch1("sex", "date_of_birth", "strain_name") == ("M", None, None)
    assert (Mouse & key).fetch1("genotype") == ""

    # The stored spelling of the strain is written, whatever case the key was given in.
    lower = register_mouse("reg-m4", "F", lab=lab_key, strain={"strain_name": "c57bl/6j"})
    assert (Mouse & lower).fetch1("strain_name") == "C57BL/6J"

    # A subject registered earlier without a Mouse row gets one, under the same id.
    earlier = register_subject("reg-m2", "mouse", lab=lab_key)
    assert register_mouse("reg-m2", "U", lab=lab_key) == earlier

    # An unknown strain is refused before anything is written.
    with pytest.raises(ValueError, match="unknown strain.*ensure_strain"):
        register_mouse("reg-m3", "F", lab=lab_key, strain={"strain_name": "no-such-strain"})
    assert not (Subject & {**lab_key, "subject_code": "reg-m3"})

    # A code that belongs to a subject of another kind is never turned into a mouse.
    register_subject("reg-h1", "human", lab=lab_key)
    for policy in (DuplicatePolicy.VERIFY, DuplicatePolicy.SKIP):
        with pytest.raises(ValueError):
            register_mouse("reg-h1", "F", lab=lab_key, if_exists=policy)
    assert not (Mouse & (Subject & {**lab_key, "subject_code": "reg-h1"}))


def test_mouse_requires_an_existing_subject(dj_connection):
    import datajoint as dj
    from base_schemas.schemas.mouse.mouse import Mouse

    with pytest.raises(dj.errors.IntegrityError):
        Mouse.insert1({"subject_id": "c" * 32, "sex": "M"})
