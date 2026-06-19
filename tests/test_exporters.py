"""CSV/JSON exporters round-trip to disk."""

from __future__ import annotations

import csv
import json

import pytest

from gcp_finops_dashboard.exporters import available_formats, export_all, get_exporter
from gcp_finops_dashboard.sample_data import sample_dashboard


def test_available_formats():
    assert set(available_formats()) == {"csv", "json", "pdf"}


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        get_exporter("xlsx")


def test_pdf_round_trip(tmp_path):
    pytest.importorskip("reportlab")
    paths = export_all(sample_dashboard(), ["pdf"], str(tmp_path), "report")
    assert len(paths) == 1
    assert paths[0].suffix == ".pdf"
    content = paths[0].read_bytes()
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_csv_round_trip(tmp_path):
    data = sample_dashboard()
    paths = export_all(data, ["csv"], str(tmp_path), "report")
    assert len(paths) == 1
    with paths[0].open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    sections = {r["section"] for r in rows}
    assert {"service_cost", "project_cost", "trend", "budget", "finding"} <= sections
    compute = next(r for r in rows if r["section"] == "service_cost" and r["key"] == "Compute Engine")
    assert compute["value"] == "4231.55"
    finding = next(r for r in rows if r["section"] == "finding")
    assert finding["value"] in {"stopped", "unattached", "idle", "untagged", "no_lifecycle"}


def test_json_round_trip(tmp_path):
    data = sample_dashboard()
    paths = export_all(data, ["json"], str(tmp_path), "report")
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    assert payload["metadata"]["bq_table"] == data.bq_table
    assert len(payload["service_costs"]) == len(data.service_costs)
    assert payload["budgets"][0]["name"] == "Monthly Org Budget"
    assert len(payload["findings"]) == len(data.findings)
    assert payload["findings"][0]["issue"] == data.findings[0].issue


def test_export_all_creates_dir_and_multiple_files(tmp_path):
    out = tmp_path / "nested" / "reports"
    paths = export_all(sample_dashboard(), ["csv", "json"], str(out), "r")
    assert len(paths) == 2
    assert all(p.exists() for p in paths)
