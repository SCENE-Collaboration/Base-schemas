"""Write helpers for the mouse tables (Strain, Mouse).

Importing this package registers the mouse schema, so it is not re-exported
from ``base_schemas.ingestion``: labs without mice never import it.
"""

from base_schemas.ingestion.mouse._version import MOUSE_WRITER_VERSION
from base_schemas.ingestion.mouse.mouse import register_mouse
from base_schemas.ingestion.mouse.strain import ensure_strain

__all__ = ["MOUSE_WRITER_VERSION", "ensure_strain", "register_mouse"]
