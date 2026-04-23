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
    tables : Iterable[dj.Table]
        Table classes to sync. Only their `full_table_name` is used — the classes
        themselves can be bound to either server's connection (or to none, if
        imported under USE_LAZY_SCHEMA).
    restrictions : Mapping[dj.Table, str], optional
        Per-table DataJoint restriction applied to the source before fetching,
        e.g. {Session: "doe >= '2026-01-01'"} for incremental syncs.

    Returns
    -------
    dict[str, dict]
        Maps `full_table_name` to {"fetched": int, "inserted": int}.
    """
    _require_instance_api()
    logger = logger or logging.getLogger(__name__)
    restrictions = restrictions or {}

    src_instance = _build_instance(source_config)
    tgt_instance = _build_instance(target_config)

    results = {}
    for table_cls in tables:
        full_name = table_cls.full_table_name
        src_table = src_instance.FreeTable(full_name)
        tgt_table = tgt_instance.FreeTable(full_name)

        restriction = restrictions.get(table_cls)
        if restriction is not None:
            src_table = src_table & restriction

        rows = src_table.fetch(as_dict=True)
        before = len(tgt_table)
        tgt_table.insert(rows, skip_duplicates=True, ignore_extra_fields=True)
        after = len(tgt_table)
        inserted = after - before

        logger.info(
            "Synced %s: fetched %d, inserted %d (%d already present)",
            full_name,
            len(rows),
            inserted,
            len(rows) - inserted,
        )
        results[full_name] = {"fetched": len(rows), "inserted": inserted}

    return results
