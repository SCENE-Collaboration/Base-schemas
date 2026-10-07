"""MLAI extension of the shared SCENE layer (example lab package).

The mouse and the session themselves live on the shared tables
(``Subject``, ``Mouse``, ``Session``). This package adds only what is specific
to MLAI, in tables that reference the shared ones:

- ``mouse``: ``MouseInfo``, surgery, sacrifice, breeding, score sheets
- ``session``: ``SessionInfo`` with its lookups, ``ExperimenterInfo``, ``SessionScoreSheet``
"""
