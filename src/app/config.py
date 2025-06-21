from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path


def _default_daily_path() -> str:
    today = date.today()
    return f"eskiler/{today:%Y/%m/%Y%m%d}.htm"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    rg_base_url: str
    rg_daily_path: str
    request_timeout_seconds: int
    http_max_retries: int
    http_backoff_factor: float
    state_file: Path
    log_level: str
    isg_min_score: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            rg_base_url=os.getenv("RG_BASE_URL", "https://www.resmigazete.gov.tr/"),
            rg_daily_path=os.getenv("RG_DAILY_PATH", _default_daily_path()),
            request_timeout_seconds=_int_env("REQUEST_TIMEOUT_SECONDS", 20),
            http_max_retries=_int_env("HTTP_MAX_RETRIES", 3),
            http_backoff_factor=_float_env("HTTP_BACKOFF_FACTOR", 0.5),
            state_file=Path(os.getenv("STATE_FILE", ".state/seen_items.json")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            isg_min_score=_float_env("ISG_MIN_SCORE", 2.0),
        )
