"""CSV exporter — single tidy/long-format file across all sections."""

from __future__ import annotations

import csv
from pathlib import Path

from gcp_finops_dashboard.exporters.base import Exporter
from gcp_finops_dashboard.models import DashboardData

_HEADER = ["section", "key", "name", "value", "currency", "extra"]


class CsvExporter(Exporter):
    extension = "csv"

    def export(self, data: DashboardData, out_path: Path) -> Path:
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(_HEADER)
            for s in data.service_costs:
                writer.writerow(["service_cost", s.service, "", f"{s.net_cost:.2f}", s.currency, ""])
            for p in data.project_costs:
                writer.writerow(
                    ["project_cost", p.project_id, p.project_name, f"{p.net_cost:.2f}", p.currency, ""]
                )
            for t in data.trend:
                writer.writerow(["trend", t.invoice_month, "", f"{t.net_cost:.2f}", t.currency, ""])
            for b in data.budgets:
                amount = "" if b.amount is None else f"{b.amount:.2f}"
                spent = "" if b.spent is None else f"spent={b.spent:.2f}"
                writer.writerow(["budget", b.name, "", amount, b.currency, spent])
            for f in data.findings:
                extra = f.detail
                if f.estimated_monthly_cost is not None:
                    extra = f"{f.detail} (est_cost={f.estimated_monthly_cost:.2f})"
                # section/key/name/value/currency/extra -> reuse columns for findings:
                # section=finding, key=resource_type, name=project/resource,
                # value=issue, currency=location, extra=detail.
                resource = f"{f.project_id}/{f.name}" if f.project_id else f.name
                writer.writerow(
                    ["finding", f.resource_type, resource, f.issue, f.location, extra]
                )
        return out_path
