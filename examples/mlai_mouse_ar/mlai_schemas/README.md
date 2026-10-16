# MLAI extension of the shared SCENE layer (example)

Tables of the M-lab (MLAI) that extend the shared SCENE tables. The mouse and
the session live on the shared layer; this package holds only what is specific
to MLAI, in tables that reference the shared ones.

| File | Content |
|---|---|
| `mouse.py` | `MouseInfo`, surgery, sacrifice, breeding, score sheets |
| `session.py` | `SessionInfo` and its lookups, `ExperimenterInfo`, `SessionScoreSheet` |
| `legacy/` | the legacy (unversioned) `mice` / `exp` tables, frozen |

Write helpers: `../mlai_ingestion`. Worked example: `../mouse_ar_example.py`.

Example code: not installed or tested by Base-schemas.
