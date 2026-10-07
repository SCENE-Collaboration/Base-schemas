"""Mathis-lab (MLAI) extension of the shared SCENE layer (example lab package).

The mouse and the session themselves live on the shared tables
(``Subject``, ``Mouse``, ``Session``). This package adds only what is specific
to the lab, in tables that reference the shared ones:

- ``mouse``: ``MouseInfo``, surgery, sacrifice, breeding, score sheets
- ``session``: ``SessionInfo`` with its lookups, ``ExperimenterInfo``, ``SessionScoreSheet``
- ``ingestion``: ``register_mlai_mouse`` / ``register_mlai_session`` write the
  shared row and the lab row in one transaction
- ``migrate``: copy the legacy ``mice`` / ``exp`` tables (``legacy/``, version 0)
"""
