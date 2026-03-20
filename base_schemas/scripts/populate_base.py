import datetime as dt
import json
import os
import re
from functools import lru_cache
from pathlib import Path

import datajoint as dj
import numpy as np

FILENAME_PATTERN = re.compile(
    r"^(?P<mouse_name>.+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<attempt>\d+)\.(?P<suffix>json|npy)$"
)


def _coerce_date(value, field_name):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, np.datetime64):
        return dt.date.fromisoformat(np.datetime_as_string(value, unit="D"))
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    raise ValueError(f"Field '{field_name}' must be a date or ISO date string, got {type(value)!r}")


def _coerce_int(value, field_name):
    if isinstance(value, bool):
        raise ValueError(f"Field '{field_name}' must be an integer, got bool")
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Field '{field_name}' must be an integer, got {type(value)!r}")


def _load_payload(path):
    if path.suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    elif path.suffix == ".npy":
        payload = np.load(path, allow_pickle=True)
        if isinstance(payload, np.ndarray) and payload.shape == ():
            payload = payload.item()
        elif hasattr(payload, "item"):
            payload = payload.item()
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    if not isinstance(payload, dict):
        raise ValueError(f"Expected {path.name} to contain a dictionary payload")

    return payload


def _normalize_payload(raw_payload):
    payload = dict(raw_payload)

    for field_name in (
        "mouse_name",
        "experimenter_name",
        "anesthesia_name",
        "opto_name",
        "task_name",
        "housing_assay",
        "general_assay",
        "body_condition",
        "license",
        "weight_percentage",
    ):
        if field_name in payload:
            payload[field_name] = str(payload[field_name])

    if "doe" in payload:
        payload["doe"] = _coerce_date(payload["doe"], "doe")
    if "doc" in payload:
        payload["doc"] = _coerce_date(payload["doc"], "doc")
    if "attempt" in payload:
        payload["attempt"] = _coerce_int(payload["attempt"], "attempt")
    if "rig_id" in payload:
        payload["rig_id"] = _coerce_int(payload["rig_id"], "rig_id")

    payload["session_notes"] = str(payload.get("session_notes", ""))
    if "day" in payload:
        payload["day"] = _coerce_int(payload["day"], "day")
    if "session_increment" in payload:
        payload["session_increment"] = _coerce_int(
            payload["session_increment"], "session_increment"
        )
    return payload


def _parse_candidate_path(path):
    match = FILENAME_PATTERN.match(path.name)
    if match is None:
        raise ValueError("File name must match {mouse_name}_YYYY-MM-DD_{attempt}.json or .npy")

    return {
        "mouse_name": match.group("mouse_name"),
        "doe": dt.date.fromisoformat(match.group("date")),
        "attempt": int(match.group("attempt")),
    }


def _discover_candidate_files(base_path):
    candidates = []
    for suffix in ("*.json", "*.npy"):
        candidates.extend(path for path in base_path.glob(suffix) if path.is_file())

    parsed_candidates = []
    for path in candidates:
        metadata = _parse_candidate_path(path)
        parsed_candidates.append((metadata["doe"], metadata["attempt"], path))

    return [path for _, _, path in sorted(parsed_candidates, key=lambda item: item[:2])]


def _existing_session_keys():
    from base_schemas.schemas.exp import Session

    return {(row["mouse_name"], row["doe"], row["attempt"]) for row in Session.to_dicts()}


def _get_latest_session_date(mouse_relation):
    if hasattr(mouse_relation, "get_latest_session_date"):
        return mouse_relation.get_latest_session_date()

    from base_schemas.schemas.exp import Session

    session_dates, session_increments = (Session & mouse_relation).fetch(
        "doe",
        "session_increment",
    )
    if len(session_increments) == 0:
        return None

    latest_index = int(np.argmax(session_increments))
    return session_dates[latest_index]


@lru_cache(maxsize=None)
def _schema_required_fields(table):
    return {
        attribute.name
        for attribute in table.heading.attributes.values()
        if not attribute.nullable and attribute.default is None and not attribute.autoincrement
    }


def _validate_insert_row(row, table, row_label):
    missing_fields = sorted(_schema_required_fields(table) - set(row))
    if missing_fields:
        raise ValueError(f"Missing required {row_label} fields: {', '.join(missing_fields)}")


def _validate_payload(payload, path_metadata):
    if payload["mouse_name"] != path_metadata["mouse_name"]:
        raise ValueError(
            f"mouse_name mismatch between file name and payload: {path_metadata['mouse_name']!r} != {payload['mouse_name']!r}"
        )
    if payload["doe"] != path_metadata["doe"]:
        raise ValueError(
            f"doe mismatch between file name and payload: {path_metadata['doe']} != {payload['doe']}"
        )
    if payload["attempt"] != path_metadata["attempt"]:
        raise ValueError(
            f"attempt mismatch between file name and payload: {path_metadata['attempt']} != {payload['attempt']}"
        )


