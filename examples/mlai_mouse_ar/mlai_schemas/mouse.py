"""MLAI mouse tables: what the lab records about a mouse beyond the shared ``Mouse``.

Name, lab, sex, date of birth, strain and genotype are on the shared tables and
are not repeated here. Every table below hangs off ``Mouse`` by ``subject_id``.
"""

import datajoint as dj
from base_schemas.schemas.mouse.mouse import Mouse  # noqa: F401  # FK context

from mlai_schemas._schema import schema


@schema
class MouseInfo(dj.Manual):
    definition = """  # lab-only fields of a mouse
    -> Mouse
    ---
    mouse_id: int32  # animal facility id
    unique index (mouse_id)
    """


@schema
class SurgeryType(dj.Lookup):
    definition = """
    surgery_type: varchar(128)  # surgery short name
    """
    contents = [{"surgery_type": "N/A"}]


@schema
class Surgery(dj.Manual):
    definition = """  # details about the surgery
    -> Mouse
    ---
    -> SurgeryType
    surgery_details: varchar(1024)  # aim of the surgery
    surgery_date=null: varchar(256)
    """


@schema
class Sacrificed(dj.Manual):
    definition = """  # record of sacrifice; these mice are hidden in the GUI
    -> Mouse
    ---
    date_of_sacrifice: datetime
    reason: varchar(2048)
    """


@schema
class Breed(dj.Manual):
    definition = """  # breeders; these mice are hidden in the GUI
    -> Mouse
    """


@schema
class License(dj.Lookup):
    definition = """  # animal licence (Geneva)
    license: varchar(128)
    ---
    informal_title: varchar(2048)
    """
    contents = [{"license": "N/A", "informal_title": "default licence"}]


@schema
class BodyCondition(dj.Lookup):
    definition = """
    body_condition: varchar(128)
    ---
    define_score: varchar(2048)
    """
    contents = [
        {"body_condition": "BodyCondition1", "define_score": "emaciated"},
        {"body_condition": "BodyCondition2", "define_score": "under-conditioned"},
        {"body_condition": "BodyCondition3", "define_score": "well-conditioned"},
        {"body_condition": "BodyCondition4", "define_score": "over-conditioned"},
        {"body_condition": "BodyCondition5", "define_score": "obese"},
    ]


@schema
class GeneralAssay(dj.Lookup):
    definition = """
    general_assay: varchar(128)
    ---
    define_score: varchar(2048)
    """
    contents = [
        {"general_assay": "Assay1", "define_score": "1 or less euthanize cannot not aroused"},
        {
            "general_assay": "Assay2",
            "define_score": "2 or less euthanize unable to rouse without large stim",
        },
        {"general_assay": "Assay3", "define_score": "3 not groomed slow movements"},
        {"general_assay": "Assay4", "define_score": "4 slightly lethargic"},
        {"general_assay": "Assay5", "define_score": "5 normal behavior"},
    ]


@schema
class HousingAssay(dj.Lookup):
    definition = """
    housing_assay: varchar(128)
    ---
    define_score: varchar(2048)
    """
    contents = [
        {"housing_assay": "Yes", "define_score": "animal built housing as normal"},
        {"housing_assay": "No", "define_score": "watch animal for signs of stress"},
    ]


@schema
class ScoreSheet(dj.Manual):
    definition = """  # welfare check of one mouse on one day
    -> Mouse
    doc: date  # date of check
    ---
    -> License
    -> BodyCondition
    -> GeneralAssay
    -> HousingAssay
    """


@schema
class WaterRestriction(dj.Manual):
    definition = """  # weight part of a welfare check
    -> ScoreSheet
    ---
    weight_percentage: varchar(128)  # percentage change from baseline
    """
