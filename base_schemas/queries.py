"""Common queries across the shared and MLAI tables.

They return DataJoint query expressions, to restrict, join or fetch further.
"""

from scene_pipelines.schemas.mouse.mouse import Mouse
from scene_pipelines.schemas.scene.subject import Subject

from base_schemas.ingestion.ingestion import MLAI_LAB_KEY
from base_schemas.schemas.mouse import Breed, MouseInfo, Sacrificed


def mlai_mice(*mouse_names: str):
    """MLAI mice with their shared and lab fields (``Subject * Mouse * MouseInfo``).

    Args:
        *mouse_names: Mouse names (``subject_code``) to select; all mice when none is given.
    """
    mice = Subject * Mouse * MouseInfo & MLAI_LAB_KEY
    return mice & [{"subject_code": name} for name in mouse_names] if mouse_names else mice


def available_mice():
    """MLAI mice that can be used in experiments: not sacrificed, not breeders."""
    return mlai_mice() - Sacrificed - Breed
