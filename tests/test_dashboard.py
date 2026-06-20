"""End-to-end: dry-run pipeline, rendering smoke test, bar-chart helper."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from gcp_finops_dashboard import visualize
from gcp_finops_dashboard.config import Config, ConfigError
from gcp_finops_dashboard.dashboard import build_dashboard
from gcp_finops_dashboard.models import BudgetInfo, ServiceCost, TrendPoint
from gcp_finops_dashboard.sample_data import sample_dashboard


class _FakeCostSource:
    """Stands in for BigQueryCostSource; records its constructor kwargs."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_service_costs(self):
        return [ServiceCost("Compute Engine", 10.0, "USD")]

    def get_project_costs(self):
        return []

    def get_trend(self):
        return [TrendPoint("202601", 10.0, "USD")]


def _patch_cost_source(monkeypatch):
    """Replace the real BigQuery cost source + its auth client factory."""
    from gcp_finops_dashboard import auth, bigquery_client

    monkeypatch.setattr(bigquery_client, "BigQueryCostSource", _FakeCostSource)
    captured = {}
    monkeypatch.setattr(
        auth, "make_bigquery_client", lambda p: captured.setdefault("billing_project", p)
    )
    return captured


def test_dry_run_returns_sample_data():
    data = build_dashboard(Config(dry_run=True))
    assert data.service_costs
    assert data.total_cost > 0


def test_missing_table_without_dry_run_raises():
    with pytest.raises(ConfigError):
        build_dashboard(Config(dry_run=False, bq_table=None))


def test_build_dashboard_wires_cost_source(monkeypatch):
    captured = _patch_cost_source(monkeypatch)
    data = build_dashboard(
        Config(bq_table="proj.ds.tbl", projects=["p1"], trend=True)
    )
    assert data.service_costs[0].service == "Compute Engine"
    assert data.trend  # populated only because trend=True
    # effective_billing_project falls back to the table's project component.
    assert captured["billing_project"] == "proj"


def test_build_dashboard_skips_trend_when_disabled(monkeypatch):
    _patch_cost_source(monkeypatch)
    data = build_dashboard(Config(bq_table="proj.ds.tbl", projects=["p1"], trend=False))
    assert data.trend == []


def test_build_dashboard_fetches_budgets_with_billing_account(monkeypatch):
    _patch_cost_source(monkeypatch)
    from gcp_finops_dashboard import auth, budgets as budgets_mod

    class _FakeBudgetSource:
        def __init__(self, client, account_id):
            self.account_id = account_id

        def get_budgets(self):
            return [BudgetInfo("Org", 100.0, "USD", [], spent=10.0)]

    monkeypatch.setattr(auth, "make_budgets_client", lambda: "budget-client")
    monkeypatch.setattr(budgets_mod, "BudgetSource", _FakeBudgetSource)

    data = build_dashboard(
        Config(bq_table="proj.ds.tbl", projects=["p1"], billing_account_id="ACC")
    )
    assert [b.name for b in data.budgets] == ["Org"]


def test_build_dashboard_discovers_projects_when_no_explicit_list(monkeypatch):
    _patch_cost_source(monkeypatch)
    from gcp_finops_dashboard import auth, budgets as budgets_mod, projects

    seen = {}
    monkeypatch.setattr(auth, "make_billing_client", lambda: seen.setdefault("billing", "C"))
    monkeypatch.setattr(
        projects,
        "resolve_project_scope",
        lambda proj, client, account: (seen.update(client=client) or ["discovered"]),
    )
    monkeypatch.setattr(auth, "make_budgets_client", lambda: "bc")
    monkeypatch.setattr(
        budgets_mod, "BudgetSource", lambda client, account: type("B", (), {"get_budgets": lambda s: []})()
    )

    data = build_dashboard(Config(bq_table="proj.ds.tbl", billing_account_id="ACC"))
    # A billing client is created and handed to project discovery.
    assert seen["billing"] == "C"
    assert seen["client"] == "C"
    assert data.project_scope == ["discovered"]


def test_build_dashboard_audit_with_empty_scope_returns_no_findings(monkeypatch):
    _patch_cost_source(monkeypatch)
    # No projects and no billing account -> empty scope -> audit yields nothing,
    # and crucially never builds audit clients (which would need credentials).
    data = build_dashboard(Config(bq_table="proj.ds.tbl", audit=True))
    assert data.findings == []


def test_build_dashboard_audit_builds_clients_for_scope(monkeypatch):
    _patch_cost_source(monkeypatch)
    from gcp_finops_dashboard import auth

    # Stub every audit client factory; None clients are skipped by run_audit,
    # so this exercises the wiring in _run_audit without needing credentials.
    for factory in (
        "make_compute_instances_client",
        "make_compute_disks_client",
        "make_compute_addresses_client",
        "make_functions_client",
    ):
        monkeypatch.setattr(auth, factory, lambda: None)
    monkeypatch.setattr(auth, "make_storage_client", lambda p: None)

    data = build_dashboard(Config(bq_table="proj.ds.tbl", projects=["p1"], audit=True))
    assert data.findings == []


def test_render_smoke():
    console = Console(file=StringIO(), width=120)
    visualize.render(sample_dashboard(), console=console, show_trend=True)
    output = console.file.getvalue()
    assert "Cost by Service" in output
    assert "Compute Engine" in output
    assert "Budgets" in output
    assert "Trend" in output
    assert "Resource Audit" in output


def test_bar_helper_scaling():
    assert visualize._bar(0, 100) == ""
    assert visualize._bar(100, 100) == visualize._BLOCK * visualize._BAR_WIDTH
    assert 0 < len(visualize._bar(50, 100)) <= visualize._BAR_WIDTH
    # A tiny non-zero value still renders at least one block.
    assert len(visualize._bar(1, 1_000_000)) == 1
