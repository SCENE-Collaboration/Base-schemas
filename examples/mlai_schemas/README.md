# M-Lab extension of the shared SCENE layer (example)

How a lab with an existing pipeline builds on the shared tables. The mouse and
the session live on the shared layer; this package holds only what is specific
to the Mathis lab, in tables that reference the shared ones.

| File | Content |
|---|---|
| `mouse.py` | `MouseInfo`, surgery, sacrifice, breeding, score sheets |
| `session.py` | `SessionInfo` and its lookups, `ExperimenterInfo`, `SessionScoreSheet` |
| `ingestion.py` | `register_mlai_mouse`, `register_mlai_session`: shared row + lab row in one transaction |
| `migrate.py` | copy the legacy `mice` / `exp` tables (`legacy/`) to the new layout |

Worked example: `../mousear_example.py`.

Example code: not installed or tested by Base-schemas. Copy it into a lab
repository to use it.
