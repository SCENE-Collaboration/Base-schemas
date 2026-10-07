# M-Lab schemas, version 0 (pre-SCENE)

Frozen copy of the Mathis-lab `mice` / `exp` tables and `populate_base`, as
they were on Base-schemas `main` before the shared SCENE layer. Table
definitions and populate logic are unchanged; only formatting and the imports
(now relative) differ.

Kept for migration: `../migrate.py` reads these tables and writes them to the
shared layer and the current M-Lab tables. Do not build new pipelines on them.

Not installed or tested by Base-schemas.
