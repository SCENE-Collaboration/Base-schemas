"""Soft typing helpers for DataJoint insert / key dicts."""

from __future__ import annotations

from typing import Annotated, Any, TypeVar

from typing_extensions import TypeAliasType  # in ``typing`` from Python 3.12

# ``DjRow[Lab]`` / ``DjKey[Lab]`` name the table a dict belongs to.
# Runtime values are plain dicts; use isinstance(x, dict).
T = TypeVar("T")
DjRow = TypeAliasType("DjRow", Annotated[dict[str, Any], T], type_params=(T,))
DjKey = TypeAliasType("DjKey", Annotated[dict[str, Any], T], type_params=(T,))
