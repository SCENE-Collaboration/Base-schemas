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


@mark_sync_authority(SyncAuthority.CENTRAL)
@schema
class Strain(dj.Manual):
    """Shared vocabulary of background strains in official nomenclature (MGI guidelines).

    Any lab adds one with ``ensure_strain``. A background strain (e.g. C57BL/6J),
    Not transgenic line or genotype: those go in ``Mouse.genotype``.
    """

    definition = """
    strain_name: varchar(128)  # official nomenclature, e.g. C57BL/6J — never renamed
    ---
    rrid=null: varchar(64)  # e.g. RRID:IMSR_JAX:000664
    unique index (rrid)
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
    genotype='': varchar(255)  # free text, e.g. Ai148(TIT2L-GC6f-ICL-tTA2)/wt;Cux2-CreERT2/wt
    """
