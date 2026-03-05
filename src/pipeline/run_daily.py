from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from time import sleep
from typing import Dict, List, Tuple

from src.app.config import get_settings
from src.core.http import build_session
from src.core.models import GazetteItem
from src.gazette.client import daily_index_url, fetch_daily_html
from src.gazette.detail_text import fetch_detail_text
from src.gazette.parser import parse_daily_items
from src.llm.ollama_client import MultiDeptDecision, OllamaClient
from src.notify.emailer import send_html_email
from src.notify.templates import build_generic_email_html, build_generic_email_subject
from src.policies.base import DepartmentPolicy, PolicyDecision
from src.policies.common_negative_rules import NEGATIVE_RULES
from src.policies.factory_signals import has_factory_override
from src.policies.ik import IkPolicy
from src.policies.isg import IsgPolicy
from src.policies.lojistik import LojistikPolicy
from src.policies.muhasebe import MuhasebePolicy
from src.policies.negative_filter import apply_negative_rules
from src.policies.utils import build_haystack, is_excluded_section, is_ilan_url, contains_financial_keywords

REQUEST_DELAY_SECONDS = 0.35


@dataclass(frozen=True)
class CandidateDecision:
    """
    Decide whether an item should go to LLM or should be skipped.
    """

    status: str  # "SKIP_ILAN" | "SKIP_NEG_HARD" | "CANDIDATE_LLM"
    neg_penalty: int = 0
    neg_reasons: Tuple[str, ...] = ()
    override_factory: bool = False


@dataclass(frozen=True)
class PolicyHit:
    item: GazetteItem
    decision: PolicyDecision
    llm: MultiDeptDecision


@dataclass(frozen=True)
class DepartmentMailResult:
    department: str
    hit_count: int
    recipients: Tuple[str, ...]
    subject: str
    status: str  # sent | failed | skipped_no_hits | skipped_no_recipients
    sample_titles: Tuple[str, ...] = ()
    error: str = ""


@dataclass(frozen=True)
class RunReport:
    day: date
    total_items: int
    hit_counts: Dict[str, int]
    department_results: Tuple[DepartmentMailResult, ...]


def decide_candidate(item: GazetteItem) -> CandidateDecision:
    # 1) If section is ilan, skip directly.
    if is_excluded_section(item):
        return CandidateDecision(status="SKIP_ILAN")

    haystack = build_haystack(item)

    # 2) Negative rules.
    neg_penalty, neg_reasons, hard_excluded = apply_negative_rules(haystack, NEGATIVE_RULES)
    override = has_factory_override(haystack)

    # 3) Hard negative and no override means skip.
    if hard_excluded and not override:
        return CandidateDecision(
            status="SKIP_NEG_HARD",
            neg_penalty=neg_penalty,
            neg_reasons=tuple(neg_reasons),
            override_factory=False,
        )

    # 4) Remaining records are LLM candidates.
    return CandidateDecision(
        status="CANDIDATE_LLM",
        neg_penalty=neg_penalty,
        neg_reasons=tuple(neg_reasons),
        override_factory=override,
    )


