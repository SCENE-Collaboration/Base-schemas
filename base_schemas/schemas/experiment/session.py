"""SCENE-shared session spine.

Placeholder scientific fields — definitions are subject to change.
``SessionRowMeta`` holds row-level write provenance (not scientific identity).
"""

from __future__ import annotations

import datajoint as dj

from base_schemas.schemas.experiment._schema import schema
from base_schemas.schemas.experiment.deployment import Deployment  # noqa: F401
from base_schemas.schemas.experiment.lab import Lab  # noqa: F401  # FK: Session -> Lab


@schema
class Session(dj.Manual):
    """One data-collection session within a lab."""

    definition = """
    -> Lab
    session_id: varchar(64)  # stable token; never renamed
    ---
    session_name: varchar(128)  # user-facing label
    session_date: date
    """


@schema
class SessionRowMeta(dj.Manual):
    """Row-level write provenance for ``Session`` (not scientific identity).

    Primary key is ``-> Session`` (``lab_id``, ``session_id``). Intended to be
    written by a supported registration path (not hand-edited). Use for sync
    etags and writer-version provenance — not schema DDL (see ``SchemaVersion``).

    ``ingestion_version`` stores ``EXPERIMENT_WRITER_VERSION`` at write time.
    ``content_hash`` is a SHA-256 etag of the caller-chosen session payload
    (see ``base_schemas.core.content_hash``).
    ``deployment_id`` identifies which DB/instance/dataset wrote the row.
    """

    definition = """
    -> Session
    ---
    -> Deployment
    ingestion_version: varchar(32)  # EXPERIMENT_WRITER_VERSION at write time
    content_hash='': char(64)       # sha256 etag of session payload; empty if unset
    updated_at: datetime
    """
