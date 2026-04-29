"""Sync rows of base_schemas tables between two DataJoint servers.

Requires DataJoint >= 2.2 for `dj.Instance`.
"""

from __future__ import annotations

import logging
from typing import Iterable, Mapping

import datajoint as dj


def _require_instance_api():
    if not hasattr(dj, "Instance"):
        raise ImportError(
            "base_schemas.scripts.sync requires datajoint>=2.2 "
            "(dj.Instance was introduced in 2.2)"
        )


def _build_instance(config):
    kwargs = {
        "host": config["host"],
        "user": config["user"],
        "password": config["password"],
    }
    for optional_key in ("port", "use_tls"):
        if optional_key in config:
            kwargs[optional_key] = config[optional_key]
    return dj.Instance(**kwargs)


def sync_tables(
    source_config: Mapping,
    target_config: Mapping,
    tables: Iterable,
    *,
    restrictions: Mapping | None = None,
    logger: logging.Logger | None = None,
):
    """Copy rows from a source DataJoint server to a target server.

    For each table, rows present in source but missing in target are inserted.
    Existing rows in the target are not modified. Tables are processed in the
    order they are provided; pass them in FK-dependency order.

    Parameters
    ----------
    source_config, target_config : Mapping
        Connection info. Keys: `host`, `user`, `password`; optional: `port`, `use_tls`.
    tables : Iterable[dj.Table | str | tuple[str, str]]
        Each entry can be one of:
          * a DataJoint table class — its `full_table_name` is used for both
            source and target;
          * a `full_table_name` string (e.g.
            "`mice`.`#mouse_score_sheet__body_condition`") — used for both
            source and target. Use this to override the class-derived name
            when a server uses a non-default naming (e.g. legacy DataJoint
            named tables with double underscores for class names containing
            underscores);
          * a `(source_name, target_name)` tuple — when the same logical
            table has different physical names on the two servers (e.g.
            legacy `__` on the source vs. DJ 2.2 `_` on the target).
        Class instances can be bound to either server's connection (or to
        none, if imported under USE_LAZY_SCHEMA).
    restrictions : Mapping, optional
        Per-table DataJoint restriction applied to the source before fetching,
        e.g. {Session: "doe >= '2026-01-01'"} for incremental syncs. Keys must
        match the entry passed in `tables` — the class object, the same
        `full_table_name` string, or the same `(src_name, tgt_name)` tuple.

    Returns
    -------
    dict[str, dict]
        Maps source `full_table_name` to {"fetched": int, "inserted": int,
        "target": str}. The "target" key holds the target full_table_name
        (equal to source unless the entry was a (src, tgt) tuple).
    """
    _require_instance_api()
    logger = logger or logging.getLogger(__name__)
    restrictions = restrictions or {}

    src_instance = _build_instance(source_config)
    tgt_instance = _build_instance(target_config)

    results = {}
    for entry in tables:
        if isinstance(entry, tuple):
            if len(entry) != 2 or not all(isinstance(name, str) for name in entry):
                raise ValueError(
                    "Invalid tables entry: tuple entries must be "
                    "(src_name, tgt_name) with exactly two strings. "
                    "Supported forms are: a table name string, a "
                    "(src_name, tgt_name) tuple of strings, or an object "
                    "with a full_table_name attribute."
                )
            src_name, tgt_name = entry
        elif isinstance(entry, str):
            src_name = tgt_name = entry
        else:
            src_name = tgt_name = entry.full_table_name
        if src_name in results:
            raise ValueError(
                f"Duplicate source table name {src_name!r} in `tables`: each "
                "source table may appear at most once per sync_tables call."
            )
        display = src_name if src_name == tgt_name else f"{src_name} -> {tgt_name}"
        logger.info("Syncing table %s", display)

        src_table = src_instance.FreeTable(src_name)
        tgt_table = tgt_instance.FreeTable(tgt_name)

        restriction = restrictions.get(entry)
        if restriction is not None:
            src_table = src_table & restriction

        rows = src_table.fetch(as_dict=True)
        before = len(tgt_table)
        tgt_table.insert(rows, skip_duplicates=True, ignore_extra_fields=True)
        after = len(tgt_table)
        inserted = after - before

        logger.info(
            "Synced %s: fetched %d, inserted %d (%d already present)\n",
            display,
            len(rows),
            inserted,
            len(rows) - inserted,
        )
        results[src_name] = {"fetched": len(rows), "inserted": inserted, "target": tgt_name}

    return results
