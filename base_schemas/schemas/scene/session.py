"""SCENE-shared session spine (Experimenter, Setup, Session)."""

from __future__ import annotations

import datajoint as dj

from base_schemas.schemas.scene._schema import schema
from base_schemas.schemas.scene.lab import Lab  # noqa: F401  # FK: Session/Setup -> Lab
from base_schemas.schemas.scene.subject import Subject  # noqa: F401
from base_schemas.schemas.scene.task import Task  # noqa: F401


@schema
class Experimenter(dj.Manual):
    """Person who ran a session (shared lookup shape)."""

    definition = """
    experimenter_name: varchar(64)
    ---
    full_name='': varchar(255)
    email='': varchar(128)
    """


@schema
class Setup(dj.Manual):
    """Recording setup / rig / room / booth (local to a lab)."""

    definition = """
    -> Lab
    setup_id: varchar(64)
    ---
    details='': varchar(2048)
    """


@schema
class Session(dj.Manual):
    """One data-collection session within a lab."""

    definition = """
    -> Lab
    session_id: varchar(64)  # stable token; never renamed
    ---
    session_name: varchar(128)  # user-facing label
    session_date: date
    -> [nullable] Task
    -> [nullable] Experimenter
    -> [nullable] Setup
    """

    class Subject(dj.Part):  # noqa: F811
        definition = """
        # subjects that participated in this session
        -> master
        -> Subject
        """
