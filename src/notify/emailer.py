from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable


def send_html_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_secure: bool = True,
    smtp_auth: bool = True,
    smtp_tls_reject_unauthorized: bool = True,
    smtp_enabled: bool = True,
    mail_from: str,
    recipients: Iterable[str],
    subject: str,
    html_body: str,
) -> None:
    if not smtp_enabled:
        return

    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        raise ValueError("No recipients provided")

    msg = MIMEMultipart("alternative")
    msg["From"] = mail_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if smtp_secure:
            if smtp_tls_reject_unauthorized:
                context = ssl.create_default_context()
            else:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            server.starttls(context=context)

        if smtp_auth:
            server.login(smtp_user, smtp_password)

        server.sendmail(mail_from, recipients, msg.as_string())
