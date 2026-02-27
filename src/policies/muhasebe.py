from __future__ import annotations

import re
from typing import List

from src.core.models import GazetteItem
from src.policies.base import DepartmentPolicy, PolicyDecision


HIGH_SIGNAL = [
    r"\bvergi\b",
    r"\bkdv\b|\bkatma\s*değer\b",
    r"\bötv\b",
    r"\bgelir\s*vergisi\b",
    r"\bkurumlar\s*vergisi\b",
    r"\btevkifat\b",
    r"\bmuhasebe\b",
    r"\bdefter\b|\be-defter\b|\be-fatura\b|\be-arşiv\b",
    r"\bvuk\b|\bvergi\s*usul\b",
    r"\bfaiz\b|\bgecikme\s*zammı\b",
    r"\bharç\b",
]

MID_SIGNAL = [
    r"\byönetmelik\b",
    r"\btebliğ\b",
    r"\bcumhurbaşkanı\s*kararı\b",
    r"\bkarar\b",
]


def _score(text: str) -> tuple[int, List[str]]:
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


class MuhasebePolicy(DepartmentPolicy):
    @property
    def name(self) -> str:
        return "muhasebe"

    def evaluate_title(self, item: GazetteItem) -> PolicyDecision:
        if item.section and "İLAN" in item.section.upper():
            return PolicyDecision(False, 0, ["section_excluded: İLAN BÖLÜMÜ"])

        haystack = " ".join([x for x in [item.section, item.subsection, item.title] if x])
        score, reasons = _score(haystack)
        return PolicyDecision(is_relevant=score >= 10, score=score, reasons=reasons)
