"""SCENE shared mouse tables (Strain, Mouse).

Species layer on top of ``base_schemas.schemas.scene``: what every mouse lab
records about a mouse. Lab-specific extras live in the lab's own schema and
reference ``Mouse``.

Placeholder scientific tables — definitions are subject to change.

DDL: ``MOUSE_SCHEMA_VERSION`` / ``SchemaVersion``.
"""

from base_schemas.schemas.mouse._schema import MOUSE_SCHEMA_VERSION

__all__ = ["MOUSE_SCHEMA_VERSION"]
