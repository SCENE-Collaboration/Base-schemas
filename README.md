# M-lab of Adaptive Intelligence (MLAI) base tables for all DataJoint pipelines

The `base_schemas` package holds the MLAI base tables shared across pipelines (MouseAR, VR4Mice, etc). It extends the SCENE-wide tables of
[SCENE-pipelines](https://github.com/SCENE-Collaboration/SCENE-pipelines).

the mouse, session, lab and project tables live there, and this package extends those to what is specific for MLAI.
```
scene (shared)       Lab, Project, Subject, Session          scene_pipelines
mouse (shared)       Strain, Mouse                           scene_pipelines
mlai (lab)           MouseInfo, SessionInfo, score sheets    base_schemas
<pipeline>           e.g. MouseAR's Dataset, SessionDataset  the pipeline's repo
```

| Package | Content |
|---|---|
| `base_schemas.schemas` | MLAI tables: `MouseInfo`, surgery, sacrifice, breeding, score sheets (`mouse`); `SessionInfo` and its lookups, `ExperimenterInfo` (`session`) |
| `base_schemas.ingestion` | write helpers: `ensure_mlai_experimenter`, `register_mlai_mouse`, `register_mlai_session`; `populate_base` for the cron job; `migrate_legacy_to_v001` |
| `base_schemas.legacy` | the previous `mice` / `exp` tables and `populate_base`, frozen; kept for migrating existing data |

Worked example: [`examples/mlai_example.py`](examples/mlai_example.py).

## Usage

Schemas stay unbound on import. Configure the connection, then bind the MLAI
schema together with the shared ones it references:

```python
from scene_pipelines.core import SCENE_REGISTRY

import base_schemas.schemas.session  # registers the "mlai" schema

SCENE_REGISTRY.activate_all()
```

Write through the helpers, not with `insert1`: the shared row and the lab row
go in one transaction, and the shared row gets a provenance stamp.
`SCENE_DEPLOYMENT_ID` must be set (see the SCENE-pipelines README).

```python
from datetime import date

from base_schemas.ingestion import (
    ensure_mlai_experimenter,
    register_mlai_mouse,
    register_mlai_session,
)

ensure_mlai_experimenter("E01", "jdoe")  # code shared; name stays in the lab
register_mlai_mouse("Tick", "F", mouse_id=1042, date_of_birth=date(2025, 11, 3))
register_mlai_session(
    "Tick",
    date(2026, 2, 11),
    1,
    project={"project_name": "mousear"},
    experimenter_name="jdoe",
    rig_id=1,
    task_name="AR_visual_discrimination",
)
```

The transfer GUI's metadata files are registered with `populate_base`, as
before, now with the project of the pipeline:

```python
from base_schemas.ingestion import populate_base

populate_base("/data/mice_metadata", project={"project_name": "mousear"}, suppress_errors=True)
```

`Lab` and `Project` rows are written once by an admin (`scene_pipelines.ingestion.scene.admin`).

## Migrating from the legacy tables

`base_schemas.schemas.mice` / `exp` moved to `base_schemas.legacy` and are no
longer written. `base_schemas.ingestion.migrate_legacy_to_v001` copies their
content through the same helpers as new data and leaves them untouched; every
step can be re-run. See section 7 of the example. Two maps are decided by hand
once: what each legacy `strain` value means on the shared layer (strain and
genotype), and the shared code of each legacy experimenter.

## Installation

Requires Python ≥ 3.10. Installs `scene-pipelines` from GitHub (`dev`).

```
# for development
pip install -e .

# for usage
pip install .
```

Or directly from GitHub (`dev` can be replaced by a commit hash or branch):

```
pip install "git+ssh://git@github.com/SCENE-Collaboration/Base-schemas.git@dev"
pip install "git+https://github.com/SCENE-Collaboration/Base-schemas.git@dev"
```

## Tests

```
pytest tests/test_mlai_populate.py tests/test_populate_base_helpers.py  # no database
pytest tests/                                                         # with DJ_HOST, DJ_USER, DJ_PASS
```

## Acknowledgments

We thank Prof. Mackenzie Mathis, Dr. Tanmay Nath, Dr. Gary Kane, and Dr. Mariia Popova for their early contributions to this codebase, which helped establish the foundation of the shared schemas used across pipelines.
