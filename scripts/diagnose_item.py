#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date

from src.app.config import get_settings
from src.core.http import build_session
from src.gazette.client import daily_index_url, fetch_daily_html
from src.gazette.detail_text import fetch_detail_text
from src.gazette.parser import parse_daily_items
from src.pipeline.run_daily import decide_candidate
from src.policies.negative_filter import apply_negative_rules
from src.policies.factory_signals import has_factory_override
from src.policies.utils import build_haystack
from src.llm.ollama_client import OllamaClient


def find_item(items, match):
    for it in items:
        if match in it.url or match in it.title:
            return it
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=False, help="YYYY-MM-DD (default: today)")
    p.add_argument("--match", required=True, help="Substring to match in title or url")
    args = p.parse_args()

    if args.date:
        day = date.fromisoformat(args.date)
    else:
        day = date.today()

    settings = get_settings()
    session = build_session()

    html = fetch_daily_html(session=session, day=day)
    items = parse_daily_items(html=html, base_url=daily_index_url(day))

    it = find_item(items, args.match)
    if not it:
        print("No item matched the given substring.")
        return

    print("FOUND ITEM:")
    print(f"title: {it.title}")
    print(f"url: {it.url}")
    print(f"section: {it.section}")
    print(f"subsection: {it.subsection}")

    # Candidate decision
    cand = decide_candidate(it)
    print("\nCANDIDATE_DECISION:")
    print(cand)

    # Haystack and negative rules
    haystack = build_haystack(it)
    neg_penalty, neg_reasons, hard_excluded = apply_negative_rules(haystack)
    override = has_factory_override(haystack)
    print('\nHAYSTACK:')
    print(haystack)
    print('\nNEGATIVE_RULES:')
    print('penalty=', neg_penalty)
    print('reasons=', neg_reasons)
    print('hard_excluded=', hard_excluded)
    print('override_factory=', override)

    # Fetch detail text
    try:
        text = fetch_detail_text(session, it.url) or ""
    except Exception as exc:
        print('\nFailed to fetch detail text:', exc)
        text = ""

    print(f"\nDETAIL_TEXT_LEN: {len(text)}")
    print('TEXT_HEAD:', text[:500].replace('\n', ' '))

    # Call LLM classify_multi
    try:
        ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        md = ollama.classify_multi(title=it.title, url=it.url, text=text[:2500])
        print('\nLLM MULTI DECISION:')
        print('raw:', md.raw)
        print('isg:', md.isg, 'ik:', md.ik, 'muhasebe:', md.muhasebe, 'lojistik:', md.lojistik)
        print('confidence:', md.confidence)
        print('evidence:', md.evidence)
    except Exception as exc:
        print('\nLLM classify failed:', exc)


if __name__ == '__main__':
    main()
