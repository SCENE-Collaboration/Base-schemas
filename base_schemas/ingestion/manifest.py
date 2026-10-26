"""Validated manifest entries: one session to register, read from a GUI file or a legacy row.

The entries are validated when they are built, before any database access, so
a bad metadata file fails with the field that is wrong instead of inside the
write. ``model_dump(mode="json")`` gives the plain-data form of a manifest.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_date(value: Any) -> Any:
    """Accept a date, a datetime, an ISO date/datetime string or ``np.datetime64``."""
    if isinstance(value, np.datetime64):
        value = np.datetime_as_string(value, unit="D")
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        return dt.datetime.fromisoformat(value.strip()).date()
    return value


class ScoreSheetEntry(BaseModel):
    """Welfare check of the session's mouse; all values or none."""

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True, frozen=True)

    license: str
    body_condition: str
    general_assay: str
    housing_assay: str
    weight_percentage: str  # percentage change from baseline, e.g. "2.5"
    doc: dt.date | None = None  # date of the check; None: the session's date

    @field_validator("doc", mode="before")
    @classmethod
    def _date_part(cls, value: Any) -> Any:
        return _to_date(value)


SCORE_SHEET_FIELDS = tuple(ScoreSheetEntry.model_fields)


class SessionManifestEntry(BaseModel):
    """Arguments of ``register_mlai_session`` plus ``source``; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True, frozen=True)

    mouse_name: str = Field(min_length=1)
    session_date: dt.date
    attempt: int = Field(ge=1)
    experimenter_name: str = Field(min_length=1)
    rig_id: int
    task_name: str = Field(min_length=1)
    anesthesia_name: str = "awake"
    opto_name: str = "none"
    session_notes: str = ""
    score_sheet: ScoreSheetEntry | None = None
    source: str | None = None  # e.g. the metadata file name; not registered

    @classmethod
    def from_gui_flat_dict(
        cls, raw: dict[str, Any], *, source: str | None = None
    ) -> SessionManifestEntry:
        """Load the transfer GUI's flat dictionary into the canonical shape.

        Maps ``doe`` to ``session_date``, nests the top-level score sheet fields with the
        check's date ``doc``, and drops GUI fields that are not registered (e.g. ``day``).
        """
        data = {name: raw[name] for name in cls.model_fields if name in raw}
        if "doe" in raw:
            data["session_date"] = raw["doe"]
        sheet = {name: raw[name] for name in SCORE_SHEET_FIELDS if raw.get(name) is not None}
        data["score_sheet"] = sheet if set(sheet) - {"doc"} else None  # a date alone: no sheet
        if source is not None:
            data["source"] = source
        return cls.model_validate(data)

    @field_validator("session_date", mode="before")
    @classmethod
    def _date_part(cls, value: Any) -> Any:
        return _to_date(value)

    @field_validator("anesthesia_name", "opto_name", "session_notes", mode="before")
    @classmethod
    def _none_is_default(cls, value: Any, info) -> Any:
        """A field written as null means not given."""
        return cls.model_fields[info.field_name].default if value is None else value

    def register_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for ``register_mlai_session``."""
        return self.model_dump(exclude={"source"})
