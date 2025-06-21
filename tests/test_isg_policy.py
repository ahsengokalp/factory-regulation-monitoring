from core.models import GazetteItem
from policies.isg import IsgPolicy


def test_isg_policy_marks_relevant_item() -> None:
    policy = IsgPolicy(min_score=2.0)
    item = GazetteItem(
        item_id="1",
        title="Is Sagligi ve Guvenligi Yonetmeligi",
        url="https://example.com/item-1",
    )

    result = policy.evaluate(item)

    assert result.is_relevant is True
    assert result.score >= 2.0
    assert "is sagligi" in result.matched_keywords or "is guvenligi" in result.matched_keywords


def test_isg_policy_marks_irrelevant_item() -> None:
    policy = IsgPolicy(min_score=2.0)
    item = GazetteItem(
        item_id="2",
        title="Turk Ceza Kanunu Degisikligi",
        url="https://example.com/item-2",
    )

    result = policy.evaluate(item)

    assert result.is_relevant is False
    assert result.score < 2.0
