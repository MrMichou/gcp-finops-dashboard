"""CLI: argument parsing, override collection and the ``main()`` exit flow.

All offline — ``--dry-run`` feeds the bundled sample data so no GCP calls or
credentials are needed, and the export/Slack side effects are monkeypatched.
"""

from __future__ import annotations

import pytest

from gcp_finops_dashboard import cli


# --- _cli_overrides ---------------------------------------------------------


def _overrides(argv):
    return cli._cli_overrides(cli.build_parser().parse_args(argv))


def test_overrides_collects_only_set_flags():
    # An empty command line should set nothing, so config-file/env can win.
    assert _overrides([]) == {}


def test_overrides_maps_flags_to_config_keys():
    overrides = _overrides(
        [
            "--projects",
            "p1",
            "p2",
            "--billing-account",
            "ACC",
            "--bq-table",
            "proj.ds.tbl",
            "--billing-project",
            "bill",
            "--report-name",
            "myreport",
            "--report-type",
            "json",
            "csv",
            "--dir",
            "/out",
            "--required-labels",
            "team",
            "--slack-webhook",
            "http://hook",
        ]
    )
    assert overrides == {
        "projects": ["p1", "p2"],
        "billing_account_id": "ACC",
        "bq_table": "proj.ds.tbl",
        "billing_project": "bill",
        "report_name": "myreport",
        "report_types": ["json", "csv"],
        "output_dir": "/out",
        "required_labels": ["team"],
        "slack_webhook": "http://hook",
    }


def test_overrides_time_range_zero_is_respected():
    # Guard the ``is not None`` check: an explicit 0 must survive.
    assert _overrides(["--time-range", "0"])["time_range_days"] == 0


def test_overrides_boolean_flags():
    overrides = _overrides(["--trend", "--audit", "--dry-run"])
    assert overrides == {"trend": True, "audit": True, "dry_run": True}


# --- main() exit codes ------------------------------------------------------


def test_main_dry_run_succeeds():
    assert cli.main(["--dry-run"]) == 0


def test_main_config_error_returns_2():
    # A missing explicit config file is a user-facing configuration error.
    assert cli.main(["--dry-run", "--config-file", "/nope/missing.toml"]) == 2


def test_main_build_failure_returns_1():
    # No dry-run and no BigQuery table -> build_dashboard raises ConfigError.
    assert cli.main([]) == 1


def test_main_export_writes_files(tmp_path):
    rc = cli.main(["--dry-run", "--report-type", "json", "--dir", str(tmp_path)])
    assert rc == 0
    assert list(tmp_path.glob("*.json"))


def test_main_export_failure_returns_1(monkeypatch):
    from gcp_finops_dashboard import exporters

    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(exporters, "export_all", boom)
    assert cli.main(["--dry-run", "--report-type", "json"]) == 1


def test_main_sends_slack_summary(monkeypatch):
    from gcp_finops_dashboard import notifications

    sent = {}
    monkeypatch.setattr(
        notifications,
        "send_slack_summary",
        lambda url, data: sent.update(url=url, total=data.total_cost),
    )
    assert cli.main(["--dry-run", "--slack-webhook", "http://hook"]) == 0
    assert sent["url"] == "http://hook"


def test_main_slack_failure_does_not_fail_run(monkeypatch):
    from gcp_finops_dashboard import notifications

    def boom(url, data):
        raise RuntimeError("slack down")

    monkeypatch.setattr(notifications, "send_slack_summary", boom)
    # A notification failure must be logged but never abort the run.
    assert cli.main(["--dry-run", "--slack-webhook", "http://hook"]) == 0


def test_main_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "0.2.0" in capsys.readouterr().out