def collect_daily_hits(
    day: date,
    policies: List[DepartmentPolicy],
) -> Tuple[List[GazetteItem], Dict[str, CandidateDecision], Dict[str, List[PolicyHit]]]:
    session = build_session()

    html = fetch_daily_html(session=session, day=day)
    items = parse_daily_items(html=html, base_url=daily_index_url(day))

    candidate_map: Dict[str, CandidateDecision] = {}
    for it in items:
        candidate_map[it.url] = decide_candidate(it)

    settings = get_settings()
    ollama = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )

    policy_map: Dict[str, DepartmentPolicy] = {pol.name: pol for pol in policies}

    text_cache: Dict[str, str] = {}
    llm_cache: Dict[str, MultiDeptDecision] = {}
    printed_debug: set[str] = set()
    hits_by_policy: Dict[str, List[PolicyHit]] = {pol.name: [] for pol in policies}

    for item in items:
        if is_ilan_url(item.url):
            continue

        cand = candidate_map[item.url]
        if cand.status != "CANDIDATE_LLM":
            continue

        text = text_cache.get(item.url)
        if text is None:
            # Soft throttle to avoid hitting the source too aggressively.
            sleep(REQUEST_DELAY_SECONDS)
            try:
                text = fetch_detail_text(session, item.url)
            except Exception:
                text = ""
            text_cache[item.url] = text

        text = (text or "").strip()
        if "20250621-18" in item.url and item.url not in printed_debug:
            printed_debug.add(item.url)
            print("\n[DEBUG] TARGET ITEM:", item.title)
            print("[DEBUG] URL:", item.url)
            print("[DEBUG] TEXT_LEN:", len(text))
            print("[DEBUG] TEXT_HEAD:", text[:300].replace("\n", " "))

        # If no detail text, allow proceeding for financial-like titles
        if not text and not contains_financial_keywords(build_haystack(item)):
            continue

        md = llm_cache.get(item.url)
        if md is None:
            try:
                md = ollama.classify_multi(title=item.title, url=item.url, text=text[:2500])
            except Exception:
                continue
            if "20250621-18" in item.url:
                print("\n[DEBUG] LLM_RAW:", md.raw)
                print("[DEBUG] LLM_PARSED:", md.isg, md.ik, md.muhasebe, md.lojistik, md.confidence)
                print("[DEBUG] LLM_EVIDENCE:", md.evidence)
            llm_cache[item.url] = md

        # Confidence gate with financial keyword handling
        haystack_local = build_haystack(item)
        is_financial_local = contains_financial_keywords(haystack_local)
        threshold_local = 20 if is_financial_local else 40
        if md.confidence < threshold_local:
            continue

        if md.isg and "isg" in policy_map:
            decision = policy_map["isg"].evaluate_title(item)
            hits_by_policy["isg"].append(PolicyHit(item=item, decision=decision, llm=md))
        if md.ik and "ik" in policy_map:
            decision = policy_map["ik"].evaluate_title(item)
            hits_by_policy["ik"].append(PolicyHit(item=item, decision=decision, llm=md))
        if md.muhasebe and "muhasebe" in policy_map:
            decision = policy_map["muhasebe"].evaluate_title(item)
            hits_by_policy["muhasebe"].append(PolicyHit(item=item, decision=decision, llm=md))
        elif is_financial_local and "muhasebe" in policy_map:
            # pre-mark muhasebe for financial-like titles
            decision = policy_map["muhasebe"].evaluate_title(item)
            hits_by_policy["muhasebe"].append(PolicyHit(item=item, decision=decision, llm=md))
        if md.lojistik and "lojistik" in policy_map:
            decision = policy_map["lojistik"].evaluate_title(item)
            hits_by_policy["lojistik"].append(PolicyHit(item=item, decision=decision, llm=md))

    return items, candidate_map, hits_by_policy


