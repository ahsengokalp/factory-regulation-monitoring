from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import sys
from time import perf_counter
import traceback
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

# Ensure project root is importable when Streamlit runs file-path entrypoints.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.config import get_settings
from src.core.http import build_session
from src.core.models import GazetteItem
from src.gazette.client import daily_index_url, fetch_daily_html
from src.gazette.parser import parse_daily_items
from src.notify.emailer import send_html_email
from src.notify.templates import build_generic_email_html, build_generic_email_subject
from src.pipeline.run_daily import default_policies
from src.policies.base import PolicyDecision


def _split_recipients(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value and value.strip()]


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


def _settings_preview(settings: Any) -> dict[str, Any]:
    return {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user,
        "smtp_password": _mask_secret(settings.smtp_password),
        "mail_from": settings.mail_from,
        "isg_recipients": _split_recipients(settings.isg_recipients),
        "ik_recipients": _split_recipients(settings.ik_recipients),
        "muhasebe_recipients": _split_recipients(settings.muhasebe_recipients),
        "lojistik_recipients": _split_recipients(settings.lojistik_recipients),
    }


def _item_to_row(item: GazetteItem) -> dict[str, str]:
    return {
        "title": item.title,
        "section": item.section or "",
        "subsection": item.subsection or "",
        "url": item.url,
    }


def _decision_to_row(item: GazetteItem, decision: PolicyDecision) -> dict[str, Any]:
    return {
        "title": item.title,
        "section": item.section or "",
        "subsection": item.subsection or "",
        "score": decision.score,
        "is_relevant": decision.is_relevant,
        "reasons": ", ".join(decision.reasons),
        "url": item.url,
    }


def _run_debug(day: date) -> dict[str, Any]:
    start = perf_counter()
    settings = get_settings()
    session = build_session()

    url = daily_index_url(day)
    html = fetch_daily_html(session=session, day=day)
    items = parse_daily_items(html=html, base_url=url)
    policies = default_policies()

    decisions_by_policy: dict[str, list[tuple[GazetteItem, PolicyDecision]]] = {}
    hits_by_policy: dict[str, list[tuple[GazetteItem, PolicyDecision]]] = {}
    item_hits: dict[str, list[str]] = defaultdict(list)

    for policy in policies:
        decisions: list[tuple[GazetteItem, PolicyDecision]] = []
        hits: list[tuple[GazetteItem, PolicyDecision]] = []

        for item in items:
            decision = policy.evaluate_title(item)
            decisions.append((item, decision))
            if decision.is_relevant:
                hits.append((item, decision))
                key = f"{item.title}|{item.url}"
                item_hits[key].append(policy.name)

        decisions_by_policy[policy.name] = decisions
        hits_by_policy[policy.name] = hits

    recipients_map = {
        "isg": _split_recipients(settings.isg_recipients),
        "ik": _split_recipients(settings.ik_recipients),
        "muhasebe": _split_recipients(settings.muhasebe_recipients),
        "lojistik": _split_recipients(settings.lojistik_recipients),
    }

    section_counts = Counter(item.section or "(empty)" for item in items)
    subsection_counts = Counter(item.subsection or "(empty)" for item in items)

    matrix_rows = []
    for item in items:
        key = f"{item.title}|{item.url}"
        matrix_rows.append(
            {
                "title": item.title,
                "section": item.section or "",
                "subsection": item.subsection or "",
                "matched_policies": ", ".join(sorted(item_hits.get(key, []))),
                "match_count": len(item_hits.get(key, [])),
                "url": item.url,
            }
        )

    elapsed_s = perf_counter() - start
    return {
        "day": day,
        "url": url,
        "html": html,
        "items": items,
        "settings": settings,
        "settings_preview": _settings_preview(settings),
        "section_counts": section_counts,
        "subsection_counts": subsection_counts,
        "decisions_by_policy": decisions_by_policy,
        "hits_by_policy": hits_by_policy,
        "recipients_map": recipients_map,
        "matrix_rows": matrix_rows,
        "elapsed_s": elapsed_s,
    }


