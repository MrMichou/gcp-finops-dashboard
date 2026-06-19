"""BigQuery SQL builders for the standard Cloud Billing export schema.

Pure functions only — no I/O. Each builder returns ``(sql, parameters)`` where
``parameters`` is a list of ``google.cloud.bigquery`` query-parameter objects.

Security model
--------------
BigQuery cannot parameterize *identifiers* (table names), so the table is
validated against a strict allowlist regex and interpolated. Every *value*
(day window, project filter) is passed as a query parameter, never string
formatted, which prevents SQL injection through user-supplied config.
"""

from __future__ import annotations

import re

from google.cloud import bigquery

# project.dataset.table — letters, digits, underscores, dashes and dots only.
_TABLE_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_$-]+$")

# Net cost = gross cost + sum of (negative) credit amounts.
_NET_COST = (
    "SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0))"
)


class InvalidTableError(ValueError):
    """Raised when a BigQuery table identifier fails validation."""


def validate_table(table: str) -> str:
    """Return ``table`` if it is a safe fully-qualified identifier, else raise."""
    if not table or not _TABLE_RE.match(table):
        raise InvalidTableError(
            f"Invalid BigQuery table identifier: {table!r}. "
            "Expected fully-qualified 'project.dataset.table'."
        )
    return table


def _quoted(table: str) -> str:
    """Backtick-quote a validated table for embedding in SQL."""
    return f"`{validate_table(table)}`"


def _project_filter(project_ids: list[str] | None) -> tuple[str, list]:
    """Build the optional project-ID filter clause and its parameter."""
    if not project_ids:
        return "", []
    clause = "  AND project.id IN UNNEST(@project_ids)\n"
    param = bigquery.ArrayQueryParameter("project_ids", "STRING", list(project_ids))
    return clause, [param]


def service_cost_query(
    table: str, days: int, project_ids: list[str] | None = None
) -> tuple[str, list]:
    """Net cost per service over the last ``days`` days."""
    clause, params = _project_filter(project_ids)
    sql = (
        "SELECT\n"
        "  service.description AS service,\n"
        f"  {_NET_COST} AS net_cost,\n"
        "  ANY_VALUE(currency) AS currency\n"
        f"FROM {_quoted(table)}\n"
        "WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)\n"
        f"{clause}"
        "GROUP BY service\n"
        "ORDER BY net_cost DESC\n"
    )
    params.append(bigquery.ScalarQueryParameter("days", "INT64", days))
    return sql, params


def project_cost_query(
    table: str, days: int, project_ids: list[str] | None = None
) -> tuple[str, list]:
    """Net cost per project over the last ``days`` days."""
    clause, params = _project_filter(project_ids)
    sql = (
        "SELECT\n"
        "  project.id AS project_id,\n"
        "  ANY_VALUE(project.name) AS project_name,\n"
        f"  {_NET_COST} AS net_cost,\n"
        "  ANY_VALUE(currency) AS currency\n"
        f"FROM {_quoted(table)}\n"
        "WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)\n"
        "  AND project.id IS NOT NULL\n"
        f"{clause}"
        "GROUP BY project_id\n"
        "ORDER BY net_cost DESC\n"
    )
    params.append(bigquery.ScalarQueryParameter("days", "INT64", days))
    return sql, params


def trend_query(
    table: str, months: int = 6, project_ids: list[str] | None = None
) -> tuple[str, list]:
    """Net cost grouped by invoice month for the trailing ``months`` months."""
    clause, params = _project_filter(project_ids)
    # months buckets = current month + (months - 1) earlier months.
    interval = max(months - 1, 0)
    sql = (
        "SELECT\n"
        "  invoice.month AS invoice_month,\n"
        f"  {_NET_COST} AS net_cost,\n"
        "  ANY_VALUE(currency) AS currency\n"
        f"FROM {_quoted(table)}\n"
        "WHERE invoice.month >= FORMAT_DATE('%Y%m', "
        "DATE_SUB(CURRENT_DATE(), INTERVAL @interval MONTH))\n"
        f"{clause}"
        "GROUP BY invoice_month\n"
        "ORDER BY invoice_month\n"
    )
    params.append(bigquery.ScalarQueryParameter("interval", "INT64", interval))
    return sql, params
