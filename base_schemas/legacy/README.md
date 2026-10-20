# MLAI legacy schemas (pre-SCENE, unversioned)

The `mice` / `exp` tables and `populate_base`, as they were in
`base_schemas.schemas` and `base_schemas.scripts` before the shared SCENE
layer. Only the import paths changed.

Kept for migrating existing data to the shared layer
(`base_schemas.ingestion.migrate_legacy_to_v001`). Do not build new pipelines
on them.

The modules bind to the database on import (`{DJ_SCHEMA_PREFIX}mice`,
`{DJ_SCHEMA_PREFIX}exp`); set `USE_LAZY_SCHEMA=1` to import them without one.
