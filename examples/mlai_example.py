"""MLAI on the shared SCENE layer: worked example.

Run it against a MySQL database (``DJ_HOST``, ``DJ_USER``, ``DJ_PASS``)::

    python examples/mlai_example.py

It writes under the schema prefix ``mlai_example_`` and can be re-run.

The layers, from shared to specific::

    scene (shared)       Lab, Project, Subject, Session          scene_pipelines
    mouse (shared)       Strain, Mouse                           scene_pipelines
    mlai (lab)           MouseInfo, SessionInfo, score sheets    base_schemas (this package)
    mousear (pipeline)   Dataset, SessionDataset, ...            SCENE_MouseAR

Sections:
    0. Connect and activate the schemas
    1. Admin: lab and project
    2. Shared layer: a strain
    3. MLAI layer: an experimenter and a mouse
    4. Register sessions
    5. Cron job: populate sessions from the GUI's metadata files
    6. Queries across the layers
    7. Legacy data: migrate the old mice / exp tables
"""

import datetime as dt
import json
import os
import tempfile
from pathlib import Path

import datajoint as dj
from scene_pipelines.core import SCENE_REGISTRY
from scene_pipelines.ingestion.mouse import ensure_strain
from scene_pipelines.ingestion.provenance import DuplicatePolicy
from scene_pipelines.ingestion.scene import admin
from scene_pipelines.schemas.mouse.mouse import Mouse, Strain
from scene_pipelines.schemas.scene.project import Project
from scene_pipelines.schemas.scene.session import Session
from scene_pipelines.schemas.scene.subject import Subject

from base_schemas.ingestion import (
    MLAI_LAB,
    MLAI_LAB_KEY,
    ensure_mlai_experimenter,
    populate_base,
    register_mlai_mouse,
    register_mlai_session,
    scan_directory,
)
from base_schemas.schemas.mouse import Sacrificed, ScoreSheet
from base_schemas.schemas.session import SessionInfo, SessionScoreSheet


def connect_to_database(prefix: str = "mlai_example_"):
    """Configure the DataJoint connection and the SCENE settings for the example."""
    # Never the DJ_SCHEMA_PREFIX of the environment: the example must not write into dev or prod.
    os.environ["DJ_SCHEMA_PREFIX"] = prefix
    os.environ["AUTO_ACTIVATE"] = ""  # schemas stay unbound until activate_all()
    os.environ.setdefault("SCENE_DEPLOYMENT_ID", "mlai-example")
    os.environ.setdefault("SCENE_DEPLOYMENT_LABEL", "MLAI example database")

    port = os.environ.get("DJ_PORT", 3306)
    password = os.environ.get("DJ_PASS", "")
    dj.config["database.host"] = os.environ.get("DJ_HOST", "127.0.0.1")
    dj.config["database.port"] = int(port)
    dj.config["database.user"] = os.environ.get("DJ_USER", "root")
    dj.config["database.password"] = password
    dj.config["database.use_tls"] = False


MOUSEAR_PROJECT = {
    "project_name": "mousear",
    "project_title": "Augmented reality for freely moving mice",
}


# --- 0. Connect and activate the schemas ----------------------------------------------------
# The MLAI package registers its schema ("mlai") in the same registry as the
# shared ones; one call binds them all, shared ones first.
connect_to_database()
SCENE_REGISTRY.activate_all()


# --- 1. Admin: lab and project --------------------------------------------------------------
# Consortium catalogs Lab and Project are written once by a admin user.
admin.ensure_lab(MLAI_LAB, if_exists=DuplicatePolicy.VERIFY)
admin.ensure_project(MOUSEAR_PROJECT, if_exists=DuplicatePolicy.VERIFY)

# All users can verify if the project was registered by checking the database.
mousear_key = (Project & {"project_name": MOUSEAR_PROJECT["project_name"]}).fetch1("KEY")
if mousear_key is None:
    raise ValueError("MouseAR project not registered.")

# --- 2. Shared SCENE layer: insert a strain ------------------------------------------------
# Shared vocabulary in official nomenclature; any lab adds what it uses.
c57 = ensure_strain({"strain_name": "C57BL/6J", "rrid": "RRID:IMSR_JAX:000664"})


# --- 3. MLAI layer: insert an experimenter and a mouse ------------------------------------
# Experimenter: only the code is shared. Name and mail stay in the lab table.
ensure_mlai_experimenter("E01", "jdoe", mail="jane.doe@example.org")

# Mouse: name, sex, date of birth, strain and genotype go to the shared tables;
# the facility id is lab-only and goes to MouseInfo. One transaction.
register_mlai_mouse(
    "Tick",
    "F",
    mouse_id=1042,
    date_of_birth=dt.date(2025, 11, 3),
    strain=c57,
    genotype="Cux2-CreERT2/wt; Ai148/wt",
)


