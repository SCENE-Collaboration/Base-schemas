"""Generic DDL schema-version helpers (per MySQL schema / version table).

Each schema defines its ``SchemaVersion`` table from ``SchemaVersionTable``,
which records the code's version in the same step that creates the table. The
helpers below check an existing database against the installed code, e.g.::

    from base_schemas.core.versioning import ensure_schema_version
    from base_schemas.schemas.experiment._schema import (
        EXPERIMENT_SCHEMA_VERSION,
        SchemaVersion,
    )

    ensure_schema_version(EXPERIMENT_SCHEMA_VERSION, SchemaVersion)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar

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


class SchemaVersionTable(dj.Manual):
    """Base for a schema's ``SchemaVersion`` table (subclass it; do not decorate this).

    Creating the table records ``code_version`` right away, so a database never
    exists without its version. Append a row when a migration has been applied;
    the latest ``applied_at`` row is the current version.

    Attributes:
        code_version: Schema version of the installed code, e.g. ``"0.2.0"``.
    """

    code_version: ClassVar[str]

    definition = """
    version: varchar(32)  # schema definition version, e.g. 0.2.0
    ---
    applied_at: datetime
    notes='': varchar(512)
    """

    def declare(self, context=None):
        """Create the table and record ``code_version`` in it."""
        super().declare(context)
        # skip_duplicates: declare() returns quietly if another process created it first.
        self.insert1(
            {
                "version": self.code_version,
                "applied_at": datetime.now(timezone.utc).replace(tzinfo=None),
                "notes": "recorded on creation",
            },
            skip_duplicates=True,
        )


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
