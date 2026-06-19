"""BigQueryCostSource maps rows correctly and runs parameterized queries."""

from __future__ import annotations

from gcp_finops_dashboard.bigquery_client import BigQueryCostSource

TABLE = "demo-proj.billing_export.gcp_billing_export_v1_abc123"


def test_service_costs_mapping(fake_bq_client, make_row):
    rows = [
        make_row(service="Compute Engine", net_cost=100.5, currency="USD"),
        make_row(service="BigQuery", net_cost=42.0, currency="USD"),
    ]
    client = fake_bq_client([rows])
    source = BigQueryCostSource(client, TABLE)
    result = source.get_service_costs()
    assert [s.service for s in result] == ["Compute Engine", "BigQuery"]
    assert result[0].net_cost == 100.5
    # A QueryJobConfig with parameters was passed.
    _, job_config = client.calls[0]
    assert job_config is not None
    assert any(p.name == "days" for p in job_config.query_parameters)


def test_none_net_cost_coerced_to_zero(fake_bq_client, make_row):
    rows = [make_row(service="Networking", net_cost=None, currency="USD")]
    source = BigQueryCostSource(fake_bq_client([rows]), TABLE)
    assert source.get_service_costs()[0].net_cost == 0.0


def test_currency_override(fake_bq_client, make_row):
    rows = [make_row(service="Compute Engine", net_cost=1.0, currency="USD")]
    source = BigQueryCostSource(fake_bq_client([rows]), TABLE, currency_override="EUR")
    assert source.get_service_costs()[0].currency == "EUR"


def test_project_costs_mapping(fake_bq_client, make_row):
    rows = [make_row(project_id="prod", project_name="Prod", net_cost=10.0, currency="USD")]
    source = BigQueryCostSource(fake_bq_client([rows]), TABLE)
    result = source.get_project_costs()
    assert result[0].project_id == "prod"
    assert result[0].project_name == "Prod"


def test_trend_mapping(fake_bq_client, make_row):
    rows = [make_row(invoice_month="202606", net_cost=500.0, currency="USD")]
    source = BigQueryCostSource(fake_bq_client([rows]), TABLE)
    result = source.get_trend()
    assert result[0].invoice_month == "202606"
    assert result[0].net_cost == 500.0
