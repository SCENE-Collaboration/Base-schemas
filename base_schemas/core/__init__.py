"""Shared core helpers (config; registry / activation comes in a follow-up)."""

from base_schemas.core.config import Settings, load_settings

__all__ = [
    "Settings",
    "load_settings",
]
