"""Row-level write provenance for tracked tables."""

from __future__ import annotations

import datajoint as dj

from base_schemas.schemas.experiment.session import Session  # noqa: F401
from base_schemas.schemas.provenance._schema import schema
from base_schemas.schemas.provenance.deployment import Deployment  # noqa: F401


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
