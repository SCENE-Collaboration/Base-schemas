"""Generic DDL schema-version helpers (per MySQL schema / version table).

Pass the expected code constant and the ``SchemaVersion`` table class for that
schema, e.g.::

    from base_schemas.core.versioning import ensure_schema_version
    from base_schemas.schemas.scene._schema import (
        SCENE_SCHEMA_VERSION,
        SchemaVersion,
    )

    ensure_schema_version(SCENE_SCHEMA_VERSION, SchemaVersion)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import datajoint as dj


class SchemaVersionError(RuntimeError):
    """DB schema definition version does not match installed code."""


@dataclass(frozen=True)
class SchemaVersionStatus:
    """Comparison of installed code vs the latest version row in the DB."""

    expected_version: str
    db_version: str | None

    @property
    def is_unset(self) -> bool:
        return self.db_version is None

    @property
    def is_compatible(self) -> bool:
        return self.db_version == self.expected_version


def get_db_schema_version(version_table: type[dj.Manual]) -> str | None:
    """Return the most recently applied schema version, or None if unset."""
    rows = version_table.fetch(order_by="applied_at DESC", limit=1, as_dict=True)
    return rows[0]["version"] if rows else None


def check_schema_version(
    expected_version: str, version_table: type[dj.Manual]
) -> SchemaVersionStatus:
    """Compare ``expected_version`` (code) to the latest DB version row."""
    return SchemaVersionStatus(
        expected_version=expected_version,
        db_version=get_db_schema_version(version_table),
    )


def assert_schema_compatible(expected_version: str, version_table: type[dj.Manual]) -> str:
    """Require DB version to match code; raise ``SchemaVersionError`` otherwise."""
    status = check_schema_version(expected_version, version_table)
    if status.is_unset:
        raise SchemaVersionError(
            f"Schema version is not recorded in the database. "
            f"Installed code expects {status.expected_version!r}. "
            f"On a fresh DB call ensure_schema_version(); after a migrate, "
            f"insert a SchemaVersion row for the new version."
        )
    if not status.is_compatible:
        raise SchemaVersionError(
            f"Schema version mismatch: database has {status.db_version!r}, "
            f"installed code expects {status.expected_version!r}. "
            f"Migrate the database (or install matching code), then record the "
            f"new version in SchemaVersion."
        )
    return status.expected_version


def ensure_schema_version(
    expected_version: str, version_table: type[dj.Manual], *, notes: str = ""
) -> str:
    """Record ``expected_version`` on an empty DB, or confirm an exact match."""
    status = check_schema_version(expected_version, version_table)
    if status.is_compatible:
        return status.expected_version
    if not status.is_unset:
        raise SchemaVersionError(
            f"Schema version mismatch: database has {status.db_version!r}, "
            f"installed code expects {status.expected_version!r}. "
            f"Refusing to overwrite — migrate explicitly, then insert a new "
            f"SchemaVersion row."
        )
    version_table.insert1(
        {
            "version": expected_version,
            "applied_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "notes": notes,
        }
    )
    return expected_version
