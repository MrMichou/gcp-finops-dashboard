"""BudgetSource maps Budget protos to BudgetInfo and builds the parent name."""

from __future__ import annotations

from types import SimpleNamespace

from gcp_finops_dashboard.budgets import BudgetSource, _parent


def _fake_budget(name, units, currency, thresholds):
    return SimpleNamespace(
        display_name=name,
        amount=SimpleNamespace(
            specified_amount=SimpleNamespace(units=units, nanos=0, currency_code=currency)
        ),
        threshold_rules=[SimpleNamespace(threshold_percent=t) for t in thresholds],
    )


class FakeBudgetsClient:
    def __init__(self, budgets):
        self._budgets = budgets
        self.last_parent = None

    def list_budgets(self, parent):
        self.last_parent = parent
        return list(self._budgets)


def test_parent_normalisation():
    assert _parent("01ABCD-23EFGH") == "billingAccounts/01ABCD-23EFGH"
    assert _parent("billingAccounts/x") == "billingAccounts/x"


def test_budget_mapping():
    client = FakeBudgetsClient(
        [_fake_budget("Org Budget", 8000, "USD", [0.5, 0.9, 1.0])]
    )
    source = BudgetSource(client, "01ABCD-23EFGH-456789")
    budgets = source.get_budgets()
    assert client.last_parent == "billingAccounts/01ABCD-23EFGH-456789"
    assert budgets[0].name == "Org Budget"
    assert budgets[0].amount == 8000.0
    assert budgets[0].currency == "USD"
    assert budgets[0].thresholds == [0.5, 0.9, 1.0]


def test_budget_without_specified_amount():
    budget = SimpleNamespace(
        display_name="Last period",
        amount=SimpleNamespace(specified_amount=SimpleNamespace(units=0, nanos=0, currency_code="")),
        threshold_rules=[],
    )
    source = BudgetSource(FakeBudgetsClient([budget]), "acct")
    info = source.get_budgets()[0]
    assert info.amount is None
    assert info.thresholds == []


def test_percent_used():
    client = FakeBudgetsClient([_fake_budget("B", 100, "USD", [])])
    info = BudgetSource(client, "acct").get_budgets()[0]
    assert info.percent_used is None  # no spend wired in
