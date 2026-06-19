"""SQL builders: required columns present, values parameterized (injection-safe)."""

from __future__ import annotations

import pytest

from gcp_finops_dashboard import queries

TABLE = "demo-proj.billing_export.gcp_billing_export_v1_abc123"


def _param_names(params):
    return {p.name for p in params}


def test_validate_table_accepts_valid():
    assert queries.validate_table(TABLE) == TABLE


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "only.two",
        "proj.dataset.table; DROP TABLE x",
        "proj dataset table",
        "`proj`.`ds`.`tbl`",
    ],
)
def test_validate_table_rejects_invalid(bad):
    with pytest.raises(queries.InvalidTableError):
        queries.validate_table(bad)


def test_service_cost_query_columns_and_params():
    sql, params = queries.service_cost_query(TABLE, days=30)
    assert "service.description AS service" in sql
    assert "UNNEST(credits)" in sql
    assert f"`{TABLE}`" in sql
    assert "@days" in sql
    assert "days" in _param_names(params)
    # No project filter when none requested.
    assert "project_ids" not in _param_names(params)


def test_project_cost_query_has_project_columns():
    sql, params = queries.project_cost_query(TABLE, days=7)
    assert "project.id AS project_id" in sql
    assert "project.name" in sql
    assert "days" in _param_names(params)


def test_trend_query_groups_by_invoice_month():
    sql, params = queries.trend_query(TABLE, months=6)
    assert "invoice.month AS invoice_month" in sql
    assert "GROUP BY invoice_month" in sql
    assert "interval" in _param_names(params)


def test_project_filter_is_parameterized_not_interpolated():
    malicious = ["x'; DROP TABLE y; --"]
    sql, params = queries.service_cost_query(TABLE, days=30, project_ids=malicious)
    # The value must never appear in the SQL text — it travels as a parameter.
    assert "DROP TABLE y" not in sql
    assert "project.id IN UNNEST(@project_ids)" in sql
    assert "project_ids" in _param_names(params)
