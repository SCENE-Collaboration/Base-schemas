"""Central configuration for base_schemas.

Read-only and side-effect free: nothing here mutates the environment or the
process.

Environment
-----------
DJ_SCHEMA_PREFIX
    Prefix for every schema name; empty, or ending in an underscore
    (e.g. ``dev_`` → ``dev_scene``).
AUTO_ACTIVATE
    Opt-in eager bind. If unset/false (default), schemas stay unbound until
    ``activate_schema`` / ``SCENE_REGISTRY.activate`` — no DB required on
    import (see SCENE-Collaboration/Base-schemas#8). If truthy, ``make_schema``
    and table modules that honor this setting bind immediately.
SCENE_DEPLOYMENT_ID
    Stable id of this database, e.g. ``mlai-prod``. Default ``deployment`` for
    the insertion helpers when the argument is omitted.
SCENE_DEPLOYMENT_LABEL
    Optional human label stored on ``Deployment`` when using the env default.
SCENE_LAB_ID
    Optional lab of this deployment, e.g. ``mlai``. Default ``lab`` for the
    lookup helpers (``subject_key``, ``session_key``); never for writes.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

_PREFIX_RE = re.compile(r"[A-Za-z0-9_]*")
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in _TRUTHY


@dataclass(frozen=True)
class Settings:
    """Immutable resolved settings. ``prefix`` includes the trailing underscore."""

    prefix: str
    auto_activate: bool
    deployment_id: str | None
    deployment_label: str
    lab_id: str | None = None

    def db_name(self, suffix: str) -> str:
        """Full prefixed database name, e.g. ``'scene'`` → ``'dev_scene'``."""
        if not suffix:
            raise ValueError("schema suffix must be a non-empty string")
        return f"{self.prefix}{suffix}"


def load_settings() -> Settings:
    """Resolve settings from the environment. Pure: no mutation, no caching."""
    prefix = (os.environ.get("DJ_SCHEMA_PREFIX") or "").strip()
    if not _PREFIX_RE.fullmatch(prefix):
        raise ValueError(f"Invalid DJ_SCHEMA_PREFIX {prefix!r}: must match [A-Za-z0-9_]*")
    if prefix and not prefix.endswith("_"):
        raise ValueError(
            f"Invalid DJ_SCHEMA_PREFIX {prefix!r}: must end with '_' "
            f"(e.g. {prefix + '_'!r} → {prefix + '_scene'!r})"
        )
    deployment_id = (os.environ.get("SCENE_DEPLOYMENT_ID") or "").strip() or None
    deployment_label = (os.environ.get("SCENE_DEPLOYMENT_LABEL") or "").strip()
    lab_id = (os.environ.get("SCENE_LAB_ID") or "").strip() or None
    return Settings(
        prefix=prefix,
        auto_activate=_env_flag("AUTO_ACTIVATE"),
        deployment_id=deployment_id,
        deployment_label=deployment_label,
        lab_id=lab_id,
    )


def deployment_row_from_settings() -> dict[str, str]:
    """Build a deployment insert dict from ``SCENE_DEPLOYMENT_ID`` / ``SCENE_DEPLOYMENT_LABEL``.

    Raises:
        ValueError: If ``SCENE_DEPLOYMENT_ID`` is unset.
    """
    settings = load_settings()
    if not settings.deployment_id:
        raise ValueError("deployment is required: pass deployment={...} or set SCENE_DEPLOYMENT_ID")
    return {
        "deployment_id": settings.deployment_id,
        "label": settings.deployment_label,
    }


def lab_key_from_settings() -> dict[str, str]:
    """Build a lab key from ``SCENE_LAB_ID``.

    Raises:
        ValueError: If ``SCENE_LAB_ID`` is unset.
    """
    lab_id = load_settings().lab_id
    if not lab_id:
        raise ValueError("lab is required: pass lab={...} or set SCENE_LAB_ID")
    return {"lab_id": lab_id}
