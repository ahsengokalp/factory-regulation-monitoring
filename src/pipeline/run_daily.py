from __future__ import annotations

from datetime import date
from typing import List

from src.core.http import build_session
from src.gazette.client import fetch_daily_html, daily_index_url
from src.gazette.parser import parse_daily_items
from src.policies.base import DepartmentPolicy
from src.policies.isg import IsgPolicy


def run(day: date, policies: List[DepartmentPolicy]) -> None:
    session = build_session()

    html = fetch_daily_html(session=session, day=day)
    items = parse_daily_items(html=html, base_url=daily_index_url(day))

    print(f"[INFO] items found: {len(items)}")

    for pol in policies:
        hits = []
        for item in items:
            decision = pol.evaluate_title(item)
            if decision.is_relevant:
                hits.append((item, decision))

        print(f"\n=== Department: {pol.name} | hits: {len(hits)} ===")
        for item, decision in hits[:20]:
            print(f"- ({decision.score}) {item.title}")
            print(f"  {item.url}")


def default_policies() -> List[DepartmentPolicy]:
    return [IsgPolicy()]
