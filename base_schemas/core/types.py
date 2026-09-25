"""Soft typing helpers for DataJoint insert / key dicts."""

from __future__ import annotations

from typing import Any, Dict, TypeVar  # Python 3.8+

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

try:
    from typing import TypeAliasType
except ImportError:  # Python < 3.12
    from typing_extensions import TypeAliasType

# Equivalent to Python 3.12+:
#   type DjRow[T] = Annotated[dict[str, Any], T]
#   type DjKey[T] = Annotated[dict[str, Any], T]
# Runtime values are plain dicts; use isinstance(x, dict).
T = TypeVar("T")
DjRow = TypeAliasType("DjRow", Annotated[Dict[str, Any], T], type_params=(T,))
DjKey = TypeAliasType("DjKey", Annotated[Dict[str, Any], T], type_params=(T,))
