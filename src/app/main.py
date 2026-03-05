from __future__ import annotations

import argparse
from datetime import date, datetime
import traceback

from src.app.config import get_settings
from src.notify.emailer import send_html_email
from src.notify.templates import build_admin_status_email_html, build_admin_status_email_subject
from src.pipeline.run_daily import RunReport, default_policies, run


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=False, help="YYYY-MM-DD (default: today)")
    return p.parse_args()


def _split_recipients(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value and value.strip()]


def _send_admin_status_email(
    *,
    day: date,
    report: RunReport | None,
    run_error: Exception | None,
    traceback_text: str = "",
) -> None:
    settings = get_settings()
    if not settings.admin_mail_enabled:
        print("[INFO] ADMIN_MAIL_ENABLED is false. Admin status email skipped.")
        return

    recipients = _split_recipients(settings.admin_recipients)
    if not recipients:
        print("[WARN] ADMIN_RECIPIENTS is empty. Admin status email skipped.")
        return

    rows: list[dict[str, str]] = []
    total_items: int | None = None
    if report is not None:
        total_items = report.total_items
        for result in report.department_results:
            rows.append(
                {
                    "department": result.department.upper(),
                    "status": result.status,
                    "hit_count": str(result.hit_count),
                    "recipients": ", ".join(result.recipients) if result.recipients else "-",
                    "subject": result.subject or "-",
                    "titles": " | ".join(result.sample_titles) if result.sample_titles else "-",
                    "error": result.error or "-",
                }
            )

    success = run_error is None
    subject = build_admin_status_email_subject(day=day, success=success)
    html_body = build_admin_status_email_html(
        day=day,
        success=success,
        total_items=total_items,
        rows=rows,
        error_message=str(run_error) if run_error else "",
        traceback_text=traceback_text if run_error else "",
    )

    send_html_email(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        smtp_secure=settings.smtp_secure,
        smtp_auth=settings.smtp_auth,
        smtp_tls_reject_unauthorized=settings.smtp_tls_reject_unauthorized,
        smtp_enabled=settings.smtp_enabled,
        mail_from=settings.mail_from,
        recipients=recipients,
        subject=subject,
        html_body=html_body,
    )
    print(f"[INFO] ADMIN: status email sent to {', '.join(recipients)}")


def main() -> None:
    args = parse_args()
    if args.date:
        day = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        day = date.today()

    report: RunReport | None = None
    run_error: Exception | None = None
    traceback_text = ""

    try:
        report = run(day=day, policies=default_policies())
    except Exception as exc:
        run_error = exc
        traceback_text = traceback.format_exc()
        print(traceback_text)
    finally:
        try:
            _send_admin_status_email(
                day=day,
                report=report,
                run_error=run_error,
                traceback_text=traceback_text,
            )
        except Exception as admin_exc:
            print(f"[ERROR] ADMIN: status email failed -> {admin_exc}")

    if run_error is not None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
