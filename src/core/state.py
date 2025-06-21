from __future__ import annotations

import json
from pathlib import Path


class SeenState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._seen: set[str] = set()

    def load(self) -> None:
        if not self.path.exists():
            self._seen = set()
            return

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = []

        if isinstance(payload, list):
            self._seen = {str(item) for item in payload}
        else:
            self._seen = set()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = sorted(self._seen)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_seen(self, item_id: str) -> bool:
        return item_id in self._seen

    def mark_seen(self, item_id: str) -> None:
        self._seen.add(item_id)