def main() -> None:
    st.set_page_config(page_title="RG Debug Console", layout="wide")
    st.title("Factory Regulation Monitoring - Debug Console")
    st.caption("Fetch -> Parse -> Policy -> Email preview")

    with st.sidebar:
        run_day = st.date_input("Date", value=date.today())
        row_limit = st.slider("Table row limit", min_value=10, max_value=500, value=100, step=10)
        show_only_hits = st.checkbox("Only show relevant policy rows", value=True)
        allow_send_email = st.checkbox("Enable real email sending", value=False)
        run_clicked = st.button("Run debug", type="primary")

    if run_clicked:
        with st.spinner("Running pipeline..."):
            try:
                st.session_state["debug_result"] = _run_debug(run_day)
                st.session_state.pop("debug_error", None)
            except Exception:
                st.session_state["debug_error"] = traceback.format_exc()
                st.session_state.pop("debug_result", None)

    if "debug_error" in st.session_state:
        st.error("Pipeline failed.")
        st.code(st.session_state["debug_error"])
        return

    if "debug_result" not in st.session_state:
        st.info("Click 'Run debug' to fetch and inspect the full flow.")
        return

    result = st.session_state["debug_result"]
    items: list[GazetteItem] = result["items"]
    hits_by_policy: dict[str, list[tuple[GazetteItem, PolicyDecision]]] = result["hits_by_policy"]
    decisions_by_policy: dict[str, list[tuple[GazetteItem, PolicyDecision]]] = result["decisions_by_policy"]

    total_hits = sum(len(hits) for hits in hits_by_policy.values())

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Items", len(items))
    metric_col2.metric("Policies", len(decisions_by_policy))
    metric_col3.metric("Total Hits", total_hits)
    metric_col4.metric("Elapsed", f"{result['elapsed_s']:.2f}s")

    tab_overview, tab_items, tab_policy, tab_email, tab_html = st.tabs(
        ["Overview", "Items", "Policies", "Email Preview", "HTML"]
    )

    with tab_overview:
        st.subheader("Request")
        st.write(f"Date: `{result['day']:%Y-%m-%d}`")
        st.write(f"URL: `{result['url']}`")
        st.write(f"HTML size: `{len(result['html'])}` chars")

        st.subheader("Settings")
        st.json(result["settings_preview"])

        st.subheader("Sections")
        section_rows = [{"section": key, "count": value} for key, value in result["section_counts"].most_common()]
        subsection_rows = [
            {"subsection": key, "count": value} for key, value in result["subsection_counts"].most_common()
        ]
        col_left, col_right = st.columns(2)
        with col_left:
            st.dataframe(section_rows[:row_limit], use_container_width=True, hide_index=True)
        with col_right:
            st.dataframe(subsection_rows[:row_limit], use_container_width=True, hide_index=True)

        st.subheader("Cross Policy Matrix")
        matrix_sorted = sorted(result["matrix_rows"], key=lambda row: row["match_count"], reverse=True)
        st.dataframe(matrix_sorted[:row_limit], use_container_width=True, hide_index=True)

    with tab_items:
        item_rows = [_item_to_row(item) for item in items]
        st.dataframe(item_rows[:row_limit], use_container_width=True, hide_index=True)
        if len(item_rows) > row_limit:
            st.caption(f"Showing first {row_limit} of {len(item_rows)} items.")

    with tab_policy:
        for policy_name, decisions in decisions_by_policy.items():
            hits = hits_by_policy[policy_name]
            with st.expander(f"{policy_name.upper()} | hits: {len(hits)} / {len(decisions)}", expanded=True):
                rows_source = hits if show_only_hits else decisions
                decision_rows = [_decision_to_row(item, decision) for item, decision in rows_source]
                st.dataframe(decision_rows[:row_limit], use_container_width=True, hide_index=True)

                reason_counts = Counter(reason for _, decision in decisions for reason in decision.reasons)
                if reason_counts:
                    st.write("Top reasons")
                    reason_rows = [{"reason": reason, "count": count} for reason, count in reason_counts.most_common()]
                    st.dataframe(reason_rows[:row_limit], use_container_width=True, hide_index=True)

    with tab_email:
        recipients_map: dict[str, list[str]] = result["recipients_map"]
        mailable_departments = [name for name, hits in hits_by_policy.items() if hits]

        if not mailable_departments:
            st.info("No hits found, no email payload to preview.")
        else:
            for dept in mailable_departments:
                hits = hits_by_policy[dept]
                hit_items = [item for item, _ in hits]
                recipients = recipients_map.get(dept, [])
                subject = build_generic_email_subject(dept, result["day"], len(hit_items))
                html_body = build_generic_email_html(dept, result["day"], hit_items)

                with st.expander(f"{dept.upper()} email | hits: {len(hit_items)}", expanded=False):
                    st.write(f"Recipients: {', '.join(recipients) if recipients else '(empty)'}")
                    st.code(subject)
                    components.html(html_body, height=350, scrolling=True)

            if allow_send_email:
                selected_departments = st.multiselect(
                    "Departments to send",
                    options=mailable_departments,
                    default=mailable_departments,
                )
                if st.button("Send selected emails", type="primary"):
                    sent_count = 0
                    errors: list[str] = []
                    settings = result["settings"]
                    for dept in selected_departments:
                        hits = hits_by_policy[dept]
                        recipients = recipients_map.get(dept, [])
                        if not recipients:
                            errors.append(f"{dept.upper()}: no recipients configured.")
                            continue

                        subject = build_generic_email_subject(dept, result["day"], len(hits))
                        html_body = build_generic_email_html(dept, result["day"], [item for item, _ in hits])
                        try:
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
                            sent_count += 1
                        except Exception as exc:  # pragma: no cover - manual/debug path
                            errors.append(f"{dept.upper()}: {exc}")

                    if sent_count:
                        st.success(f"Sent {sent_count} email batch(es).")
                    if errors:
                        st.error("Some emails failed:")
                        for err in errors:
                            st.write(f"- {err}")

    with tab_html:
        preview_len = st.slider(
            "HTML preview length",
            min_value=500,
            max_value=min(max(len(result["html"]), 500), 50000),
            value=min(len(result["html"]), 8000),
            step=500,
        )
        st.code(result["html"][:preview_len], language="html")


if __name__ == "__main__":
    main()
