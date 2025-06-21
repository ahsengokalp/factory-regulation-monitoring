from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

#veri şablonu
@dataclass(frozen=True)
class GazetteItem:
    title: str
    url: str
    section: Optional[str] = None      # ör: "YASAMA BÖLÜMÜ"
    subsection: Optional[str] = None   # ör: "KANUN"
