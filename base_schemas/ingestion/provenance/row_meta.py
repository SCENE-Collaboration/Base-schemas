"""Write a tracked row together with its row-level provenance stamp."""

from __future__ import annotations

import enum
import warnings
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

import datajoint as dj

from base_schemas.core.db import atomic
from base_schemas.core.hash import content_hash
from base_schemas.core.types import DjKey, DjRow
from base_schemas.core.versioning import assert_database_compatible
from base_schemas.ingestion.provenance.ingestion_version import SCENE_WRITER_VERSION
from base_schemas.schemas.provenance.deployment import Deployment
from base_schemas.schemas.provenance.row_meta import RowMetaBase


class DuplicatePolicy(str, enum.Enum):
    """What to do when the tracked row's primary key is already stored.

    DataJoint's ``skip_duplicates`` / ``replace`` flags only look at the primary
    key. This policy also compares the ``content_hash`` stored in the row-meta
    stamp, so callers can detect a re-registration with different content.

    Attributes:
        REJECT: Raise ``ValueError``.
        SKIP: Leave the stored row and its stamp untouched.
        VERIFY: Leave the stored row untouched when the stamp hash matches
            ``payload``; raise ``ValueError`` when it differs or no stamp exists.
        OVERWRITE: Overwrite the row and it's stamp. Warns when the hash changed.
            Omitted optional fields are reset to their default.
    """

    REJECT = "reject"
    SKIP = "skip"
    VERIFY = "verify"
    OVERWRITE = "overwrite"


