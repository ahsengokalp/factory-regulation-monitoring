#!/usr/bin/env python3
from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def run_once() -> None:
    logging.info("Starting hourly run")
    try:
        # call the existing entrypoint as a subprocess so behavior matches CLI
        subprocess.run([sys.executable, "-m", "src.app.main"], check=False)
    except Exception:
        logging.exception("Run failed")
    logging.info("Hourly run finished")


def sleep_until_next_hour() -> None:
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    seconds = (next_hour - now).total_seconds()
    logging.info("Sleeping %.0f seconds until next hour (%s)", seconds, next_hour.isoformat())
    time.sleep(seconds)


def main() -> None:
    logging.info("Hourly runner started")
    # Run immediately on start, then at every top of hour
    while True:
        run_once()
        sleep_until_next_hour()


if __name__ == "__main__":
    main()
