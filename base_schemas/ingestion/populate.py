"""Populate MLAI sessions from the metadata files the transfer GUI writes.

One file per session, named ``<mouse>_<YYYY-MM-DD>_<attempt>.json`` (or ``.npy``).
``scan_directory`` reads them into a manifest of validated ``SessionManifestEntry``,
``register_from_manifest`` writes a manifest, and ``populate_base`` does both
with the call of the legacy cron job.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from scene_pipelines.core.db import lookup_key
from scene_pipelines.schemas.scene.session import Session
from scene_pipelines.schemas.scene.subject import Subject

from base_schemas.ingestion.ingestion import MLAI_LAB_KEY, register_mlai_session, session_code
from base_schemas.ingestion.manifest import SessionManifestEntry

FILENAME = re.compile(r"(?P<mouse_name>.+)_(?P<session_date>\d{4}-\d{2}-\d{2})_(?P<attempt>\d+)")


def _manifest_entry(path: Path) -> SessionManifestEntry:
    """Read and validate one metadata file; its name must agree with its content."""
    if path.suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = np.load(path, allow_pickle=True).item()

    entry = SessionManifestEntry.from_gui_flat_dict(raw, source=path.name)
    in_content = {
        "mouse_name": entry.mouse_name,
        "session_date": entry.session_date.isoformat(),
        "attempt": str(entry.attempt),
    }
    for name, in_filename in FILENAME.fullmatch(path.stem).groupdict().items():
        if in_content[name] != in_filename:
            raise ValueError(
                f"{name} differs: {in_filename!r} in the name, {in_content[name]!r} inside"
            )
    return entry


def scan_directory(
    folder: str | Path, *, suppress_errors: bool = False, logger: logging.Logger | None = None
) -> list[SessionManifestEntry]:
    """Read the metadata files of ``folder`` into a manifest, one entry per session.

    No database access. Files with another name are ignored. To save the
    manifest as JSON: ``[entry.model_dump(mode="json") for entry in manifest]``.
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
    return sorted(manifest, key=lambda entry: (entry.session_date, entry.attempt))


def register_from_manifest(
    manifest: Iterable[SessionManifestEntry | dict[str, Any]],
    *,
    project: dict[str, str],
    suppress_errors: bool = False,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Register the sessions of a manifest; return the keys of the new ones.

    Entries may also be plain dicts (e.g. a manifest loaded from JSON); they are
    validated first, so an invalid manifest raises before anything is written.
    Sessions that are already registered are skipped, and so are sessions of
    mice that are not registered (with a warning).
    """
    logger = logger or logging.getLogger(__name__)
    manifest = [SessionManifestEntry.model_validate(entry) for entry in manifest]
    known = set((Session & MLAI_LAB_KEY).to_arrays("session_code"))
    registered = []
    for entry in manifest:
        code = session_code(entry.mouse_name, entry.session_date, entry.attempt)
        if code in known:
            continue
        if not lookup_key(Subject, {**MLAI_LAB_KEY, "subject_code": entry.mouse_name}):
            logger.warning(f"Skipping {code}: mouse {entry.mouse_name!r} is not registered")
            continue
        try:
            registered.append(register_mlai_session(**entry.register_kwargs(), project=project))
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
