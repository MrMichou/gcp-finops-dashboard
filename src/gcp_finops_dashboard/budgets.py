"""Budget data source backed by the Cloud Billing Budgets API.

The API returns budget *configuration* (display name, amount, threshold rules),
not live spend. We surface that config; live-spend comparison is a documented
follow-up that joins BigQuery totals onto these budgets.
"""

from __future__ import annotations

from typing import Any

from gcp_finops_dashboard.models import BudgetInfo

_DEFAULT_CURRENCY = "USD"


def _parent(billing_account_id: str) -> str:
    """Normalise a billing account ID to the API's parent resource name."""
    if billing_account_id.startswith("billingAccounts/"):
        return billing_account_id
    return f"billingAccounts/{billing_account_id}"


def _amount_and_currency(budget: Any) -> tuple[float | None, str]:
    """Extract a comparable amount and currency from a Budget proto.

    A budget is either a fixed ``specified_amount`` or a ``last_period_amount``
    (track previous period). Only the former exposes a number.
    """
    amount_field = getattr(budget, "amount", None)
    if amount_field is None:
        return None, _DEFAULT_CURRENCY

    specified = getattr(amount_field, "specified_amount", None)
    if specified is not None and getattr(specified, "currency_code", None):
        units = getattr(specified, "units", 0) or 0
        nanos = getattr(specified, "nanos", 0) or 0
        value = float(units) + float(nanos) / 1e9
        return value, specified.currency_code or _DEFAULT_CURRENCY
    return None, _DEFAULT_CURRENCY


def _thresholds(budget: Any) -> list[float]:
    rules = getattr(budget, "threshold_rules", None) or []
    return [float(getattr(rule, "threshold_percent", 0.0)) for rule in rules]


class BudgetSource:
    """Lists budgets for a billing account and maps them to :class:`BudgetInfo`."""

    def __init__(self, client: Any, billing_account_id: str) -> None:
        self.client = client
        self.parent = _parent(billing_account_id)

    def get_budgets(self) -> list[BudgetInfo]:
        budgets: list[BudgetInfo] = []
        for budget in self.client.list_budgets(parent=self.parent):
            amount, currency = _amount_and_currency(budget)
            budgets.append(
                BudgetInfo(
                    name=getattr(budget, "display_name", "") or "(unnamed)",
                    amount=amount,
                    currency=currency,
                    thresholds=_thresholds(budget),
                )
            )
        return budgets
