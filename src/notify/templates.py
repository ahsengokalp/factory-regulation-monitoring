from __future__ import annotations

from datetime import date
from typing import Sequence

from src.core.models import GazetteItem


def build_generic_email_subject(dept: str, day: date, count: int) -> str:
    return f"[{dept.upper()}] Resmî Gazete ({day:%d.%m.%Y}) - {count} yeni kayıt"


def build_generic_email_html(dept: str, day: date, items: Sequence[GazetteItem]) -> str:
    title = dept.upper()
    rows = "\n".join(
        f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">
            <div style="font-weight:600;">{_escape(i.title)}</div>
            <div><a href="{i.url}">{i.url}</a></div>
            <div style="color:#666;font-size:12px;margin-top:4px;">
              { _escape(i.section or '') } {(' / ' + _escape(i.subsection)) if i.subsection else ''}
            </div>
          </td>
        </tr>
        """
        for i in items
    )

    return f"""
    <div style="font-family:Arial, sans-serif; max-width:700px;">
      <h2 style="margin:0 0 12px 0;">{title} için Resmî Gazete Bildirimi</h2>
      <div style="color:#444;margin-bottom:12px;">
        Tarih: <b>{day:%d.%m.%Y}</b><br/>
        Bulunan kayıt: <b>{len(items)}</b>
      </div>

      <table style="width:100%; border-collapse:collapse; border:1px solid #eee;">
        {rows}
      </table>

      <p style="color:#666;font-size:12px;margin-top:12px;">
        Not: Bu ilk versiyonda sadece başlığa göre filtreleme yapılmıştır.
      </p>
    </div>
    """


def build_isg_email_subject(day: date, count: int) -> str:
    return build_generic_email_subject("isg", day, count)


def build_isg_email_html(day: date, items: Sequence[GazetteItem]) -> str:
    return build_generic_email_html("isg", day, items)


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
