from __future__ import annotations

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Optional

from src.core.models import GazetteItem


def parse_daily_items(html: str, base_url: str) -> List[GazetteItem]:
    soup = BeautifulSoup(html, "html.parser")

    items: List[GazetteItem] = []
    current_section: Optional[str] = None
    current_subsection: Optional[str] = None

    content = soup.select_one("#html-content")
    if not content:
        return items

    # Sayfada “card-title html-title” ve “html-subtitle” blokları var.
    # Ardından “fihrist-item”’lar geliyor.
    for node in content.select(".html-title, .html-subtitle, .fihrist-item"):
        classes = node.get("class", [])

        if "html-title" in classes:
            current_section = node.get_text(" ", strip=True) or current_section
            continue

        if "html-subtitle" in classes:
            current_subsection = node.get_text(" ", strip=True) or current_subsection
            continue

        if "fihrist-item" in classes:
            a = node.select_one("a")
            if not a:
                continue

            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            url = urljoin(base_url, href)

            if title and url:
                items.append(
                    GazetteItem(
                        title=title,
                        url=url,
                        section=current_section,
                        subsection=current_subsection,
                    )
                )

    return items
