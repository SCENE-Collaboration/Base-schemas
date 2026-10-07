"""MLAI session tables: what the lab records about a session beyond the shared ``Session``.

Date, project, experimenter and the participating mouse are on the shared
tables. ``day`` and ``session_increment`` of the legacy ``exp.Session`` are not
stored any more: both follow from the session dates (see ``session_day``).
"""

import datajoint as dj
from base_schemas.schemas.scene.session import Experimenter, Session  # noqa: F401  # FK context

from mlai_schemas._schema import schema
from mlai_schemas.mouse import ScoreSheet  # noqa: F401  # FK context


@schema
class ExperimenterInfo(dj.Manual):
    definition = """  # personal details: stay in the lab database, never synced
    -> Experimenter
    ---
    full_name: varchar(255)
    mail='': varchar(128)
    """


@schema
class Anesthesia(dj.Lookup):
    definition = """
    anesthesia_name: varchar(20)
    ---
    anesthesia_details='': varchar(1024)
    """
    contents = [
        {
            "anesthesia_name": "awake",
            "anesthesia_details": "mouse is awake and no immediate hx of anesthesia",
        }
    ]


@schema
class Rig(dj.Lookup):
    definition = """
    rig_id: int32  # experimental setup number
    ---
    details: varchar(2048)
    """
    contents = [{"rig_id": 1, "details": "AR"}]


@schema
class OptogeneticsRegion(dj.Lookup):
    definition = """
    opto_region_name: char(10)
    ---
    opto_region_details='': varchar(2048)
    """
    contents = [
        {
            "opto_region_name": "none",
            "opto_region_details": "no optogenetics was applied during the session",
        }
    ]


@schema
class OptogeneticsTiming(dj.Lookup):
    definition = """
    opto_timing_name: varchar(20)
    ---
    opto_timing_details='': varchar(2048)
    """
    contents = [{"opto_timing_name": "none"}]


@schema
class OptogeneticsVariant(dj.Lookup):
    definition = """
    opto_variant_name: char(10)
    ---
    opto_variant_details='': varchar(2048)
    """
    contents = [{"opto_variant_name": "none", "opto_variant_details": "no optogenetics used"}]


@schema
class Optogenetics(dj.Lookup):
    definition = """  # optogenetics protocol used in the session
    opto_name: char(128)
    ---
    pulse_frequency: float64  # Hz
    pulse_length: float64  # ms
    laser_power: float64  # input power at laser tip in mW
    -> OptogeneticsRegion
    -> OptogeneticsTiming
    -> OptogeneticsVariant
    """
    contents = [
        {
            "opto_name": "none",
            "pulse_frequency": -1,
            "pulse_length": -1,
            "laser_power": -1,
            "opto_region_name": "none",
            "opto_timing_name": "none",
            "opto_variant_name": "none",
        }
    ]


@schema
class Task(dj.Lookup):
    definition = """
    task_name: char(100)
    ---
    task_details='': varchar(2048)
    """
    contents = [
        {
            "task_name": "AR_visual_discrimination",
            "task_details": "mouse in AR has to decide which side a white cube is on "
            "by reporting its location at the lick port",
        }
    ]


@schema
class SessionInfo(dj.Manual):
    definition = """  # lab-only fields of a session
    -> Session
    ---
    attempt: int32  # counter for sessions of one mouse on the same day (usually 1)
    -> Rig
    -> Anesthesia
    -> Optogenetics
    -> Task
    session_notes='': varchar(4095)
    """


@schema
class SessionScoreSheet(dj.Manual):
    definition = """  # welfare check done at this session, for the session's mouse
    -> Session.Subject
    ---
    -> ScoreSheet
    """


def session_day(session_key) -> int:
    """Day of the experiment for the session's mouse: 1 on its first session date."""
    from base_schemas.schemas.scene.session import Session as SceneSession

    mouse = (SceneSession.Subject & session_key).fetch1("subject_id")
    dates = (SceneSession * SceneSession.Subject & {"subject_id": mouse}).to_arrays("session_date")
    return ((SceneSession & session_key).fetch1("session_date") - min(dates)).days + 1
