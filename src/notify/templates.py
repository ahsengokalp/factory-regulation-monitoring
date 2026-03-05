from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from src.core.models import GazetteItem


def build_generic_email_subject(dept: str, day: date, count: int) -> str:
    return f"[{dept.upper()}] Resmi Gazete ({day:%d.%m.%Y}) - {count} yeni kayit"


def build_generic_email_html(dept: str, day: date, items: Sequence[GazetteItem]) -> str:
    title = dept.upper()
    rows = "\n".join(
        f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">
            <div style="font-weight:600;">{_escape(i.title)}</div>
            <div><a href="{i.url}">{i.url}</a></div>
            <div style="color:#666;font-size:12px;margin-top:4px;">
              {_escape(i.section or '')} {(' / ' + _escape(i.subsection)) if i.subsection else ''}
            </div>
          </td>
        </tr>
        """
        for i in items
    )

    return f"""
    <div style="font-family:Arial, sans-serif; max-width:700px;">
      <h2 style="margin:0 0 12px 0;">{title} icin Resmi Gazete Bildirimi</h2>
      <div style="color:#444;margin-bottom:12px;">
        Tarih: <b>{day:%d.%m.%Y}</b><br/>
        Bulunan kayit: <b>{len(items)}</b>
      </div>

      <table style="width:100%; border-collapse:collapse; border:1px solid #eee;">
        {rows}
      </table>

      <p style="color:#666;font-size:12px;margin-top:12px;">
        Not: Bu ilk versiyonda sadece basliga gore filtreleme yapilmistir.
      </p>
    </div>
    """


def build_isg_email_subject(day: date, count: int) -> str:
    return build_generic_email_subject("isg", day, count)


def build_isg_email_html(day: date, items: Sequence[GazetteItem]) -> str:
    return build_generic_email_html("isg", day, items)


def build_admin_status_email_subject(*, day: date, success: bool) -> str:
    status = "CALISTI" if success else "CALISMADI"
    return f" {status} :[ADMIN] Regulation Monitor {status} ({day:%d.%m.%Y})"


def build_admin_status_email_html(
    *,
    day: date,
    success: bool,
    total_items: int | None,
    rows: Sequence[Mapping[str, str]],
    error_message: str = "",
    traceback_text: str = "",
) -> str:
    status_text = "Calisti" if success else "Calismadi"
    status_color = "#166534" if success else "#991b1b"
    summary_rows = "".join(
        f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('department', '-'))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('status', '-'))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('hit_count', '0'))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('recipients', '-'))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('subject', '-'))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('titles', '-'))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{_escape(r.get('error', '-'))}</td>
        </tr>
        """
        for r in rows
    )

    total_items_text = str(total_items) if total_items is not None else "-"
    error_block = ""
    if error_message:
        error_block = (
            "<h3 style='margin:14px 0 8px 0;'>Hata Ozeti</h3>"
            f"<div style='background:#fee2e2;border:1px solid #fecaca;padding:10px;color:#7f1d1d;'>{_escape(error_message)}</div>"
        )

    traceback_block = ""
    if traceback_text:
        traceback_block = (
            "<h3 style='margin:14px 0 8px 0;'>Traceback</h3>"
            f"<pre style='white-space:pre-wrap;background:#111827;color:#e5e7eb;padding:10px;border-radius:6px;'>{_escape(traceback_text)}</pre>"
        )

    return f"""
    <div style="font-family:Arial, sans-serif; max-width:1000px;">
      <h2 style="margin:0 0 12px 0;">Regulation Monitor - Admin Durum Bildirimi</h2>
      <div style="margin-bottom:12px;">
        Tarih: <b>{day:%d.%m.%Y}</b><br/>
        Durum: <b style="color:{status_color};">{status_text}</b><br/>
        Toplam fihrist kaydi: <b>{total_items_text}</b>
      </div>

      <table style="width:100%; border-collapse:collapse; border:1px solid #eee;">
        <thead>
          <tr style="background:#f8fafc;">
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Departman</th>
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Mail Durumu</th>
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Hit</th>
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Alicilar</th>
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Konu</th>
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Ilgili Basliklar</th>
            <th style="padding:8px;border-bottom:1px solid #eee;text-align:left;">Hata</th>
          </tr>
        </thead>
        <tbody>
          {summary_rows if summary_rows else "<tr><td colspan='7' style='padding:8px;'>Departman raporu yok.</td></tr>"}
        </tbody>
      </table>

      {error_block}
      {traceback_block}
    </div>
    """


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
