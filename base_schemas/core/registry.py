"""DataJoint schema registry with lazy-by-default activation.

Schemas created via ``SchemaRegistry.make_schema`` stay unbound unless
``AUTO_ACTIVATE`` is set. Bind later with ``activate`` / ``activate_all``, or
call ``activate_schema`` for any ``dj.Schema`` with an explicit suffix.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import datajoint as dj

from base_schemas.core.config import load_settings


def activate_schema(
    schema: Any,
    suffix: str,
    *,
    context: Mapping[str, Any] | None = None,
    create_tables: bool = True,
    connection: Any | None = None,
) -> Any:
    """Run DataJoint ``Schema.activate()`` with ``{DJ_SCHEMA_PREFIX}{suffix}``.

    Args:
        schema: Unbound (or rebound) ``dj.Schema`` instance.
        suffix: Logical schema name without prefix (e.g. ``"experiment"``).
        context: Optional FK resolution mapping passed as ``add_objects``.
        create_tables: Forwarded to ``schema.activate``.
        connection: Optional DataJoint connection forwarded to ``activate``.

    Returns:
        The same ``schema`` instance after activation.

    Raises:
        ValueError: If ``suffix`` is empty.
    """
    if not suffix:
        raise ValueError("schema suffix must be a non-empty string")

    name = load_settings().db_name(suffix)
    kwargs: dict[str, Any] = {"create_tables": create_tables}
    if connection is not None:
        kwargs["connection"] = connection
    if context is not None:
        kwargs["add_objects"] = dict(context)
    schema.activate(name, **kwargs)
    return schema


@dataclass
class _Entry:
    """One registered schema and the defaults used when activating it."""

    suffix: str
    schema: Any
    context: dict[str, Any] | None = None
    create_tables: bool = True


class SchemaRegistry:
    """Track schemas created via ``make_schema`` and bind them on demand.

    Lazy by default: ``make_schema`` returns an unbound ``dj.Schema`` but
    remembers the logical suffix (and optional FK context) so ``activate`` /
    ``activate_all`` can bind without re-stating the name. When
    ``AUTO_ACTIVATE`` is set, ``make_schema`` binds immediately.

    Attributes:
        name: Label for this registry instance (e.g. ``"scene"``).
    """

    def __init__(self, name: str = "default") -> None:
        """Create an empty registry.

        Args:
            name: Human-readable label for this registry instance.
        """
        self.name = name
        self._entries: list[_Entry] = []

    def make_schema(
        self,
        suffix: str,
        context: Mapping[str, Any] | None = None,
        *,
        create_tables: bool = True,
    ) -> dj.Schema:
        """Create a DataJoint schema, unbound unless ``AUTO_ACTIVATE`` is set.

        Args:
            suffix: Logical name without prefix (e.g. ``"experiment"``).
            context: Optional FK resolution mapping. Stored for later
                ``activate`` / ``activate_all``; used immediately when
                auto-activating.
            create_tables: Forwarded when activating.

        Returns:
            A ``dj.Schema`` instance (unbound unless ``AUTO_ACTIVATE``).

        Raises:
            ValueError: If ``suffix`` is empty.
        """
        if not suffix:
            raise ValueError("schema suffix must be a non-empty string")

        schema = dj.Schema()
        stored_context = dict(context) if context is not None else None
        self._entries.append(
            _Entry(
                suffix=suffix,
                schema=schema,
                context=stored_context,
                create_tables=create_tables,
            )
        )
        if load_settings().auto_activate:
            return self.activate(
                schema,
                context=stored_context,
                create_tables=create_tables,
            )
        return schema

    def activate(
        self,
        schema: Any,
        suffix: str | None = None,
        *,
        context: Mapping[str, Any] | None = None,
        create_tables: bool | None = None,
        connection: Any | None = None,
    ) -> Any:
        """Bind ``schema`` using ``activate_schema``, with registry defaults.

        When ``suffix`` is omitted, uses the suffix stored by ``make_schema``.
        Explicit ``context`` / ``create_tables`` override stored values.
        Schemas not created via this registry require an explicit ``suffix``.

        Args:
            schema: Schema instance to bind (typically from ``make_schema``).
            suffix: Logical name without prefix. Optional if ``schema`` was
                registered via ``make_schema``.
            context: Optional FK resolution mapping; defaults to the mapping
                stored at registration when omitted.
            create_tables: Forwarded to ``activate_schema``; defaults to the
                value stored at registration when omitted.
            connection: Optional DataJoint connection forwarded to activate.

        Returns:
            The same ``schema`` instance after activation.

        Raises:
            ValueError: If ``suffix`` is omitted and ``schema`` is not
                registered with this registry.
        """
        entry = self._entry_for(schema)
        resolved_suffix = suffix if suffix is not None else (entry.suffix if entry else None)
        if not resolved_suffix:
            raise ValueError(
                "suffix is required when activating a schema not created via make_schema"
            )

        resolved_context = context
        if resolved_context is None and entry is not None:
            resolved_context = entry.context

        if create_tables is None:
            resolved_create = entry.create_tables if entry is not None else True
        else:
            resolved_create = create_tables

        return activate_schema(
            schema,
            resolved_suffix,
            context=resolved_context,
            create_tables=resolved_create,
            connection=connection,
        )

    def activate_all(
        self,
        *,
        context: Mapping[str, Any] | None = None,
        create_tables: bool | None = None,
        connection: Any | None = None,
    ) -> None:
        """Activate every registered schema that is still unbound.

        Skips schemas that already have a ``database`` set. Per-schema context
        and ``create_tables`` from ``make_schema`` are used unless overridden
        here (a passed ``context`` is applied to every unbound entry).

        Args:
            context: Shared FK mapping applied to all unbound schemas. When
                omitted, each entry uses the context stored at registration.
            create_tables: Shared create-tables flag. When omitted, each entry
                uses the value stored at registration.
            connection: Optional DataJoint connection forwarded to each
                ``activate`` call.
        """
        for entry in list(self._entries):
            if getattr(entry.schema, "database", None):
                continue
            self.activate(
                entry.schema,
                context=context,
                create_tables=create_tables,
                connection=connection,
            )

    def _entry_for(self, schema: Any) -> _Entry | None:
        """Return the registry entry for ``schema``, or ``None`` if unknown."""
        for entry in self._entries:
            if entry.schema is schema:
                return entry
        return None


# Process-wide registry for package schemas and consumers.
SCENE_REGISTRY = SchemaRegistry(name="scene")
