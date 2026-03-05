from __future__ import annotations

import base64
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"
JSONL_PATH = LOG_DIR / "mail_events.jsonl"
HTML_PATH = LOG_DIR / "mail_log_dashboard.html"
ASSETS_DIR = PROJECT_ROOT / "assets"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _preview_text(value: str, limit: int = 280) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def append_mail_event(
    *,
    status: str,
    mail_from: str,
    recipients: Iterable[str],
    subject: str,
    html_body: str,
    message: str = "",
) -> None:
    event = {
        "time": now_text(),
        "status": status,
        "mail_from": (mail_from or "").strip(),
        "recipients": [r.strip() for r in recipients if r and r.strip()],
        "subject": (subject or "").strip(),
        "body_preview": _preview_text(html_body),
        "message": (message or "").strip(),
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # Keep dashboard in sync with the latest mail events.
    write_dashboard_from_events()


def _read_events(max_rows: int = 1000) -> list[dict]:
    if not JSONL_PATH.exists():
        return []
    rows: list[dict] = []
    with JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows[-max_rows:]


def _logo_data_uri() -> str:
    candidates = (
        (LOG_DIR / "LOGO.png", "image/png"),
        (LOG_DIR / "logo.png", "image/png"),
        (ASSETS_DIR / "dikkan_logo.png", "image/png"),
        (ASSETS_DIR / "dikkan_logo.jpg", "image/jpeg"),
        (ASSETS_DIR / "dikkan_logo.jpeg", "image/jpeg"),
        (ASSETS_DIR / "dikkan_logo.svg", "image/svg+xml"),
    )
    for path, mime in candidates:
        if not path.exists():
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"
    return ""


def _render_dashboard_html(events: list[dict]) -> str:
    sent_count = sum(1 for row in events if row.get("status") == "sent")
    failed_count = sum(1 for row in events if str(row.get("status", "")).startswith("failed"))
    other_count = len(events) - sent_count - failed_count
    logo_src = _logo_data_uri()
    if logo_src:
        logo_html = f'<img class="brand-logo" src="{logo_src}" alt="Dikkan logo" />'
    else:
        logo_html = '<div class="brand-fallback"><span class="d">D</span><span class="ikkan">ikkan</span></div>'

    rows_html: list[str] = []
    for row in reversed(events):
        recipients = row.get("recipients", [])
        if isinstance(recipients, list):
            recipients_text = ", ".join(str(v) for v in recipients)
        else:
            recipients_text = str(recipients)
        rows_html.append(
            (
                "<tr>"
                f"<td>{escape(str(row.get('time', '-')))}</td>"
                f"<td>{escape(str(row.get('status', '-')))}</td>"
                f"<td>{escape(str(row.get('mail_from', '-')))}</td>"
                f"<td>{escape(recipients_text)}</td>"
                f"<td>{escape(str(row.get('subject', '-')))}</td>"
                f"<td>{escape(str(row.get('body_preview', '-')))}</td>"
                f"<td>{escape(str(row.get('message', '-')))}</td>"
                "</tr>"
            )
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Mail Log Dashboard</title>
    <style>
      body {{
        margin: 0;
        padding: 18px;
        font-family: Segoe UI, Arial, sans-serif;
        background: #f5f7fb;
        color: #111827;
      }}
      .wrap {{ max-width: 1400px; margin: 0 auto; }}
      .head {{
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 6px;
      }}
      .brand-logo {{
        height: 54px;
        width: auto;
        display: block;
      }}
      .brand-fallback {{
        font-size: 50px;
        font-weight: 700;
        line-height: 1;
        letter-spacing: 0.4px;
        font-family: Segoe UI, Arial, sans-serif;
      }}
      .brand-fallback .d {{ color: #f07721; }}
      .brand-fallback .ikkan {{ color: #54565a; }}
      h1 {{ margin: 0; }}
      .muted {{ color: #6b7280; font-size: 13px; margin-bottom: 14px; }}
      .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 8px;
        margin-bottom: 14px;
      }}
      .card {{
        background: #fff;
        border: 1px solid #dbe3ef;
        border-radius: 10px;
        padding: 10px;
      }}
      .label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; }}
      .value {{ margin-top: 4px; font-size: 18px; font-weight: 700; }}
      table {{
        width: 100%;
        border-collapse: collapse;
        background: #fff;
        border: 1px solid #dbe3ef;
      }}
      th, td {{
        padding: 8px;
        border-bottom: 1px solid #e8edf5;
        text-align: left;
        vertical-align: top;
        font-size: 12px;
      }}
      th {{ background: #eef3fb; }}
      tr:hover td {{ background: #fafcff; }}
      .empty {{ color: #6b7280; font-style: italic; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="head">
        {logo_html}
        <h1>Mail Log Dashboard</h1>
      </div>
      <div class="muted">Generated at: {escape(now_text())} | Source: {escape(str(JSONL_PATH))}</div>

      <div class="cards">
        <div class="card"><div class="label">Total Events</div><div class="value">{len(events)}</div></div>
        <div class="card"><div class="label">Sent</div><div class="value">{sent_count}</div></div>
        <div class="card"><div class="label">Failed</div><div class="value">{failed_count}</div></div>
        <div class="card"><div class="label">Other</div><div class="value">{other_count}</div></div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Status</th>
            <th>From</th>
            <th>Recipients</th>
            <th>Subject</th>
            <th>Content Preview</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_html) if rows_html else "<tr><td colspan='7' class='empty'>No mail log events yet.</td></tr>"}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


def write_dashboard_from_events(max_rows: int = 1000) -> Path:
    events = _read_events(max_rows=max_rows)
    html = _render_dashboard_html(events)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(html, encoding="utf-8")
    return HTML_PATH
