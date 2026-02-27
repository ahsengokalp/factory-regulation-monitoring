from __future__ import annotations

import re
from typing import List

from src.core.models import GazetteItem
from src.policies.base import DepartmentPolicy, PolicyDecision


HIGH_SIGNAL = [
    r"\biş\s*sağlığı\b",
    r"\biş\s*güvenliği\b",
    r"\bİSG\b",
    r"\b6331\b",
    r"\brisk\s*değerlendirm(e|esi)\b",
    r"\biş\s*kazası\b",
    r"\bmeslek\s*hastalığı\b",
    r"\biş\s*güvenliği\s*uzmanı\b",
    r"\bişyeri\s*hekimi\b",
    r"\bkişisel\s*koruyucu\b|\bKKD\b",
    r"\bacil\s*durum\b",
    r"\btehlikeli\b|\bçok\s*tehlikeli\b",
]

MID_SIGNAL = [
    r"\bçalışma\b",
    r"\bdenetim\b",
    r"\bidari\s*para\s*cezası\b",
    r"\bteftiş\b",
    r"\beğitim\b",
]


def _score_text(text: str) -> tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    for pat in HIGH_SIGNAL:
        if re.search(pat, text, flags=re.IGNORECASE):
            score += 10
            reasons.append(f"high:{pat}")

    for pat in MID_SIGNAL:
        if re.search(pat, text, flags=re.IGNORECASE):
            score += 3
            reasons.append(f"mid:{pat}")

    return score, reasons


class IsgPolicy(DepartmentPolicy):
    @property
    def name(self) -> str:
        return "isg"

    def evaluate_title(self, item: GazetteItem) -> PolicyDecision:
        # 1️⃣ İLAN BÖLÜMÜ ise direkt ilgisiz say
        if item.section and "İLAN" in item.section.upper():
            return PolicyDecision(
                is_relevant=False,
                score=0,
                reasons=["section_excluded: İLAN BÖLÜMÜ"],
            )

        haystack = " ".join(
            [x for x in [item.section, item.subsection, item.title] if x]
        )

        score, reasons = _score_text(haystack)
        is_relevant = score >= 10

        return PolicyDecision(is_relevant=is_relevant, score=score, reasons=reasons)
