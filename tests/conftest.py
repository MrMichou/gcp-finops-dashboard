"""Shared pytest fixtures — all offline, no GCP credentials required."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Make the src/ layout importable without an editable install.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class FakeQueryJob:
    """Mimics the object returned by ``bigquery.Client.query``."""

    def __init__(self, rows: list):
        self._rows = rows

    def result(self):
        return self._rows


class FakeBigQueryClient:
    """Records the SQL/params it was called with and returns canned rows."""

    def __init__(self, rows_by_call: list[list]):
        self._rows_by_call = list(rows_by_call)
        self.calls: list[tuple] = []

    def query(self, sql, job_config=None):
        self.calls.append((sql, job_config))
        rows = self._rows_by_call.pop(0) if self._rows_by_call else []
        return FakeQueryJob(rows)


def row(**kwargs):
    """A lightweight stand-in for a BigQuery Row (attribute access)."""
    return SimpleNamespace(**kwargs)


@pytest.fixture
def fake_bq_client():
    return FakeBigQueryClient


@pytest.fixture
def make_row():
    return row
