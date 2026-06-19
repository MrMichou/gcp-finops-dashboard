"""PDF exporter — a printable one-page summary of the dashboard.

``reportlab`` is an optional dependency (the ``pdf`` extra). It is imported
inside :meth:`export` so the rest of the tool keeps working without it, with an
actionable error when the format is requested but the extra is missing — the
same pattern config.py uses for the optional YAML dependency.
"""

from __future__ import annotations

from pathlib import Path

from gcp_finops_dashboard.exporters.base import Exporter
from gcp_finops_dashboard.models import DashboardData


def _money(value: float, currency: str) -> str:
    return f"{value:,.2f} {currency}"


class PdfExporter(Exporter):
    extension = "pdf"

    def export(self, data: DashboardData, out_path: Path) -> Path:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ValueError(
                "PDF export requires reportlab. Install with: "
                "pip install 'gcp-finops-dashboard[pdf]'"
            ) from exc

        styles = getSampleStyleSheet()
        story: list = [Paragraph("GCP FinOps Dashboard", styles["Title"])]

        meta = [
            f"Billing account: {data.billing_account_id or '(n/a)'}",
            f"Export table: {data.bq_table or '(n/a)'}",
            f"Window: last {data.time_range_days} days",
            f"Projects: {', '.join(data.project_scope) if data.project_scope else 'all projects'}",
            f"Total cost: {_money(data.total_cost, data.currency)}",
        ]
        for line in meta:
            story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))

        def section(title: str, header: list[str], rows: list[list[str]]) -> None:
            if not rows:
                return
            story.append(Paragraph(title, styles["Heading2"]))
            table = Table([header, *rows], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6feb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f3f6")]),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.4 * cm))

        section(
            "Cost by Service",
            ["Service", "Net Cost"],
            [[s.service, _money(s.net_cost, s.currency)] for s in data.service_costs],
        )
        section(
            "Cost by Project",
            ["Project", "Name", "Net Cost"],
            [[p.project_id, p.project_name, _money(p.net_cost, p.currency)] for p in data.project_costs],
        )
        section(
            "Budgets",
            ["Budget", "Amount", "Spent", "% Used"],
            [
                [
                    b.name,
                    _money(b.amount, b.currency) if b.amount is not None else "—",
                    _money(b.spent, b.currency) if b.spent is not None else "—",
                    f"{b.percent_used:.1f}%" if b.percent_used is not None else "—",
                ]
                for b in data.budgets
            ],
        )
        section(
            "Resource Audit",
            ["Type", "Project", "Issue", "Detail"],
            [[f.resource_type, f.project_id, f.issue, f.detail] for f in data.findings],
        )
        section(
            "6-Month Cost Trend",
            ["Month", "Net Cost"],
            [
                [f"{t.invoice_month[:4]}-{t.invoice_month[4:]}", _money(t.net_cost, t.currency)]
                for t in data.trend
            ],
        )

        SimpleDocTemplate(str(out_path), pagesize=A4).build(story)
        return out_path
