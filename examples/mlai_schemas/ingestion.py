"""MLAI write helpers: the shared row and the lab row, in one transaction.

The shared rows go through the SCENE helpers (``register_mouse``,
``register_session``) and get a provenance stamp. The lab rows are plain
inserts: they are not synced to the consortium, so they carry no stamp.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import datajoint as dj
from base_schemas.core.db import atomic, lookup_key
from base_schemas.ingestion.mouse import register_mouse
from base_schemas.ingestion.provenance import DuplicatePolicy
from base_schemas.ingestion.scene import register_session
from base_schemas.schemas.scene.session import Experimenter, Session
from base_schemas.schemas.scene.subject import Subject

from mlai_schemas._schema import MLAI_LAB
from mlai_schemas.mouse import MouseInfo, ScoreSheet, WaterRestriction
from mlai_schemas.session import ExperimenterInfo, SessionInfo, SessionScoreSheet

MOUSEAR_PROJECT = {"project_name": "mousear"}


def session_code(mouse_name: str, session_date: date, attempt: int) -> str:
    """Lab code of a session: the stem of its metadata file, e.g. ``Tick_2026-02-11_1``."""
    return f"{mouse_name}_{session_date.isoformat()}_{attempt}"


def write_lab_row(table: type[dj.Table], row: dict[str, Any], if_exists: DuplicatePolicy) -> None:
    """Insert a lab row; an existing row is handled like the shared rows, without a stamp.

    ``VERIFY`` compares the stored row field by field (there is no hash), so pass
    values in the type of their column.
    """
    key = {name: row[name] for name in table.primary_key}
    stored = table & key
    if not stored:
        table.insert1(row)
        return
    if if_exists is DuplicatePolicy.REJECT:
        raise ValueError(f"{table.__name__} row {key} is already registered")
    if if_exists is DuplicatePolicy.SKIP:
        return
    current = stored.fetch1()
    changed = sorted(name for name, value in row.items() if current[name] != value)
    if not changed:
        return
    if if_exists is DuplicatePolicy.VERIFY:
        raise ValueError(f"{table.__name__} row {key} is already registered with other {changed}")
    table.update1(row)


def ensure_mlai_experimenter(experimenter_code: str, full_name: str, mail: str = ""):
    """Add an experimenter: the pseudonymous code is shared, name and mail stay in the lab."""
    key = {**MLAI_LAB, "experimenter_code": experimenter_code}
    with atomic(Experimenter.connection):
        Experimenter.insert1(key, skip_duplicates=True)
        write_lab_row(
            ExperimenterInfo,
            {**key, "full_name": full_name, "mail": mail},
            DuplicatePolicy.OVERWRITE,
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
    """Register a mouse on the shared tables and its lab fields in ``MouseInfo``.

    Returns:
        Mouse primary key ``{subject_id: ...}``.
    """
    with atomic(MouseInfo.connection):
        mouse = register_mouse(
            mouse_name,
            sex,
            lab=MLAI_LAB,
            date_of_birth=date_of_birth,
            strain=strain,
            genotype=genotype,
            if_exists=if_exists,
        )
        write_lab_row(MouseInfo, {**mouse, "mouse_id": mouse_id}, if_exists)
        return mouse


def register_mlai_session(
    mouse_name: str,
    session_date: date,
    attempt: int,
    *,
    experimenter_code: str,
    rig_id: int,
    task_name: str,
    anesthesia_name: str = "awake",
    opto_name: str = "none",
    session_notes: str = "",
    score_sheet: dict[str, Any] | None = None,
    project: dict[str, str] = MOUSEAR_PROJECT,
    if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY,
):
    """Register a session of one mouse: shared ``Session`` plus the lab's ``SessionInfo``.

    Args:
        mouse_name: Code of an already registered mouse.
        session_date: Date of the session.
        attempt: Counter for sessions of this mouse on the same day.
        experimenter_code: Code of an existing experimenter of the lab.
        rig_id: Existing ``Rig``.
        task_name: Existing ``Task``.
        anesthesia_name: Existing ``Anesthesia``.
        opto_name: Existing ``Optogenetics`` protocol.
        session_notes: Free text.
        score_sheet: Optional welfare check done at the session: ``license``,
            ``body_condition``, ``general_assay``, ``housing_assay``,
            ``weight_percentage`` and optionally ``doc`` (defaults to ``session_date``).
        project: Existing project key.
        if_exists: Policy when the session is already registered.

    Returns:
        Session primary key ``{lab_id, session_id}``.
    """
    mouse = lookup_key(Subject, {**MLAI_LAB, "subject_code": mouse_name})
    if mouse is None:
        raise ValueError(f"unknown mouse {mouse_name!r}; register it with register_mlai_mouse")

    with atomic(Session.connection):
        session = register_session(
            session_code(mouse_name, session_date, attempt),
            session_date,
            lab=MLAI_LAB,
            subjects=[mouse],
            project=project,
            experimenter={**MLAI_LAB, "experimenter_code": experimenter_code},
            if_exists=if_exists,
        )
        write_lab_row(
            SessionInfo,
            {
                **session,
                "attempt": attempt,
                "rig_id": rig_id,
                "anesthesia_name": anesthesia_name,
                "opto_name": opto_name,
                "task_name": task_name,
                "session_notes": session_notes,
            },
            if_exists,
        )
        if score_sheet is not None:
            check = {**mouse, "doc": score_sheet.get("doc", session_date)}
            sheet = {name: score_sheet[name] for name in ScoreSheet.heading.secondary_attributes}
            write_lab_row(ScoreSheet, {**check, **sheet}, if_exists)
            write_lab_row(
                WaterRestriction,
                {**check, "weight_percentage": score_sheet["weight_percentage"]},
                if_exists,
            )
            write_lab_row(SessionScoreSheet, {**session, **check}, if_exists)
        return session


def register_session_from_metadata(
    payload: dict[str, Any], *, if_exists: DuplicatePolicy = DuplicatePolicy.VERIFY
):
    """Register a session from a metadata dict as the transfer GUI writes it.

    Takes the field names of the legacy ``populate_base`` payload (``mouse_name``,
    ``doe``, ``attempt``, ``experimenter_name``, …). ``day`` and
    ``session_increment`` are ignored: they are no longer stored.
    """
    sheet_fields = ("license", "body_condition", "general_assay", "housing_assay")
    has_sheet = all(name in payload for name in (*sheet_fields, "weight_percentage"))
    return register_mlai_session(
        str(payload["mouse_name"]),
        payload["doe"],
        int(payload["attempt"]),
        experimenter_code=str(payload["experimenter_name"]),
        rig_id=int(payload["rig_id"]),
        task_name=str(payload["task_name"]),
        anesthesia_name=str(payload.get("anesthesia_name", "awake")),
        opto_name=str(payload.get("opto_name", "none")),
        session_notes=str(payload.get("session_notes", "")),
        score_sheet=(
            {
                **{name: str(payload[name]) for name in sheet_fields},
                "weight_percentage": str(payload["weight_percentage"]),
                "doc": payload.get("doc", payload["doe"]),
            }
            if has_sheet
            else None
        ),
        if_exists=if_exists,
    )
