"""SCENE-shared mouse identity extension (Strain, Mouse)."""

import datajoint as dj

from base_schemas.core.access_markers import (
    SyncAuthority,
    WriteRole,
    mark_sync_authority,
    mark_write_role,
)
from base_schemas.schemas.mouse._schema import schema
from base_schemas.schemas.scene.subject import Subject  # noqa: F401  # FK: Mouse -> Subject


@mark_sync_authority(SyncAuthority.SHARED)
@schema
class Strain(dj.Manual):
    """Shared strain vocabulary — insert a row to add a strain."""

    definition = """
    strain_name: varchar(128)  # short stable name, e.g. C57BL/6J — never renamed
    ---
    formal_name='': varchar(2048)  # full nomenclature
    stock_number='': varchar(255)  # vendor stock number, e.g. JAX 000664
    """


@mark_write_role(WriteRole.ACQUISITION)
@schema
class Mouse(dj.Manual):
    """What every mouse lab records about a mouse; one row per mouse ``Subject``.

    The mouse is the ``Subject``: its identity (``subject_id``, ``subject_code``,
    lab) lives there and is not repeated here. Labs add their own fields in
    tables that reference ``Mouse``, never by redeclaring these.
    """

    definition = """
    -> Subject
    ---
    sex: enum('M', 'F', 'U')  # male, female, unknown
    date_of_birth=null: date
    -> [nullable] Strain
    """
