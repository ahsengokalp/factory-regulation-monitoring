from __future__ import annotations

from datetime import date
from typing import Optional

import requests
#günün sayfasını cekmek

BASE = "https://www.resmigazete.gov.tr"

#verilen tarihten link üretir
def daily_index_url(day: date) -> str:
    # ör: https://www.resmigazete.gov.tr/27.02.2026
    return f"{BASE}/{day:%d.%m.%Y}"

#linke gir, sayfayı indir, html metni dön
def fetch_daily_html(session: requests.Session, day: date, timeout_s: int = 30) -> str:
    url = daily_index_url(day)
    resp = session.get(url, timeout=timeout_s)
    resp.raise_for_status()
    return resp.text
