# MLAI legacy schemas (pre-SCENE, unversioned)

The `mice` / `exp` tables and `populate_base`, as they were in
`base_schemas.schemas` and `base_schemas.scripts` before the shared SCENE
layer. Only the import paths changed.

Kept for migrating existing data to the shared layer
(`migrate_to_v001.py`, one-off; goes with this folder once the legacy tables are retired).
Do not build new pipelines on them.

The modules bind to the database on import (`{DJ_SCHEMA_PREFIX}mice`,
`{DJ_SCHEMA_PREFIX}exp`); set `USE_LAZY_SCHEMA=1` to import them without one.
