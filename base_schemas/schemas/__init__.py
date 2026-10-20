"""MLAI extension of the shared SCENE layer (``scene_pipelines``).

The mouse and the session themselves live on the shared tables
(``Subject``, ``Mouse``, ``Session``). This package adds only what is specific
to MLAI, in tables that reference the shared ones:

- ``mouse``: ``MouseInfo``, surgery, sacrifice, breeding, score sheets
- ``session``: ``SessionInfo`` with its lookups, ``ExperimenterInfo``, ``SessionScoreSheet``

Schemas stay unbound on import; ``SCENE_REGISTRY.activate_all()`` binds them
together with the shared ones.
"""
