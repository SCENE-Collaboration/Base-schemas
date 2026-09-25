"""Admin catalog writes (Lab, Task, …).

Pipeline roles should SELECT these tables only; use these helpers with an
admin DB role. Markers: ``mark_admin_write`` on the table classes.
"""

from base_schemas.admin.lab import ensure_lab
from base_schemas.admin.task import ensure_task

__all__ = ["ensure_lab", "ensure_task"]
