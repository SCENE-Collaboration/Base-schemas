"""Migrate the MLAI schemas from the legacy layout to version 0.0.1.

Legacy is the unversioned ``mice`` / ``exp`` layout (``mlai_schemas.legacy``);
0.0.1 is the shared SCENE layer plus the MLAI tables. Writes through the
same helpers as new data and leaves the legacy tables untouched. Every
step can be re-run: mice and sessions are matched by their code (the mouse
name, and ``<mouse>_<date>_<attempt>``).

The legacy modules bind to the database on import, so they are imported inside
the functions, after the connection is configured.
"""

from __future__ import annotations

from typing import Any

from base_schemas.core.db import lookup_key
from base_schemas.schemas.scene.subject import Subject
from mlai_schemas import mouse, session
from mlai_schemas._schema import MLAI_SCHEMA_VERSION

from mlai_ingestion.ingestion import MLAI_LAB_KEY, ensure_mlai_experimenter, register_mlai_mouse
from mlai_ingestion.populate import SCORE_SHEET_FIELDS, register_from_manifest

assert MLAI_SCHEMA_VERSION == "0.0.1", "this script migrates to MLAI schema version 0.0.1"


def migrate_lookups() -> None:
    """Copy the lookup rows (rigs, tasks, anesthesia, optogenetics, score-sheet scales)."""
    from mlai_schemas.legacy import exp as exp_legacy
    from mlai_schemas.legacy import mice as mice_legacy

    pairs = [
        (exp_legacy.Anesthesia, session.Anesthesia),
        (exp_legacy.Rig, session.Rig),
        (exp_legacy.OptogeneticsRegion, session.OptogeneticsRegion),
        (exp_legacy.OptogeneticsTiming, session.OptogeneticsTiming),
        (exp_legacy.OptogeneticsVariant, session.OptogeneticsVariant),
        (exp_legacy.Optogenetics, session.Optogenetics),
        (exp_legacy.Task, session.Task),
        (mice_legacy.SurgeryType, mouse.SurgeryType),
        (mice_legacy.MouseLicensingGeneva, mouse.License),
        (mice_legacy.MouseScoreSheet_BodyCondition, mouse.BodyCondition),
        (mice_legacy.MouseScoreSheet_GeneralAssay, mouse.GeneralAssay),
        (mice_legacy.MouseScoreSheet_HousingAssesment, mouse.HousingAssay),
    ]
    for legacy_table, table in pairs:
        table.insert(legacy_table.to_dicts(), skip_duplicates=True)


def migrate_mice(strain_map: dict[str, dict]) -> None:
    """Register the legacy experimenters and mice, with their surgery, sacrifice and breeding rows.

    ``strain_map`` says what each legacy ``strain`` value means on the shared
    layer: ``{"strain": <Strain key or None>, "genotype": <text>}``. The legacy
    column mixed background strains and genotypes, so this is decided by hand.
    """
    from mlai_schemas.legacy import exp as exp_legacy
    from mlai_schemas.legacy import mice as mice_legacy

    for row in exp_legacy.Experimenter.to_dicts():
        ensure_mlai_experimenter(row["experimenter_name"], row["full_name"], row["mail"])
    for row in mice_legacy.Mouse.to_dicts():
        mapped = strain_map[row["strain"]]
        register_mlai_mouse(
            row["mouse_name"],
            row["sex"],
            mouse_id=row["mouse_id"],
            date_of_birth=row["dob"],
            strain=mapped.get("strain"),
            genotype=mapped.get("genotype", ""),
        )
    pairs = [
        (mice_legacy.Surgery, mouse.Surgery),
        (mice_legacy.Sacrificed, mouse.Sacrificed),
        (mice_legacy.Breed, mouse.Breed),
    ]
    for legacy_table, table in pairs:
        for row in legacy_table.to_dicts():
            mouse_key = lookup_key(Subject, {**MLAI_LAB_KEY, "subject_code": row.pop("mouse_name")})
            table.insert1({**mouse_key, **row}, skip_duplicates=True)


def manifest_from_legacy(task_names: list[str] | None = None) -> list[dict[str, Any]]:
    """Legacy sessions as a manifest (see ``populate``); every task when none is named."""
    from mlai_schemas.legacy import exp as exp_legacy
    from mlai_schemas.legacy import mice as mice_legacy

    manifest = []
    for row in exp_legacy.Session.to_dicts():
        if task_names is not None and row["task_name"] not in task_names:
            continue
        score_sheet = None
        linked = exp_legacy.SessionScoreSheet & {
            name: row[name] for name in exp_legacy.Session.primary_key
        }
        if linked:
            check = {"mouse_name": row["mouse_name"], "doc": linked.fetch1("doc")}
            sheet = {
                **(mice_legacy.MouseScoreSheet & check).fetch1(),
                **(mice_legacy.MouseScoreSheet_WaterRestriction & check).fetch1(),
            }
            score_sheet = {name: sheet[name] for name in SCORE_SHEET_FIELDS}
        manifest.append(
            {
                "mouse_name": row["mouse_name"],
                "session_date": row["doe"].isoformat(),
                "attempt": row["attempt"],
                "experimenter_code": row["experimenter_name"],
                "rig_id": row["rig_id"],
                "task_name": row["task_name"],
                "anesthesia_name": row["anesthesia_name"],
                "opto_name": row["opto_name"],
                "session_notes": row["session_notes"],
                "score_sheet": score_sheet,
            }
        )
    return manifest


def migrate_sessions(*, project: dict[str, str], task_names: list[str] | None = None) -> list[dict]:
    """Register the legacy sessions of one pipeline under its project.

    The legacy table holds the sessions of every pipeline; ``task_names``
    selects the ones of this project.
    """
    return register_from_manifest(manifest_from_legacy(task_names), project=project)
