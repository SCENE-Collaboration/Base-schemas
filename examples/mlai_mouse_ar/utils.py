import os
from pathlib import Path

import datajoint as dj

REPO_ROOT = Path(__file__).resolve().parents[3]


def connect_to_database(prefix: str = "mousear_example_"):
    """Configure the DataJoint connection and the SCENE settings for the example.

    Shell variables win, then the repo ``.env``. The schema prefix is never
    taken from ``.env``, so the example cannot write into dev or production schemas.
    """
    prefix = os.environ.get("DJ_SCHEMA_PREFIX", prefix)  # read before .env is loaded
    env_file = REPO_ROOT / ".env"
    for line in env_file.read_text().splitlines() if env_file.is_file() else []:
        name, sep, value = line.partition("=")
        if sep and not name.strip().startswith("#"):
            os.environ.setdefault(name.strip(), value.strip().strip("'\""))
    os.environ["DJ_SCHEMA_PREFIX"] = prefix
    os.environ["AUTO_ACTIVATE"] = ""  # schemas stay unbound until activate_all()
    os.environ.setdefault("SCENE_DEPLOYMENT_ID", "mlai-example")
    os.environ.setdefault("SCENE_DEPLOYMENT_LABEL", "MLAI example database")

    port = os.environ.get("DJ_PORT") or os.environ.get("MYSQL_PUBLISH_PORT") or 3306
    password = os.environ.get("DJ_PASS") or os.environ.get("MYSQL_ROOT_PASSWORD", "")
    dj.config["database.host"] = os.environ.get("DJ_HOST", "127.0.0.1")
    dj.config["database.port"] = int(port)
    dj.config["database.user"] = os.environ.get("DJ_USER", "root")
    dj.config["database.password"] = password
    dj.config["database.use_tls"] = False
