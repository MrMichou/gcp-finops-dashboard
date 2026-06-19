"""End-to-end: dry-run pipeline, rendering smoke test, bar-chart helper."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from gcp_finops_dashboard import visualize
from gcp_finops_dashboard.config import Config, ConfigError
from gcp_finops_dashboard.dashboard import build_dashboard
from gcp_finops_dashboard.sample_data import sample_dashboard


def test_dry_run_returns_sample_data():
    data = build_dashboard(Config(dry_run=True))
    assert data.service_costs
    assert data.total_cost > 0


def test_missing_table_without_dry_run_raises():
    with pytest.raises(ConfigError):
        build_dashboard(Config(dry_run=False, bq_table=None))


def test_render_smoke():
    console = Console(file=StringIO(), width=120)
    visualize.render(sample_dashboard(), console=console, show_trend=True)
    output = console.file.getvalue()
    assert "Cost by Service" in output
    assert "Compute Engine" in output
    assert "Budgets" in output
    assert "Trend" in output


def test_bar_helper_scaling():
    assert visualize._bar(0, 100) == ""
    assert visualize._bar(100, 100) == visualize._BLOCK * visualize._BAR_WIDTH
    assert 0 < len(visualize._bar(50, 100)) <= visualize._BAR_WIDTH
    # A tiny non-zero value still renders at least one block.
    assert len(visualize._bar(1, 1_000_000)) == 1
