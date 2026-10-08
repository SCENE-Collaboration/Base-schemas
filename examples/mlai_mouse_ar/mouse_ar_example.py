"""MouseAR on the shared SCENE layer: example for the M-lab (MLAI).

Run it against a MySQL database (``make db_up``)::

    python examples/mlai_mouse_ar/mouse_ar_example.py

It writes under the schema prefix ``mousear_example_`` and can be re-run.

The layers, from shared to specific::

    scene (shared)       Lab, Project, Subject, Session          base_schemas
    mouse (shared)       Strain, Mouse                           base_schemas
    mlai (lab)           MouseInfo, SessionInfo, score sheets    mlai_schemas, mlai_ingestion
    mousear (pipeline)   Dataset, SessionDataset, ...            this file (the MouseAR repo)

Sections:
    0. Connect and activate the schemas
    1. Admin: lab and project
    2. Shared layer: a strain
    3. MLAI layer: an experimenter and a mouse
    4. MouseAR: register sessions and link each dataset to its session
    5. Cron job: populate sessions from the GUI's metadata files
    6. Queries across the layers
    7. Legacy data: migrate the old mice / exp tables
"""

import datetime as dt
import json
import tempfile
from pathlib import Path

import datajoint as dj
from base_schemas.core import SCENE_REGISTRY, load_settings
from base_schemas.ingestion.mouse import ensure_strain
from base_schemas.ingestion.provenance import DuplicatePolicy
from base_schemas.ingestion.scene import admin
from base_schemas.schemas.mouse.mouse import Mouse, Strain
from base_schemas.schemas.scene.project import Project
from base_schemas.schemas.scene.session import Session
from base_schemas.schemas.scene.subject import Subject
from mlai_ingestion.ingestion import (
    MLAI_LAB,
    MLAI_LAB_KEY,
    ensure_mlai_experimenter,
    register_mlai_mouse,
    register_mlai_session,
)
from mlai_ingestion.populate import populate_base, scan_directory
from mlai_schemas.mouse import Sacrificed, ScoreSheet
from mlai_schemas.session import SessionInfo, SessionScoreSheet
from utils import connect_to_database

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
ensure_mlai_experimenter("jdoe", full_name="Jane Doe", mail="jane.doe@example.org")

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


# --- 4. MouseAR: register sessions and link each dataset to its session ------------------
# A session is registered with the MouseAR project. Its code is
# <mouse>_<date>_<attempt>; date, project, experimenter and mouse go to the
# shared Session, the rest to the lab's SessionInfo.
day = dt.date(2026, 2, 11)
session = {
    "project": mousear_key,
    "experimenter_code": "jdoe",
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

# In MouseAR every table hangs off `dataset_id`. The only table that touches the
# shared layer is SessionDataset: it references the shared Session instead of
# the legacy exp.Session. Reduced copies of both tables:
mousear = dj.Schema(load_settings().db_name("mousear_dataset"))


@mousear
class Dataset(dj.Manual):
    definition = """
    dataset_id: varchar(64)  # <mouse>_<yyyymmdd>_<hhmmss>, from the Unity file name
    ---
    session_date: datetime
    """


@mousear
class SessionDataset(dj.Computed):
    definition = """  # links a dataset to its session
    -> Dataset
    ---
    -> Session
    """

    def make(self, key):
        # Datasets carry a timestamp, not the attempt: the n-th dataset of a
        # mouse on a day belongs to the n-th attempt.
        dataset = (Dataset & key).fetch1()
        mouse_name = dataset["dataset_id"].split("_")[0]
        recorded_on = dataset["session_date"].date()

        same_mouse = (Dataset & f"dataset_id LIKE '{mouse_name}\\_%'").to_dicts()
        same_day = sorted(
            d["dataset_id"] for d in same_mouse if d["session_date"].date() == recorded_on
        )
        sessions = (
            Session * Session.Subject * Subject * SessionInfo
            & MLAI_LAB_KEY
            & {"subject_code": mouse_name, "session_date": recorded_on}
        ).keys(order_by="attempt")

        index = same_day.index(dataset["dataset_id"])
        if index < len(sessions):
            self.insert1({**key, **{name: sessions[index][name] for name in Session.primary_key}})


Dataset.insert(
    [
        {"dataset_id": "Tick_20260211_091500", "session_date": dt.datetime(2026, 2, 11, 9, 15)},
        {"dataset_id": "Tick_20260211_143000", "session_date": dt.datetime(2026, 2, 11, 14, 30)},
    ],
    skip_duplicates=True,
)
SessionDataset.populate()

for row in (SessionDataset * Session).to_dicts(order_by="dataset_id"):
    print(f"{row['dataset_id']} -> {row['session_code']}")


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
# From a dataset up to the mouse's strain: pipeline -> scene -> mouse.
dataset = {"dataset_id": "Tick_20260211_091500"}
row = (SessionDataset * Session * Session.Subject * Mouse * Strain & dataset).fetch1()
print(f"strain of {dataset['dataset_id']}: {row['strain_name']} ({row['rrid']})")

# Lab fields join on the same keys: rig and task of that dataset's session.
print("rig, task:", (SessionDataset * SessionInfo & dataset).fetch1("rig_id", "task_name"))

# The welfare check of a session is tied to the session's own mouse.
check = (SessionScoreSheet * ScoreSheet & morning).fetch1()
print("score sheet:", check["doc"], check["body_condition"])

# Mice available for experiments: every mouse of the lab that is not sacrificed.
available = (Subject * Mouse & MLAI_LAB_KEY) - Sacrificed
print("available mice:", sorted(available.to_arrays("subject_code")))


# --- 7. Legacy data: migrate the old mice / exp tables -----------------------------------
# The legacy modules bind to the database on import, hence the late import.
from mlai_ingestion import migrate_legacy_to_v001 as migrate  # noqa: E402
from mlai_schemas.legacy import exp as legacy_exp  # noqa: E402
from mlai_schemas.legacy import mice as legacy_mice  # noqa: E402

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
migrate.migrate_mice(strain_map)
migrated = migrate.migrate_sessions(project=mousear_key, task_names=["AR_visual_discrimination"])
print("migrated:", list((Session & migrated).to_arrays("session_code")))
assert migrate.migrate_sessions(project=mousear_key) == []  # nothing new on a re-run
