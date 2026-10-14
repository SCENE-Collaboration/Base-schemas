"""Write helpers for the scene tables (Subject, Session; admin catalogs in ``admin``).

``register_subject`` and ``register_session`` are everyday pipeline writes;
``subject_key`` and ``session_key`` find a row by its lab code.
``Lab`` and ``Project`` are admin catalogs: see ``base_schemas.ingestion.scene.admin``.
"""

from base_schemas.ingestion.scene._version import SCENE_WRITER_VERSION
from base_schemas.ingestion.scene.session import register_session, session_key
from base_schemas.ingestion.scene.subject import register_subject, subject_key

__all__ = [
    "SCENE_WRITER_VERSION",
    "register_session",
    "register_subject",
    "session_key",
    "subject_key",
]
