"""JSON exporter — structured dump of the full dashboard."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from gcp_finops_dashboard.exporters.base import Exporter
from gcp_finops_dashboard.models import DashboardData


class JsonExporter(Exporter):
    extension = "json"

    def export(self, data: DashboardData, out_path: Path) -> Path:
        payload = {
            "metadata": {
                "billing_account_id": data.billing_account_id,
                "bq_table": data.bq_table,
                "time_range_days": data.time_range_days,
                "project_scope": data.project_scope,
                "total_cost": round(data.total_cost, 2),
                "currency": data.currency,
            },
            "service_costs": [asdict(s) for s in data.service_costs],
            "project_costs": [asdict(p) for p in data.project_costs],
            "trend": [asdict(t) for t in data.trend],
            "budgets": [asdict(b) for b in data.budgets],
            "findings": [asdict(f) for f in data.findings],
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out_path
