"""Canonical content hashing for row etags / sync comparison."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def content_hash(payload: Any) -> str:
    """SHA-256 of a JSON-canonicalized payload (sorted keys, compact separators).

    Use for sync etags: pass only the fields that should affect equality
    (typically non-primary-key attributes and related part keys). Callers
    decide the payload shape per table.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
