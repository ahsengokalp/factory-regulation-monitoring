from __future__ import annotations

from src.core.models import GazetteItem


def is_excluded_section(item: GazetteItem) -> bool:
    if not item.section:
        return False
    return "İLAN" in item.section.upper()


def build_haystack(item: GazetteItem) -> str:
    return " ".join([x for x in [item.section, item.subsection, item.title] if x])


def is_ilan_url(url: str) -> bool:
    return "/ilanlar/" in (url or "").lower()


def contains_financial_keywords(text: str) -> bool:
    if not text:
        return False
    kws = [
        "vergi",
        "özel tüketim vergisi",
        "kDV",
        "kdv",
        "vergi tutar",
        "vergi oran",
        "stopaj",
        "matrah",
        "vergiye",
        "vergisi",
    ]
    lower = text.lower()
    return any(k.lower() in lower for k in kws)
