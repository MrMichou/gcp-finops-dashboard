"""Domain models shared across the dashboard.

These dataclasses are the contract between the data sources (BigQuery, Budgets
API) and the consumers (terminal rendering, exporters). Keeping them free of any
GCP types means the rendering/export layers stay testable without credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ServiceCost:
    """Net cost for a single GCP service over the reporting window."""

    service: str
    net_cost: float
    currency: str


@dataclass(frozen=True)
class ProjectCost:
    """Net cost for a single project over the reporting window."""

    project_id: str
    project_name: str
    net_cost: float
    currency: str


@dataclass(frozen=True)
class TrendPoint:
    """Net cost for one invoice month (``YYYYMM``)."""

    invoice_month: str
    net_cost: float
    currency: str


@dataclass(frozen=True)
class BudgetInfo:
    """A configured Cloud Billing budget.

    The Budgets API returns budget *configuration* (amount + threshold rules),
    not live spend. ``spent`` is therefore optional and only populated when a
    follow-up wires the BigQuery totals into the budget comparison.
    """

    name: str
    amount: float | None
    currency: str
    thresholds: list[float] = field(default_factory=list)
    spent: float | None = None

    @property
    def percent_used(self) -> float | None:
        if self.amount and self.amount > 0 and self.spent is not None:
            return self.spent / self.amount * 100.0
        return None


@dataclass
class DashboardData:
    """Everything needed to render or export a dashboard run."""

    billing_account_id: str | None = None
    bq_table: str | None = None
    time_range_days: int = 30
    project_scope: list[str] = field(default_factory=list)
    service_costs: list[ServiceCost] = field(default_factory=list)
    project_costs: list[ProjectCost] = field(default_factory=list)
    trend: list[TrendPoint] = field(default_factory=list)
    budgets: list[BudgetInfo] = field(default_factory=list)

    @property
    def currency(self) -> str:
        """Best-effort currency for headline totals."""
        for collection in (self.service_costs, self.project_costs, self.trend):
            if collection:
                return collection[0].currency
        return "USD"

    @property
    def total_cost(self) -> float:
        return sum(s.net_cost for s in self.service_costs)


@runtime_checkable
class CostSource(Protocol):
    """Interface implemented by cost backends (e.g. BigQuery).

    Defined as a Protocol so alternative sources can be dropped in without the
    orchestrator depending on a concrete class.
    """

    def get_service_costs(self) -> list[ServiceCost]: ...

    def get_project_costs(self) -> list[ProjectCost]: ...

    def get_trend(self) -> list[TrendPoint]: ...
