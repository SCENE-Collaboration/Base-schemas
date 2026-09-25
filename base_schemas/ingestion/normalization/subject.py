"""Subject-id normalization for session registration helpers."""

from __future__ import annotations

from collections.abc import Iterable


def normalize_subject_ids(subject_ids: str | Iterable[str]) -> list[str]:
    """Coerce to a non-empty, ordered-unique list of subject ids."""
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

    if not normalized:
        raise ValueError("at least one subject_id is required")
    return normalized
