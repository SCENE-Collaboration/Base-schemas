"""MLAI write helpers: the shared SCENE row and the lab row, in one transaction.

Shared rows go through the SCENE helpers and are stamped. Lab rows are plain
inserts that skip an existing row.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from scene_pipelines.core.db import atomic, lookup_key
from scene_pipelines.ingestion.mouse import register_mouse
from scene_pipelines.ingestion.provenance import DuplicatePolicy
from scene_pipelines.ingestion.scene import register_session
from scene_pipelines.schemas.scene.session import Experimenter, Session
from scene_pipelines.schemas.scene.subject import Subject

from base_schemas.schemas.mouse import MouseInfo, ScoreSheet, WaterRestriction
from base_schemas.schemas.session import ExperimenterInfo, SessionInfo, SessionScoreSheet

MLAI_LAB = {
    "lab_id": "mlai",
    "lab_name": "Mackenzie Mathis Lab of Adaptive Intelligence",
    "institution": "EPFL",
}
MLAI_LAB_KEY = {"lab_id": MLAI_LAB["lab_id"]}


def session_code(mouse_name: str, session_date: date, attempt: int) -> str:
    """Lab code of a session, e.g. ``Tick_2026-02-11_1``."""
    return f"{mouse_name}_{session_date.isoformat()}_{attempt}"


def _insert_if_not_stored(table, row: dict[str, Any]) -> None:
    """Insert ``row`` unless its primary key is stored; a unique-index clash still raises."""
    if not (table & {name: row[name] for name in table.primary_key}):
        table.insert1(row)


def ensure_mlai_experimenter(experimenter_code: str, experimenter_name: str, mail: str = ""):
    """Add an experimenter: the code is shared, name and mail stay in the lab."""
    key = {**MLAI_LAB_KEY, "experimenter_code": experimenter_code}
    with atomic(Experimenter.connection):
        Experimenter.insert1(key, skip_duplicates=True)
        _insert_if_not_stored(
            ExperimenterInfo, {**key, "experimenter_name": experimenter_name, "mail": mail}
        )
    return key


def register_mlai_mouse(
    mouse_name: str,
    sex: str,
    *,
    mouse_id: int,
    date_of_birth: date | None = None,
    strain: dict[str, str] | None = None,
    genotype: str | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
):
    """Register a mouse on the shared tables, and its facility id in ``MouseInfo``."""
    with atomic(MouseInfo.connection):
        mouse = register_mouse(
            mouse_name,
            sex,
            lab=MLAI_LAB_KEY,
            date_of_birth=date_of_birth,
            strain=strain,
            genotype=genotype,
            if_exists=if_exists,
        )
        _insert_if_not_stored(MouseInfo, {**mouse, "mouse_id": mouse_id})
        return mouse


def register_mlai_session(
    mouse_name: str,
    session_date: date,
    attempt: int,
    *,
    project: dict[str, str],
    experimenter_name: str,
    rig_id: int,
    task_name: str,
    anesthesia_name: str = "awake",
    opto_name: str = "none",
    session_notes: str = "",
    score_sheet: dict[str, Any] | None = None,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
):
    """Register a session of one mouse on the shared tables, and its ``SessionInfo``.

    ``score_sheet`` is the optional welfare check of the session: ``license``,
    ``body_condition``, ``general_assay``, ``housing_assay``, ``weight_percentage``, and
    optionally ``doc``, the date of the check (default: the session date).
    """
    mouse = lookup_key(Subject, {**MLAI_LAB_KEY, "subject_code": mouse_name})
    if mouse is None:
        raise ValueError(f"unknown mouse {mouse_name!r}; register it with register_mlai_mouse")
    experimenter = (ExperimenterInfo & {"experimenter_name": experimenter_name}).fetch1("KEY")

    with atomic(Session.connection):
        session = register_session(
            session_code(mouse_name, session_date, attempt),
            session_date,
            lab=MLAI_LAB_KEY,
            subjects=[mouse],
            project=project,
            experimenter=experimenter,
            if_exists=if_exists,
        )
        SessionInfo.insert1(
            {
                **session,
                "attempt": attempt,
                "rig_id": rig_id,
                "anesthesia_name": anesthesia_name,
                "opto_name": opto_name,
                "task_name": task_name,
                "session_notes": session_notes,
            },
            skip_duplicates=True,
        )
        if score_sheet is not None:
            check = {**mouse, "doc": score_sheet.get("doc") or session_date}
            ScoreSheet.insert1(
                {**score_sheet, **check}, skip_duplicates=True, ignore_extra_fields=True
            )
            WaterRestriction.insert1(
                {**check, "weight_percentage": score_sheet["weight_percentage"]},
                skip_duplicates=True,
            )
            SessionScoreSheet.insert1({**session, **check}, skip_duplicates=True)
        return session
