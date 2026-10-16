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
    """Mouse-specific subject metadata; one row per mouse ``Subject`` .

    Subject identity belongs to ``Subject`` and is not duplicated here.
    ``subject_id`` is a minted UUID; the memorable lab-unique ``subject_code``
    and lab membership are attributes of ``Subject``.

    Example:
        Resolve a lab-specific subject code to its key when looking up a mouse::

            Mouse & subject_key("Tick", lab={"lab_id": "mlai"})

            # Or equivalently:
            Mouse & (Subject & {"lab_id": "mlai", "subject_code": "Tick"})

    Note:
        Do NOT restrict ``Mouse`` directly by ``subject_code``. It is not an
        attribute of ``Mouse`` but of ``Subject``::

            Mouse & {"subject_code": "Tick"} # <-- wrong: returns every mouse!
    """

    definition = """
    -> Subject
    ---
    sex: enum('M', 'F', 'U')  # male, female, unknown
    date_of_birth=null: date
    -> [nullable] Strain
    genotype=null: varchar(255)  # free text, e.g. Cux2-CreERT2/wt; null = not recorded
    """
