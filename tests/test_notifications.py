"""Slack summary payload and webhook posting — offline (urlopen mocked)."""

from __future__ import annotations

import json
from contextlib import contextmanager

from gcp_finops_dashboard import notifications
from gcp_finops_dashboard.models import BudgetInfo, DashboardData, ServiceCost
from gcp_finops_dashboard.notifications import build_slack_payload, send_slack_summary
from gcp_finops_dashboard.sample_data import sample_dashboard


def test_payload_summarises_total_and_top_services():
    payload = build_slack_payload(sample_dashboard())
    assert payload["blocks"][0]["type"] == "header"
    text = payload["blocks"][1]["text"]["text"]
    assert "Total cost" in text
    assert "Compute Engine" in text
    # Only the top N services are listed.
    assert text.count("•") <= 5 + 10  # services + alerts/findings lines


def test_payload_flags_budget_alerts_sorted():
    data = DashboardData(
        service_costs=[ServiceCost("Compute Engine", 100.0, "USD")],
        budgets=[
            BudgetInfo("Under", 1000.0, "USD", spent=100.0),  # 10% -> no alert
            BudgetInfo("Near", 100.0, "USD", spent=85.0),  # 85%
            BudgetInfo("Over", 100.0, "USD", spent=130.0),  # 130%
        ],
    )
    text = build_slack_payload(data)["blocks"][1]["text"]["text"]
    assert "Budget alerts" in text
    # Worst budget appears before the milder one.
    assert text.index("Over") < text.index("Near")
    assert "Under" not in text


def test_payload_mentions_findings_count():
    text = build_slack_payload(sample_dashboard())["blocks"][1]["text"]["text"]
    assert "finding(s)" in text


def test_send_posts_json_to_webhook(monkeypatch):
    captured: dict = {}

    @contextmanager
    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["content_type"] = request.headers.get("Content-type")

        class _Resp:
            def read(self_inner):
                return b"ok"

        yield _Resp()

    monkeypatch.setattr(notifications.urllib.request, "urlopen", fake_urlopen)

    send_slack_summary("https://hooks.slack.com/services/T/B/X", sample_dashboard())

    assert captured["url"].startswith("https://hooks.slack.com/")
    assert captured["content_type"] == "application/json"
    assert "blocks" in captured["body"]
