from __future__ import annotations

from datetime import date
from typing import List

from src.app.config import get_settings
from src.core.http import build_session
from src.gazette.client import fetch_daily_html, daily_index_url
from src.gazette.parser import parse_daily_items
from src.notify.emailer import send_html_email
from src.notify.templates import build_generic_email_html, build_generic_email_subject
from src.policies.ik import IkPolicy
from src.policies.lojistik import LojistikPolicy
from src.policies.muhasebe import MuhasebePolicy
from src.policies.base import DepartmentPolicy
from src.policies.isg import IsgPolicy


def run(day: date, policies: List[DepartmentPolicy]) -> None:
    session = build_session()  # http session hazirlar

    html = fetch_daily_html(session=session, day=day)
    # html i madde listesine cevirir
    items = parse_daily_items(html=html, base_url=daily_index_url(day))

    print(f"[INFO] items found: {len(items)}")

    settings = get_settings()
    recipients_map = {
        "isg": settings.isg_recipients,
        "ik": settings.ik_recipients,
        "muhasebe": settings.muhasebe_recipients,
        "lojistik": settings.lojistik_recipients,
    }

    for pol in policies:
        hits = []
        for item in items:
            decision = pol.evaluate_title(item)
            if decision.is_relevant:
                hits.append(item)

        print(f"\n=== Department: {pol.name} | hits: {len(hits)} ===")
        for item in hits[:20]:
            print(f"- {item.title}")
            print(f"  {item.url}")

        if hits:
            recipients = recipients_map[pol.name].split(",")
            subject = build_generic_email_subject(pol.name, day, len(hits))
            html_body = build_generic_email_html(pol.name, day, hits)

            send_html_email(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_user=settings.smtp_user,
                smtp_password=settings.smtp_password,
                mail_from=settings.mail_from,
                recipients=recipients,
                subject=subject,
                html_body=html_body,
            )

            print(f"[INFO] {pol.name.upper()} email sent.")


def default_policies() -> List[DepartmentPolicy]:
    return [IsgPolicy(), IkPolicy(), MuhasebePolicy(), LojistikPolicy()]
