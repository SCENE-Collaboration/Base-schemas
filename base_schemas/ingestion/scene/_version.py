"""Version of the scene write helpers, stamped as ``ingestion_version`` on every row they write.

Bump it when a helper in this package changes what it writes or what it
hashes into ``content_hash``. Other ingestion packages version separately.
"""

SCENE_WRITER_VERSION = "0.0.1"
