"""MLAI write helpers: the shared SCENE row and the lab row, in one transaction.

Shared rows go through the SCENE helpers and are stamped. Lab rows are plain
inserts that skip an existing row.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from base_schemas.core.db import atomic, lookup_key
from base_schemas.ingestion.mouse import register_mouse
from base_schemas.ingestion.provenance import DuplicatePolicy
from base_schemas.ingestion.scene import register_session
from base_schemas.schemas.scene.session import Experimenter, Session
from base_schemas.schemas.scene.subject import Subject
from mlai_schemas.mouse import MouseInfo, ScoreSheet, WaterRestriction
from mlai_schemas.session import ExperimenterInfo, SessionInfo, SessionScoreSheet

MLAI_LAB = {
    "lab_id": "mlai",
    "lab_name": "Mackenzie Mathis Lab of Adaptive Intelligence",
    "institution": "EPFL",
}
MLAI_LAB_KEY = {"lab_id": MLAI_LAB["lab_id"]}


def session_code(mouse_name: str, session_date: date, attempt: int) -> str:
    """Lab code of a session, e.g. ``Tick_2026-02-11_1``."""
    return f"{mouse_name}_{session_date.isoformat()}_{attempt}"


def ensure_mlai_experimenter(experimenter_code: str, full_name: str, mail: str = ""):
    """Add an experimenter: the code is shared, name and mail stay in the lab."""
    key = {**MLAI_LAB_KEY, "experimenter_code": experimenter_code}
    with atomic(Experimenter.connection):
        Experimenter.insert1(key, skip_duplicates=True)
        ExperimenterInfo.insert1(
            {**key, "full_name": full_name, "mail": mail}, skip_duplicates=True
        )
    return key


def register_mlai_mouse(
    mouse_name: str,
    sex: str,
    *,
    mouse_id: int,
    date_of_birth: date | None = None,
    strain: dict[str, str] | None = None,
    genotype: str = "",
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
        MouseInfo.insert1({**mouse, "mouse_id": mouse_id}, skip_duplicates=True)
        return mouse


def register_mlai_session(
    mouse_name: str,
    session_date: date,
    attempt: int,
    *,
    project: dict[str, str],
    experimenter_code: str,
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
    ``body_condition``, ``general_assay``, ``housing_assay``, ``weight_percentage``.
    """
    mouse = lookup_key(Subject, {**MLAI_LAB_KEY, "subject_code": mouse_name})
    if mouse is None:
        raise ValueError(f"unknown mouse {mouse_name!r}; register it with register_mlai_mouse")

    with atomic(Session.connection):
        session = register_session(
            session_code(mouse_name, session_date, attempt),
            session_date,
            lab=MLAI_LAB_KEY,
            subjects=[mouse],
            project=project,
            experimenter={**MLAI_LAB_KEY, "experimenter_code": experimenter_code},
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
            check = {**mouse, "doc": session_date}
            ScoreSheet.insert1(
                {**check, **score_sheet}, skip_duplicates=True, ignore_extra_fields=True
            )
            WaterRestriction.insert1(
                {**check, "weight_percentage": score_sheet["weight_percentage"]},
                skip_duplicates=True,
            )
            SessionScoreSheet.insert1({**session, **check}, skip_duplicates=True)
        return session
