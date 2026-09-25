"""Access-intent markers on schema tables (no DB required)."""

from base_schemas.core.access_markers import AccessRole
from base_schemas.schemas.scene.lab import Lab
from base_schemas.schemas.scene.task import Task


def test_lab_and_task_marked_admin_write():
    assert Lab._access_role is AccessRole.ADMIN_WRITE
    assert Task._access_role is AccessRole.ADMIN_WRITE
