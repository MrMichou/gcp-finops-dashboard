"""Rich terminal rendering of a :class:`DashboardData`."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gcp_finops_dashboard.models import DashboardData

_BAR_WIDTH = 30
_BLOCK = "█"


def _money(value: float, currency: str) -> str:
    return f"{value:,.2f} {currency}"


def _bar(value: float, max_value: float, width: int = _BAR_WIDTH) -> str:
    """Return a block-character bar scaled to ``max_value``.

    Pure and deterministic so it can be unit-tested.
    """
    if max_value <= 0 or value <= 0:
        return ""
    filled = max(1, round(value / max_value * width))
    return _BLOCK * min(filled, width)


def _header_panel(data: DashboardData) -> Panel:
    scope = ", ".join(data.project_scope) if data.project_scope else "all projects"
    lines = [
        f"[bold]Billing account:[/bold] {data.billing_account_id or '(n/a)'}",
        f"[bold]Export table:[/bold] {data.bq_table or '(n/a)'}",
        f"[bold]Window:[/bold] last {data.time_range_days} days",
        f"[bold]Projects:[/bold] {scope}",
    ]
    return Panel("\n".join(lines), title="GCP FinOps Dashboard", expand=False)


def _service_table(data: DashboardData) -> Table:
    total = data.total_cost
    table = Table(title="Cost by Service", title_style="bold cyan")
    table.add_column("Service")
    table.add_column("Net Cost", justify="right")
    table.add_column("% of Total", justify="right")
    for item in data.service_costs:
        pct = (item.net_cost / total * 100.0) if total else 0.0
        table.add_row(item.service, _money(item.net_cost, item.currency), f"{pct:.1f}%")
    if data.service_costs:
        table.add_section()
        table.add_row("[bold]TOTAL[/bold]", f"[bold]{_money(total, data.currency)}[/bold]", "")
    return table


def _project_table(data: DashboardData) -> Table:
    table = Table(title="Cost by Project", title_style="bold cyan")
    table.add_column("Project ID")
    table.add_column("Name")
    table.add_column("Net Cost", justify="right")
    for item in data.project_costs:
        table.add_row(item.project_id, item.project_name, _money(item.net_cost, item.currency))
    return table


def _budget_table(data: DashboardData) -> Table:
    table = Table(title="Budgets", title_style="bold cyan")
    table.add_column("Budget")
    table.add_column("Amount", justify="right")
    table.add_column("Thresholds")
    table.add_column("Spent", justify="right")
    table.add_column("% Used", justify="right")
    for budget in data.budgets:
        amount = _money(budget.amount, budget.currency) if budget.amount is not None else "—"
        thresholds = (
            ", ".join(f"{t * 100:.0f}%" for t in budget.thresholds) if budget.thresholds else "—"
        )
        spent = _money(budget.spent, budget.currency) if budget.spent is not None else "—"
        pct = budget.percent_used
        if pct is None:
            pct_str = "—"
        else:
            colour = "green" if pct < 80 else "yellow" if pct <= 100 else "red"
            pct_str = f"[{colour}]{pct:.1f}%[/{colour}]"
        table.add_row(budget.name, amount, thresholds, spent, pct_str)
    return table


def _trend_table(data: DashboardData) -> Table:
    max_cost = max((p.net_cost for p in data.trend), default=0.0)
    table = Table(title="6-Month Cost Trend", title_style="bold cyan")
    table.add_column("Month")
    table.add_column("Trend")
    table.add_column("Net Cost", justify="right")
    for point in data.trend:
        label = f"{point.invoice_month[:4]}-{point.invoice_month[4:]}"
        table.add_row(
            label,
            f"[green]{_bar(point.net_cost, max_cost)}[/green]",
            _money(point.net_cost, point.currency),
        )
    return table


def render(data: DashboardData, console: Console | None = None, show_trend: bool = False) -> None:
    """Render the dashboard to ``console`` (a fresh one is created if omitted)."""
    console = console or Console()
    console.print(_header_panel(data))
    if data.service_costs:
        console.print(_service_table(data))
    if data.project_costs:
        console.print(_project_table(data))
    if data.budgets:
        console.print(_budget_table(data))
    if show_trend and data.trend:
        console.print(_trend_table(data))
