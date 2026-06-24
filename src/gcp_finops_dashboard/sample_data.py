"""Bundled sample data for ``--dry-run`` and tests.

Lets the full pipeline (render + export) run without any GCP credentials.
"""

from __future__ import annotations

from gcp_finops_dashboard.models import (
    BudgetInfo,
    DashboardData,
    ProjectCost,
    ResourceFinding,
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
        findings=[
            ResourceFinding(
                resource_type="compute_instance",
                name="legacy-batch-runner",
                project_id="sandbox",
                location="us-central1-a",
                issue="stopped",
                detail="Instance is TERMINATED but still reserves disks/IPs that may bill.",
                estimated_monthly_cost=18.40,
            ),
            ResourceFinding(
                resource_type="persistent_disk",
                name="orphaned-data-disk",
                project_id="data-platform",
                location="us-central1-a",
                issue="unattached",
                detail="Disk is not attached to any instance (200 GB) but still bills.",
                estimated_monthly_cost=8.00,
            ),
            ResourceFinding(
                resource_type="static_ip",
                name="old-lb-ip",
                project_id="prod-app",
                location="us-central1",
                issue="idle",
                detail="Static IP is RESERVED but not in use; reserved unused IPs bill.",
                estimated_monthly_cost=7.30,
            ),
            ResourceFinding(
                resource_type="gcs_bucket",
                name="prod-app-uploads",
                project_id="prod-app",
                location="US",
                issue="no_lifecycle",
                detail="Bucket has no lifecycle rules; old objects accumulate cost.",
            ),
            ResourceFinding(
                resource_type="cloud_function",
                name="webhook-handler",
                project_id="sandbox",
                location="",
                issue="untagged",
                detail="Missing required label(s): team, env.",
            ),
            ResourceFinding(
                resource_type="cloud_sql_instance",
                name="legacy-reporting-db",
                project_id="data-platform",
                location="us-central1",
                issue="stopped",
                detail="Cloud SQL instance is stopped but still bills for provisioned storage.",
                estimated_monthly_cost=42.50,
            ),
        ],
    )
