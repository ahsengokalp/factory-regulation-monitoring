from __future__ import annotations

import argparse
from datetime import datetime

from src.pipeline.run_daily import run, default_policies


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    day = datetime.strptime(args.date, "%Y-%m-%d").date()
    run(day=day, policies=default_policies())


if __name__ == "__main__":
    main()