def _compute_session_fields(mouse_relation, session_date, payload, fix_dates):
    starting_date = mouse_relation.get_starting_date()
    latest_session_date = _get_latest_session_date(mouse_relation)

    if latest_session_date is not None and session_date < latest_session_date:
        raise ValueError(
            "Session date "
            f"{session_date} is earlier than the latest existing session date "
            f"{latest_session_date}; inserting it would require reordering session increments"
        )

    if starting_date is None:
        day = 1
        session_increment = 1
    else:
        day = (session_date - starting_date).days + 1
        session_increment = mouse_relation.get_session_increment()

    if day < 1:
        raise ValueError(
            f"Session date {session_date} precedes the first known session date {starting_date}"
        )

    payload_day = payload.get("day")
    if not fix_dates:
        if payload_day is None:
            raise ValueError("Payload must include day when fix_dates is false")
        if payload_day != day:
            raise ValueError(f"Payload day {payload_day} does not match computed day {day}")

    return day, session_increment


def _insert_payload(payload, day, session_increment):
    from base_schemas.schemas.exp import Session, SessionScoreSheet
    from base_schemas.schemas.mice import MouseScoreSheet, MouseScoreSheet_WaterRestriction

    insert_row = {
        **payload,
        "day": day,
        "session_increment": session_increment,
    }

    _validate_insert_row(insert_row, Session, "Session")
    _validate_insert_row(insert_row, MouseScoreSheet, "MouseScoreSheet")
    _validate_insert_row(
        insert_row,
        MouseScoreSheet_WaterRestriction,
        "MouseScoreSheet_WaterRestriction",
    )
    _validate_insert_row(insert_row, SessionScoreSheet, "SessionScoreSheet")

    with dj.conn().transaction:
        Session.insert1(insert_row, skip_duplicates=True, ignore_extra_fields=True)
        MouseScoreSheet.insert1(insert_row, skip_duplicates=True, ignore_extra_fields=True)
        MouseScoreSheet_WaterRestriction.insert1(
            insert_row,
            skip_duplicates=True,
            ignore_extra_fields=True,
        )
        SessionScoreSheet.insert1(insert_row, skip_duplicates=True, ignore_extra_fields=True)


def _format_error(path, payload, error):
    mouse_name = None
    if isinstance(payload, dict):
        mouse_name = payload.get("mouse_name")
    mouse_label = mouse_name if mouse_name is not None else "<unknown mouse>"
    return f"Error processing {path.name} for {mouse_label}: {error}"


def populate_base(
    path_to_basemeta: str | Path | None = None, suppress_errors=False, fix_dates=False, logger=None
):
    """
    Populate the base schemas from .json and .npy files under PATH_TO_BASEMETA.

    Files must contain a dictionary with fields matching the Session, MouseScoreSheet,
    and MouseScoreSheet_WaterRestriction schemas. Files for mice that are not already
    present in Mouse are skipped.
    """
    if path_to_basemeta is None:
        path_to_basemeta = os.environ.get("PATH_TO_BASEMETA")
        if path_to_basemeta is None:
            raise ValueError("PATH_TO_BASEMETA environment variable is not set.")

    from base_schemas.schemas.mice import Mouse

    basemeta_path = Path(path_to_basemeta)
    if not basemeta_path.exists() or not basemeta_path.is_dir():
        raise ValueError(f"PATH_TO_BASEMETA is not a directory: {basemeta_path}")

    existing_session_keys = _existing_session_keys()

    for mouse_meta_path in _discover_candidate_files(basemeta_path):
        raw_payload = None
        normalized_payload = None
        try:
            path_metadata = _parse_candidate_path(mouse_meta_path)
            session_key = (
                path_metadata["mouse_name"],
                path_metadata["doe"],
                path_metadata["attempt"],
            )
            if session_key in existing_session_keys:
                continue

            raw_payload = _load_payload(mouse_meta_path)
            normalized_payload = _normalize_payload(raw_payload)
            _validate_payload(normalized_payload, path_metadata)

            mouse_relation = Mouse & {"mouse_name": normalized_payload["mouse_name"]}
            if len(mouse_relation) == 0:
                message = (
                    f"Skipping {mouse_meta_path.name}: mouse "
                    f"{normalized_payload['mouse_name']!r} is not present in Mouse"
                )
                if logger is not None:
                    logger.warning(message)
                else:
                    print(message)
                continue

            day, session_increment = _compute_session_fields(
                mouse_relation,
                normalized_payload["doe"],
                normalized_payload,
                fix_dates,
            )
            _insert_payload(normalized_payload, day, session_increment)
            existing_session_keys.add(session_key)
        except Exception as error:
            message = _format_error(mouse_meta_path, normalized_payload or raw_payload, error)
            if suppress_errors:
                if logger is not None:
                    logger.error(message)
                else:
                    print(message)
                continue
            raise


if __name__ == "__main__":
    test_environment = bool(int(os.environ.get("TEST_BASE", "0")))
    fix_dates = bool(int(os.environ.get("FIX_DATES", "0")))
    populate_base(suppress_errors=not test_environment, fix_dates=fix_dates)
