# MLAI base tables for all datajoint pipelines - extension of the shared SCENE layer

Tables of the M-lab of Adaptive Intelligence (MLAI) that extend the shared SCENE tables
([SCENE-pipelines](https://github.com/SCENE-Collaboration/SCENE-pipelines)).
The mouse and the session live on the shared layer; this package holds only
what is specific to MLAI, in tables that reference the shared ones.

| File | Content |
|---|---|
| `_schema.py` | the `mlai` schema and its DDL version |
| `mouse.py` | `MouseInfo`, surgery, sacrifice, breeding, score sheets |
| `session.py` | `SessionInfo` and its lookups, `ExperimenterInfo`, `SessionScoreSheet` |

Write helpers: `../ingestion`. Legacy `mice` / `exp` tables: `../legacy`.
