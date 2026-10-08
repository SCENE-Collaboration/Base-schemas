"""Populate MLAI sessions from the metadata files the transfer GUI writes.

One file per session, named ``<mouse>_<YYYY-MM-DD>_<attempt>.json`` (or ``.npy``).
``scan_directory`` reads them into a manifest, ``register_from_manifest`` writes
a manifest, and ``populate_base`` does both with the call of the legacy cron job.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from base_schemas.core.db import lookup_key
from base_schemas.schemas.scene.session import Session
from base_schemas.schemas.scene.subject import Subject

from mlai_ingestion.ingestion import MLAI_LAB_KEY, register_mlai_session, session_code

FILENAME = re.compile(r"(?P<mouse_name>.+)_(?P<session_date>\d{4}-\d{2}-\d{2})_(?P<attempt>\d+)")
SCORE_SHEET_FIELDS = (
    "license",
    "body_condition",
    "general_assay",
    "housing_assay",
    "weight_percentage",
)


def _manifest_entry(path: Path) -> dict[str, Any]:
    """Read one metadata file into a manifest entry (arguments of ``register_mlai_session``)."""
    if path.suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = np.load(path, allow_pickle=True).item()

    score_sheet = {name: str(raw[name]) for name in SCORE_SHEET_FIELDS if name in raw}
    if score_sheet and len(score_sheet) < len(SCORE_SHEET_FIELDS):
        raise ValueError(f"incomplete score sheet: only {sorted(score_sheet)} given")
    entry = {
        "mouse_name": str(raw["mouse_name"]),
        "session_date": str(raw["doe"])[:10],  # date, datetime or ISO string
        "attempt": int(raw["attempt"]),
        "experimenter_code": str(raw["experimenter_name"]),
        "rig_id": int(raw["rig_id"]),
        "task_name": str(raw["task_name"]),
        "anesthesia_name": str(raw.get("anesthesia_name", "awake")),
        "opto_name": str(raw.get("opto_name", "none")),
        "session_notes": str(raw.get("session_notes", "")),
        "score_sheet": score_sheet or None,
        "source": path.name,
    }
    for name, in_filename in FILENAME.fullmatch(path.stem).groupdict().items():
        if str(entry[name]) != in_filename:
            raise ValueError(f"{name} differs: {in_filename!r} in the name, {entry[name]!r} inside")
    return entry


def scan_directory(
    folder: str | Path, *, suppress_errors: bool = False, logger: logging.Logger | None = None
) -> list[dict[str, Any]]:
    """Read the metadata files of ``folder`` into a manifest, one entry per session.

    No database access. Files with another name are ignored. The manifest is
    plain data (dates as ISO strings), so it can be saved as JSON and inspected.
    """
    logger = logger or logging.getLogger(__name__)
    manifest = []
    for path in sorted(Path(folder).iterdir()):
        if path.suffix not in (".json", ".npy") or not FILENAME.fullmatch(path.stem):
            continue
        try:
            manifest.append(_manifest_entry(path))
        except Exception as error:
            if not suppress_errors:
                raise ValueError(f"{path.name}: {error}") from error
            logger.error(f"Error reading {path.name}: {error}")
    return sorted(manifest, key=lambda entry: (entry["session_date"], entry["attempt"]))


def register_from_manifest(
    manifest: list[dict[str, Any]],
    *,
    project: dict[str, str],
    suppress_errors: bool = False,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Register the sessions of a manifest; return the keys of the new ones.

    Sessions that are already registered are skipped, and so are sessions of
    mice that are not registered (with a warning).
    """
    logger = logger or logging.getLogger(__name__)
    known = set((Session & MLAI_LAB_KEY).to_arrays("session_code"))
    registered = []
    for entry in manifest:
        entry = {name: value for name, value in entry.items() if name != "source"}
        entry["session_date"] = date.fromisoformat(entry["session_date"])
        code = session_code(entry["mouse_name"], entry["session_date"], entry["attempt"])
        if code in known:
            continue
        if not lookup_key(Subject, {**MLAI_LAB_KEY, "subject_code": entry["mouse_name"]}):
            logger.warning(f"Skipping {code}: mouse {entry['mouse_name']!r} is not registered")
            continue
        try:
            registered.append(register_mlai_session(**entry, project=project))
            logger.info(f"Registered session {code}")
        except Exception as error:
            if not suppress_errors:
                raise
            logger.error(f"Error registering {code}: {error}")
    return registered


def populate_base(
    path_to_basemeta: str | Path | None = None,
    *,
    project: dict[str, str],
    suppress_errors: bool = False,
    fix_dates: bool | None = None,  # legacy argument, ignored
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Register every new session found in the metadata folder (the cron job's call).

    ``path_to_basemeta`` defaults to ``PATH_TO_BASEMETA`` from the environment.
    """
    folder = path_to_basemeta or os.environ["PATH_TO_BASEMETA"]
    manifest = scan_directory(folder, suppress_errors=suppress_errors, logger=logger)
    return register_from_manifest(
        manifest, project=project, suppress_errors=suppress_errors, logger=logger
    )