def insert_tracked_row(
    row_meta_table: type[RowMetaBase],
    row: DjRow,
    *,
    payload: dict[str, Any],
    deployment: DjRow[Deployment],
    if_exists: DuplicatePolicy,
    parts: Mapping[type[dj.Part], Sequence[DjRow]] | None = None,
    writer_version: str | None = None,
) -> DjKey:
    """Insert ``row`` into ``row_meta_table.tracked_table`` and stamp it.

    A new primary key is inserted and stamped. An existing primary key is
    handled by ``if_exists``. ``parts`` are written whenever the row is: inserted
    with a new row, replaced on ``OVERWRITE``, and left untouched otherwise. The
    ``Deployment`` row is inserted when missing. All statements run atomically:
    inside the caller's open transaction when there is one, otherwise in a
    transaction opened here.

    Args:
        row_meta_table: Row-meta table; its ``tracked_table`` receives ``row``.
        row: Full insert dict for the tracked table.
        payload: Fields hashed into ``content_hash`` (caller-defined shape).
        deployment: Deployment row to stamp with.
        if_exists: Policy when the tracked primary key already exists.
        parts: Optional part rows per part table, without the master key
            (it is added here), e.g. ``{Session.Subject: [{"subject_id": ...}]}``.
            Include them in ``payload`` so the hash covers them.
        writer_version: Stamped ``ingestion_version``; ``SCENE_WRITER_VERSION``
            when omitted.

    Returns:
        Primary key of the tracked row.

    Raises:
        ValueError: When ``if_exists`` rejects the existing row.
        SchemaVersionError: When a written database's schema version does not
            match the installed code (checked once per database and process).
    """
    tracked_table = row_meta_table.tracked_table
    for table in (tracked_table, row_meta_table):
        assert_database_compatible(table.database)
    row_key = row_meta_table.tracked_key(row)
    stamp = {
        **row_key,
        **{name: deployment[name] for name in Deployment.primary_key},
        "ingestion_version": writer_version or SCENE_WRITER_VERSION,
        "content_hash": content_hash(payload),
        "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }

    with atomic(tracked_table.connection):
        if not (tracked_table & row_key):
            _ensure_deployment(deployment)
            tracked_table.insert1(row)
            _insert_parts(parts, row_key)
            row_meta_table.insert1(stamp)
            return row_key

        stored_hash = _stored_hash(row_meta_table, row_key)
        overwrite = _resolve_duplicate(
            if_exists,
            label=f"{tracked_table.__name__} row {row_key}",
            stored_hash=stored_hash,
            new_hash=stamp["content_hash"],
        )
        if not overwrite:
            return row_key

        _ensure_deployment(deployment)
        # Complement ``row`` with all omitted optional fields set to their default values.
        full_row = {**dict.fromkeys(tracked_table.heading.secondary_attributes), **row}
        tracked_table.update1(full_row)
        for part_table, part_rows in (parts or {}).items():
            _replace_parts(part_table, row_key, part_rows)
        if stored_hash is None:
            row_meta_table.insert1(stamp)
        else:
            row_meta_table.update1(stamp)
        return row_key


def _ensure_deployment(deployment: DjRow[Deployment]) -> None:
    """Insert the Deployment row when missing; warn when the stored label differs.

    ``Deployment`` is append-only (``SyncAuthority.SHARED``): the label is set by
    the first write and never overwritten here.
    """
    stored = Deployment & {name: deployment[name] for name in Deployment.primary_key}
    if not stored:
        Deployment.insert1(deployment)
        return
    stored_label = stored.fetch1("label")
    new_label = deployment.get("label", "")
    if new_label != stored_label:
        warnings.warn(
            f"Deployment {deployment['deployment_id']!r} keeps its stored label "
            f"{stored_label!r}; ignoring {new_label!r} (update the Deployment row to change it)",
            UserWarning,
            stacklevel=4,
        )


def _insert_parts(parts: Mapping[type[dj.Part], Sequence[DjRow]] | None, row_key: DjKey) -> None:
    """Insert each part table's rows under the master ``row_key``."""
    for part_table, part_rows in (parts or {}).items():
        if part_rows:
            part_table.insert([{**row_key, **part_row} for part_row in part_rows])


def _replace_parts(part_table: type[dj.Part], row_key: DjKey, part_rows: Sequence[DjRow]) -> None:
    """Replace the part rows under ``row_key``, writing only the rows that differ.

    Kept rows are not deleted: other tables may reference them.
    """
    primary_key = part_table.primary_key
    secondary = part_table.heading.secondary_attributes

    def identity(row: DjRow) -> tuple:
        return tuple(row[name] for name in primary_key)

    new_rows = {identity(row): row for row in ({**row_key, **part} for part in part_rows)}
    stored_keys = {identity(key): key for key in (part_table & row_key).keys()}

    for ident, key in stored_keys.items():
        if ident not in new_rows:
            (part_table & key).delete_quick()
    added = [row for ident, row in new_rows.items() if ident not in stored_keys]
    if added:
        part_table.insert(added)
    if secondary:
        for ident, row in new_rows.items():
            if ident in stored_keys:
                # Omitted optional fields are reset to their default.
                part_table.update1({**dict.fromkeys(secondary), **row})


def _stored_hash(row_meta_table: type[RowMetaBase], row_key: DjKey) -> str | None:
    """Return the stamped ``content_hash`` for ``row_key``, or None when unstamped."""
    stamp = row_meta_table & row_key
    return stamp.fetch1("content_hash") if stamp else None


def _resolve_duplicate(
    if_exists: DuplicatePolicy,
    *,
    label: str,
    stored_hash: str | None,
    new_hash: str,
) -> bool:
    """Apply ``if_exists`` to an existing tracked row; return whether to overwrite."""
    if if_exists is DuplicatePolicy.REJECT:
        raise ValueError(f"{label} is already registered")
    if if_exists is DuplicatePolicy.SKIP:
        return False
    if if_exists is DuplicatePolicy.VERIFY:
        if stored_hash is None:
            raise ValueError(f"{label} has no provenance stamp to verify against")
        if stored_hash != new_hash:
            raise ValueError(f"{label} is already registered with a different content hash")
        return False
    if if_exists is DuplicatePolicy.OVERWRITE:
        if stored_hash is not None and stored_hash != new_hash:
            # stacklevel: warn -> here -> insert_tracked_row -> helper -> caller
            warnings.warn(f"{label} content hash changed; overwriting", UserWarning, stacklevel=4)
        return True
    raise ValueError(f"unknown DuplicatePolicy {if_exists!r}")