# --- 4. Register sessions ------------------------------------------------------------------
# A session is registered with the MouseAR project. Its code is
# <mouse>_<date>_<attempt>; date, project, experimenter and mouse go to the
# shared Session, the rest to the lab's SessionInfo.
day = dt.date(2026, 2, 11)
session = {
    "project": mousear_key,
    "experimenter_name": "jdoe",
    "rig_id": 1,
    "task_name": "AR_visual_discrimination",
}
score_sheet = {
    "license": "N/A",
    "body_condition": "BodyCondition3",
    "general_assay": "Assay5",
    "housing_assay": "Yes",
    "weight_percentage": "2.5",
}
morning = register_mlai_session("Tick", day, 1, **session, score_sheet=score_sheet)
register_mlai_session("Tick", day, 2, **session, session_notes="afternoon run")

# Registering a session again returns the same key (VERIFY is the default).
assert register_mlai_session("Tick", day, 1, **session, score_sheet=score_sheet) == morning

# Linking each MouseAR dataset to its session lives in SCENE_MouseAR (`SessionDataset`).


# --- 5. Cron job: populate sessions from the GUI's metadata files ------------------------
# After a session the transfer GUI writes one file, <mouse>_<date>_<attempt>.json.
# The cron job registers every new file with the same call as before, plus the project.
metadata_folder = Path(tempfile.mkdtemp(prefix="mice_metadata_"))
gui_metadata = {
    "mouse_name": "Tick",
    "doe": "2026-02-12",
    "attempt": 1,
    "experimenter_name": "jdoe",
    "rig_id": 1,
    "task_name": "AR_visual_discrimination",
    **score_sheet,
}
(metadata_folder / "Tick_2026-02-12_1.json").write_text(json.dumps(gui_metadata))

print("manifest:", scan_directory(metadata_folder))  # what would be registered; no database
new = populate_base(metadata_folder, project=mousear_key, suppress_errors=True)
print("populated:", list((Session & new).to_arrays("session_code")))
assert populate_base(metadata_folder, project=mousear_key) == []  # nothing new on a re-run


# --- 6. Queries across the layers -------------------------------------------------------
# From a session up to the mouse's strain: scene -> mouse.
row = (Session * Session.Subject * Mouse * Strain & morning).fetch1()
print(f"strain of {row['session_code']}: {row['strain_name']} ({row['rrid']})")

# Lab fields join on the same keys: rig and task of that session.
print("rig, task:", (SessionInfo & morning).fetch1("rig_id", "task_name"))

# The welfare check of a session is tied to the session's own mouse.
check = (SessionScoreSheet * ScoreSheet & morning).fetch1()
print("score sheet:", check["doc"], check["body_condition"])

# Mice available for experiments: every mouse of the lab that is not sacrificed.
available = (Subject * Mouse & MLAI_LAB_KEY) - Sacrificed
print("available mice:", sorted(available.to_arrays("subject_code")))


# --- 7. Legacy data: migrate the old mice / exp tables -----------------------------------
# The legacy modules bind to the database on import, hence the late import.
from base_schemas.ingestion import migrate_legacy_to_v001 as migrate  # noqa: E402
from base_schemas.legacy import exp as legacy_exp  # noqa: E402
from base_schemas.legacy import mice as legacy_mice  # noqa: E402

# Stand-in for the existing lab database: one mouse with one session.
legacy_mice.Strain.insert1(
    {"strain": "Cux2-Ai148", "formal_name": "Cux2-CreERT2;Ai148", "stock_number": "N/A"},
    skip_duplicates=True,
)
legacy_mice.Mouse.insert1(
    {
        "mouse_name": "Tock",
        "mouse_id": 977,
        "dob": "2025-06-20",
        "sex": "M",
        "strain": "Cux2-Ai148",
    },
    skip_duplicates=True,
)
legacy_exp.Session.insert1(
    {
        "mouse_name": "Tock",
        "day": 1,
        "attempt": 1,
        "doe": "2026-01-12",
        "session_increment": 1,
        "rig_id": 1,
        "experimenter_name": "user",
        "anesthesia_name": "awake",
        "opto_name": "none",
        "task_name": "AR_visual_discrimination",
    },
    skip_duplicates=True,
)

# The legacy `strain` column mixed background strains and genotypes: what each
# value means on the shared layer is decided here, once, by hand.
strain_map = {"Cux2-Ai148": {"strain": c57, "genotype": "Cux2-CreERT2/wt; Ai148/wt"}}
migrate.migrate_lookups()
migrate.migrate_mice(strain_map, experimenter_codes={"user": "E02"})
migrated = migrate.migrate_sessions(project=mousear_key, task_names=["AR_visual_discrimination"])
print("migrated:", list((Session & migrated).to_arrays("session_code")))
assert migrate.migrate_sessions(project=mousear_key) == []  # nothing new on a re-run
