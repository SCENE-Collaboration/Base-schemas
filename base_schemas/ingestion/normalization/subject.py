"""Subject-id helpers for session registration."""

from __future__ import annotations

from collections.abc import Iterable


def normalize_subject_ids(subject_ids: str | Iterable[str]) -> list[str]:
    """Coerce to an ordered-unique list of subject ids (empty allowed)."""
    if isinstance(subject_ids, str):
        values = [subject_ids]
    else:
        values = list(subject_ids)

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        sid = str(raw).strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        normalized.append(sid)
    return normalized
