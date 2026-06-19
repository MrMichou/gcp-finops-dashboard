"""Orchestration: turn a :class:`Config` into a :class:`DashboardData`.

Wires the BigQuery cost source, the Budgets source and project discovery
together. GCP clients are created lazily (and only when not in dry-run) so the
module imports cleanly without credentials.
"""

from __future__ import annotations

from gcp_finops_dashboard.config import Config, ConfigError
from gcp_finops_dashboard.models import DashboardData


def build_dashboard(config: Config) -> DashboardData:
    """Gather all data described by ``config`` into a single object."""
    if config.dry_run:
        from gcp_finops_dashboard.sample_data import sample_dashboard

        return sample_dashboard()

    if not config.bq_table:
        raise ConfigError(
            "A BigQuery billing export table is required. "
            "Set --bq-table or 'bq_table' in your config file (or use --dry-run)."
        )

    # Imported here so the module stays importable without GCP libs/creds.
    from gcp_finops_dashboard import auth, projects
    from gcp_finops_dashboard.bigquery_client import BigQueryCostSource
    from gcp_finops_dashboard.budgets import BudgetSource

    # Resolve project scope (explicit list, else all projects on the account).
    billing_client = None
    if not config.projects and config.billing_account_id:
        billing_client = auth.make_billing_client()
    project_scope = projects.resolve_project_scope(
        config.projects, billing_client, config.billing_account_id
    )

    bq_client = auth.make_bigquery_client(config.effective_billing_project)
    cost_source = BigQueryCostSource(
        client=bq_client,
        table=config.bq_table,
        time_range_days=config.time_range_days,
        trend_months=config.trend_months,
        project_ids=project_scope or None,
        currency_override=config.currency,
    )

    data = DashboardData(
        billing_account_id=config.billing_account_id,
        bq_table=config.bq_table,
        time_range_days=config.time_range_days,
        project_scope=project_scope,
        service_costs=cost_source.get_service_costs(),
        project_costs=cost_source.get_project_costs(),
        trend=cost_source.get_trend() if config.trend else [],
    )

    if config.billing_account_id:
        budget_source = BudgetSource(auth.make_budgets_client(), config.billing_account_id)
        data.budgets = budget_source.get_budgets()

    return data