def run(day: date, policies: List[DepartmentPolicy]) -> RunReport:
    _ = policies
    settings = get_settings()
    session = build_session()

    html = fetch_daily_html(session=session, day=day)
    items = parse_daily_items(html=html, base_url=daily_index_url(day))
    print(f"[INFO] items found: {len(items)}")
    # Print parsed items so they are visible in terminal output
    for it in items:
        print(f"- {it.title}")
        print(f"  {it.url}")
        if it.section:
            print(f"  section: {it.section}")
        if it.subsection:
            print(f"  subsection: {it.subsection}")

    ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model)

    hits_by_dept = defaultdict(list)  # dept -> list[(item, md)]
    text_cache = {}
    llm_cache = {}

    for item in items:
        # 1) Candidate gate
        if is_ilan_url(item.url):
            continue

        if is_excluded_section(item):
            continue

        haystack = build_haystack(item)
        _, _, hard_excluded = apply_negative_rules(haystack, NEGATIVE_RULES)
        override = has_factory_override(haystack)
        if hard_excluded and not override:
            continue

        # 2) Text cache
        text = text_cache.get(item.url)
        if text is None:
            text = fetch_detail_text(session, item.url)
            text_cache[item.url] = text
        text = (text or "").strip()

        # If no detail text (e.g., PDF), allow proceeding when title/haystack looks financial
        if not text and not contains_financial_keywords(haystack):
            continue

        # 3) LLM cache (multi-label)
        md = llm_cache.get(item.url)
        if md is None:
            md = ollama.classify_multi(title=item.title, url=item.url, text=text[:2500])
            llm_cache[item.url] = md

        # 4) Confidence gate
        # Confidence gate: lower threshold for financial-like titles
        haystack = build_haystack(item)
        is_financial = contains_financial_keywords(haystack)
        threshold = 20 if is_financial else 40
        if md.confidence < threshold:
            continue

        if md.isg:
            hits_by_dept["isg"].append((item, md))
        if md.ik:
            hits_by_dept["ik"].append((item, md))
        # Pre-mark muhasebe if title contains financial keywords even if LLM didn't
        if md.muhasebe:
            hits_by_dept["muhasebe"].append((item, md))
        elif is_financial:
            hits_by_dept["muhasebe"].append((item, md))
        if md.lojistik:
            hits_by_dept["lojistik"].append((item, md))

    recipients_map = {
        "isg": [v.strip() for v in settings.isg_recipients.split(",") if v and v.strip()],
        "ik": [v.strip() for v in settings.ik_recipients.split(",") if v and v.strip()],
        "muhasebe": [v.strip() for v in settings.muhasebe_recipients.split(",") if v and v.strip()],
        "lojistik": [v.strip() for v in settings.lojistik_recipients.split(",") if v and v.strip()],
    }
    dept_order = ("isg", "ik", "muhasebe", "lojistik")
    department_results: list[DepartmentMailResult] = []

    for dept in dept_order:
        hits = hits_by_dept.get(dept, [])
        if not hits:
            department_results.append(
                DepartmentMailResult(
                    department=dept,
                    hit_count=0,
                    recipients=(),
                    subject="",
                    status="skipped_no_hits",
                )
            )
            continue

        hit_items = [item for item, _ in hits]
        sample_titles = tuple(item.title for item in hit_items[:5])
        subject = build_generic_email_subject(dept, day, len(hit_items))
        recipients = recipients_map.get(dept, [])
        if not recipients:
            print(f"[WARN] {dept.upper()}: no recipients configured")
            department_results.append(
                DepartmentMailResult(
                    department=dept,
                    hit_count=len(hit_items),
                    recipients=(),
                    subject=subject,
                    status="skipped_no_recipients",
                    sample_titles=sample_titles,
                    error="No recipients configured",
                )
            )
            continue

        html_body = build_generic_email_html(dept, day, hit_items)

        try:
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
            print(f"[INFO] {dept.upper()}: email sent to {', '.join(recipients)}")
            department_results.append(
                DepartmentMailResult(
                    department=dept,
                    hit_count=len(hit_items),
                    recipients=tuple(recipients),
                    subject=subject,
                    status="sent",
                    sample_titles=sample_titles,
                )
            )
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"[ERROR] {dept.upper()}: email failed -> {exc}")
            department_results.append(
                DepartmentMailResult(
                    department=dept,
                    hit_count=len(hit_items),
                    recipients=tuple(recipients),
                    subject=subject,
                    status="failed",
                    sample_titles=sample_titles,
                    error=str(exc),
                )
            )

    # 5) Print results
    for dept in dept_order:
        hits = hits_by_dept.get(dept, [])
        print(f"\n=== Department: {dept} | hits: {len(hits)} ===")
        for item, md in hits[:10]:
            print(f"- ({md.confidence}) {item.title}")
            print(f"  {item.url}")
            if md.evidence:
                print(f"  evidence: {md.evidence}")

    return RunReport(
        day=day,
        total_items=len(items),
        hit_counts={dept: len(hits_by_dept.get(dept, [])) for dept in dept_order},
        department_results=tuple(department_results),
    )


def default_policies() -> List[DepartmentPolicy]:
    return [IsgPolicy(), IkPolicy(), MuhasebePolicy(), LojistikPolicy()]
