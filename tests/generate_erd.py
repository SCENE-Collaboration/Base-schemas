import os
import time

import datajoint as dj


def configure_datajoint():
    dj.config.update(
        {
            "database.host": os.environ["DJ_HOST"],
            "database.user": os.environ["DJ_USER"],
            "database.password": os.environ["DJ_PASS"],
            "database.port": int(os.environ.get("DJ_PORT", "3306")),
        }
    )


def wait_for_database(max_attempts=30, delay_seconds=2):
    last_error = None
    for _ in range(max_attempts):
        try:
            dj.conn().connect()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError(f"MySQL connection failed: {last_error}")


def generate_erd(output_path="base_schemas_erd.png"):
    from base_schemas.schemas import exp, mice

    (dj.Diagram(mice.schema) + dj.Diagram(exp.schema)).save(output_path)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    configure_datajoint()
    wait_for_database()
    generate_erd()
