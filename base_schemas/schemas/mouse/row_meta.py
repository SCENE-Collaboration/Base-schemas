"""Row-level write provenance for the mouse tables.

Lives in the mouse schema, not in ``provenance``, so labs without mice never
have to activate it.
"""

from base_schemas.schemas.mouse._schema import schema
from base_schemas.schemas.mouse.mouse import Mouse, Strain
from base_schemas.schemas.provenance.deployment import Deployment  # noqa: F401
from base_schemas.schemas.provenance.row_meta import RowMetaBase


@schema
class MouseRowMeta(RowMetaBase):
    """Provenance for one ``Mouse`` row."""

    tracked_table = Mouse
    definition = RowMetaBase.build_definition(tracked_table)


@schema
class StrainRowMeta(RowMetaBase):
    """Provenance for one ``Strain`` row."""

    tracked_table = Strain
    definition = RowMetaBase.build_definition(tracked_table)
