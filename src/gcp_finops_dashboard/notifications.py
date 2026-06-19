"""Slack notifications — post a run summary to an incoming webhook.

Uses the standard library (``urllib``) so no extra dependency is required. The
message body is built by a pure function (:func:`build_slack_payload`) that is
unit-tested offline; only :func:`send_slack_summary` touches the network.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from gcp_finops_dashboard.models import DashboardData

_TOP_SERVICES = 5


def _money(value: float, currency: str) -> str:
    return f"{value:,.2f} {currency}"


def _budget_alerts(data: DashboardData) -> list[str]:
    """Budgets at or above 80% utilisation, worst first."""
    alerts: list[tuple[float, str]] = []
    for budget in data.budgets:
        pct = budget.percent_used
        if pct is not None and pct >= 80.0:
            alerts.append((pct, f"{budget.name}: {pct:.0f}% used"))
    alerts.sort(reverse=True)
    return [text for _pct, text in alerts]


def build_slack_payload(data: DashboardData) -> dict[str, Any]:
    """Build the Slack message payload (Block Kit) summarising a run."""
    currency = data.currency
    lines = [f"*Total cost (last {data.time_range_days} days):* {_money(data.total_cost, currency)}"]

    top = data.service_costs[:_TOP_SERVICES]
    if top:
        services = "\n".join(f"• {s.service}: {_money(s.net_cost, s.currency)}" for s in top)
        lines.append(f"*Top services:*\n{services}")

    alerts = _budget_alerts(data)
    if alerts:
        lines.append("*Budget alerts:*\n" + "\n".join(f"• {a}" for a in alerts))

    if data.findings:
        lines.append(f"*Resource audit:* {len(data.findings)} finding(s) need attention")

    text = "\n\n".join(lines)
    return {
        "text": f"GCP FinOps Dashboard — {_money(data.total_cost, currency)} total",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "GCP FinOps Dashboard"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ],
    }


def send_slack_summary(webhook_url: str, data: DashboardData, timeout: float = 10.0) -> None:
    """POST the run summary to a Slack incoming webhook.

    Raises on transport/HTTP failure; callers decide whether that should abort
    the run (the CLI logs it and keeps going).
    """
    payload = json.dumps(build_slack_payload(data)).encode("utf-8")
    request = urllib.request.Request(
        webhook_url, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-supplied webhook
        response.read()
