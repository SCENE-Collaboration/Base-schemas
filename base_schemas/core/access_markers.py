"""Access-intent markers for SCENE tables (documentation for deploy / grants).

These do NOT enforce MySQL privileges. They signal which tables pipeline roles
should SELECT only; catalog writes are reserved for admin / ensure helpers.
"""

from __future__ import annotations

from enum import Enum


class AccessRole(str, Enum):
    """Intended write role for a table (hint for DB grants, not enforcement)."""

    ADMIN_WRITE = "admin_write"


def mark_admin_write(cls):
    """Mark a table as admin-write: pipeline users should not INSERT."""
    cls._access_role = AccessRole.ADMIN_WRITE
    return cls
