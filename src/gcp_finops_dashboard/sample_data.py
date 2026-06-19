"""Bundled sample data for ``--dry-run`` and tests.

Lets the full pipeline (render + export) run without any GCP credentials.
"""

from __future__ import annotations

from gcp_finops_dashboard.models import (
    BudgetInfo,
    DashboardData,
    ProjectCost,
    ServiceCost,
    TrendPoint,
)


def sample_dashboard() -> DashboardData:
    """Return a realistic, fully-populated :class:`DashboardData`."""
    return DashboardData(
        billing_account_id="01ABCD-23EFGH-456789",
        bq_table="demo-proj.billing_export.gcp_billing_export_v1_sample",
        time_range_days=30,
        project_scope=["prod-app", "data-platform", "sandbox"],
        service_costs=[
            ServiceCost("Compute Engine", 4231.55, "USD"),
            ServiceCost("BigQuery", 1820.10, "USD"),
            ServiceCost("Cloud Storage", 642.30, "USD"),
            ServiceCost("Cloud SQL", 511.88, "USD"),
            ServiceCost("Networking", 298.04, "USD"),
            ServiceCost("Cloud Functions", 73.22, "USD"),
        ],
        project_costs=[
            ProjectCost("prod-app", "Production App", 5120.44, "USD"),
            ProjectCost("data-platform", "Data Platform", 2103.91, "USD"),
            ProjectCost("sandbox", "Sandbox", 352.74, "USD"),
        ],
        trend=[
            TrendPoint("202601", 6890.12, "USD"),
            TrendPoint("202602", 7012.55, "USD"),
            TrendPoint("202603", 6644.30, "USD"),
            TrendPoint("202604", 7333.18, "USD"),
            TrendPoint("202605", 7901.44, "USD"),
            TrendPoint("202606", 7577.09, "USD"),
        ],
        budgets=[
            BudgetInfo("Monthly Org Budget", 8000.0, "USD", [0.5, 0.9, 1.0], spent=7577.09),
            BudgetInfo("Data Platform Cap", 2500.0, "USD", [0.8, 1.0], spent=2103.91),
        ],
    )
