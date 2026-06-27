"""Config precedence (CLI > file > env > default) and multi-format parsing."""

from __future__ import annotations

import json

import pytest

from gcp_finops_dashboard.config import (
    DEFAULT_TIME_RANGE_DAYS,
    Config,
    ConfigError,
    load_config,
)


def test_defaults_when_nothing_provided(monkeypatch):
    monkeypatch.delenv("GCP_FINOPS_BQ_TABLE", raising=False)
    config = load_config({}, config_file=None)
    assert config.time_range_days == DEFAULT_TIME_RANGE_DAYS
    assert config.bq_table is None
    assert config.report_types == []


def test_cli_overrides_file(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text('bq_table = "p.d.file_table"\ntime_range_days = 90\n')
    config = load_config({"time_range_days": 7}, config_file=str(cfg))
    assert config.time_range_days == 7  # CLI wins
    assert config.bq_table == "p.d.file_table"  # falls back to file


def test_env_lowest_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("GCP_FINOPS_BQ_TABLE", "p.d.env_table")
    cfg = tmp_path / "c.toml"
    cfg.write_text('bq_table = "p.d.file_table"\n')
    config = load_config({}, config_file=str(cfg))
    assert config.bq_table == "p.d.file_table"  # file beats env


def test_json_config(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"bq_table": "p.d.j", "projects": ["a", "b"]}))
    config = load_config({}, config_file=str(cfg))
    assert config.bq_table == "p.d.j"
    assert config.projects == ["a", "b"]


def test_yaml_config(tmp_path):
    pytest.importorskip("yaml")
    cfg = tmp_path / "c.yaml"
    cfg.write_text("bq_table: p.d.y\ntrend: true\n")
    config = load_config({}, config_file=str(cfg))
    assert config.bq_table == "p.d.y"
    assert config.trend is True


def test_missing_config_file_raises():
    with pytest.raises(ConfigError):
        load_config({}, config_file="/nonexistent/path.toml")


@pytest.mark.parametrize("bad", [0, -1, -30])
def test_non_positive_time_range_rejected(bad):
    with pytest.raises(ConfigError, match="time_range_days must be a positive integer"):
        load_config({"time_range_days": bad}, config_file=None)


def test_effective_billing_project_inferred():
    config = Config(bq_table="my-proj.ds.tbl")
    assert config.effective_billing_project == "my-proj"
    assert Config(billing_project="explicit").effective_billing_project == "explicit"
