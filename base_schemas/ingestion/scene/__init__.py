"""Write helpers for the scene tables (Subject, Session; admin catalogs in ``admin``).

``register_subject`` and ``register_session`` are everyday pipeline writes.
``Lab`` and ``Project`` are admin catalogs: see ``base_schemas.ingestion.scene.admin``.
"""

from base_schemas.ingestion.scene._version import SCENE_WRITER_VERSION
from base_schemas.ingestion.scene.session import register_session
from base_schemas.ingestion.scene.subject import register_subject

__all__ = [
    "SCENE_WRITER_VERSION",
    "register_session",
    "register_subject",
]
