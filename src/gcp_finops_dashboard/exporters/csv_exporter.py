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
        return out_path
