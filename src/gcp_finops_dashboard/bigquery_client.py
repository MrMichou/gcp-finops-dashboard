"""Cost data source backed by the BigQuery Cloud Billing export.

Implements the :class:`~gcp_finops_dashboard.models.CostSource` protocol. The
BigQuery client is injected so tests can supply a mock without credentials.
"""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery

from gcp_finops_dashboard import queries
from gcp_finops_dashboard.models import ProjectCost, ServiceCost, TrendPoint

_DEFAULT_CURRENCY = "USD"


def _f(value: Any) -> float:
    """Coerce a possibly-``None`` numeric row value to float."""
    return float(value) if value is not None else 0.0


class BigQueryCostSource:
    """Runs the billing-export queries and maps rows to domain models."""

    def __init__(
        self,
        client: bigquery.Client,
        table: str,
        time_range_days: int = 30,
        trend_months: int = 6,
        project_ids: list[str] | None = None,
        currency_override: str | None = None,
    ) -> None:
        # Validate eagerly so a bad table fails before any query runs.
        self.table = queries.validate_table(table)
        self.client = client
        self.time_range_days = time_range_days
        self.trend_months = trend_months
        self.project_ids = project_ids or None
        self.currency_override = currency_override

    def _run(self, sql: str, params: list) -> list:
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return list(self.client.query(sql, job_config=job_config).result())

    def _currency(self, row: Any) -> str:
        return self.currency_override or getattr(row, "currency", None) or _DEFAULT_CURRENCY

    def get_service_costs(self) -> list[ServiceCost]:
        sql, params = queries.service_cost_query(
            self.table, self.time_range_days, self.project_ids
        )
        return [
            ServiceCost(
                service=row.service or "(unknown)",
                net_cost=_f(row.net_cost),
                currency=self._currency(row),
            )
            for row in self._run(sql, params)
        ]

    def get_project_costs(self) -> list[ProjectCost]:
        sql, params = queries.project_cost_query(
            self.table, self.time_range_days, self.project_ids
        )
        return [
            ProjectCost(
                project_id=row.project_id or "(unknown)",
                project_name=getattr(row, "project_name", None) or "",
                net_cost=_f(row.net_cost),
                currency=self._currency(row),
            )
            for row in self._run(sql, params)
        ]

    def get_trend(self) -> list[TrendPoint]:
        sql, params = queries.trend_query(
            self.table, self.trend_months, self.project_ids
        )
        return [
            TrendPoint(
                invoice_month=row.invoice_month,
                net_cost=_f(row.net_cost),
                currency=self._currency(row),
            )
            for row in self._run(sql, params)
        ]
