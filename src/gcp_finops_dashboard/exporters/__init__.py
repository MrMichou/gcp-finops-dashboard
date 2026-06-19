"""Exporter factory.

New formats (e.g. a future ``pdf``) register here without touching callers.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from gcp_finops_dashboard.exporters.base import Exporter
from gcp_finops_dashboard.exporters.csv_exporter import CsvExporter
from gcp_finops_dashboard.exporters.json_exporter import JsonExporter
from gcp_finops_dashboard.models import DashboardData

_EXPORTERS: dict[str, type[Exporter]] = {
    "csv": CsvExporter,
    "json": JsonExporter,
}


def available_formats() -> list[str]:
    return sorted(_EXPORTERS)


def get_exporter(report_type: str) -> Exporter:
    """Return an exporter instance for ``report_type`` (case-insensitive)."""
    key = report_type.lower()
    try:
        return _EXPORTERS[key]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown report type: {report_type!r}. Available: {', '.join(available_formats())}"
        ) from exc


def export_all(
    data: DashboardData,
    report_types: list[str],
    output_dir: str,
    report_name: str,
) -> list[Path]:
    """Export ``data`` to every requested format and return the files written."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    written: list[Path] = []
    for report_type in report_types:
        exporter = get_exporter(report_type)
        path = out_dir / f"{report_name}-{stamp}.{exporter.extension}"
        written.append(exporter.export(data, path))
    return written
