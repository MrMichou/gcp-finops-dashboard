"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from rich.console import Console

from gcp_finops_dashboard import __version__
from gcp_finops_dashboard.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gcp-finops",
        description="GCP FinOps dashboard: cost breakdowns, trends and budgets across projects.",
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        metavar="PROJECT_ID",
        help="Filter to specific project IDs (default: all projects on the billing account).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Explicitly analyse all projects on the billing account (default behaviour).",
    )
    parser.add_argument(
        "--billing-account",
        metavar="ID",
        help="Billing account ID, e.g. 01ABCD-23EFGH-456789 (used for budgets and project listing).",
    )
    parser.add_argument(
        "--bq-table",
        metavar="PROJECT.DATASET.TABLE",
        help="Fully-qualified BigQuery billing export table.",
    )
    parser.add_argument(
        "--billing-project",
        metavar="ID",
        help="Project that runs and is billed for BigQuery jobs (defaults to the table's project).",
    )
    parser.add_argument(
        "--time-range",
        type=int,
        metavar="DAYS",
        help="Lookback window in days for service/project costs (default: 30).",
    )
    parser.add_argument(
        "--trend",
        action="store_true",
        help="Show the 6-month cost trend chart.",
    )
    parser.add_argument(
        "--report-name",
        metavar="NAME",
        help="Base filename for exported reports (default: gcp-finops).",
    )
    parser.add_argument(
        "--report-type",
        nargs="+",
        choices=["csv", "json", "pdf"],
        metavar="FORMAT",
        help="One or more export formats: csv json pdf.",
    )
    parser.add_argument(
        "--dir",
        dest="output_dir",
        metavar="PATH",
        help="Output directory for exported reports (default: ./reports).",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audit resources for waste/compliance (stopped VMs, unattached disks, "
        "idle IPs, buckets without lifecycle, untagged resources).",
    )
    parser.add_argument(
        "--required-labels",
        nargs="+",
        metavar="KEY",
        help="Label keys every resource must carry; missing ones are flagged as untagged.",
    )
    parser.add_argument(
        "--config-file",
        metavar="PATH",
        help="Path to a TOML/YAML/JSON config file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use bundled sample data — no GCP calls. Useful for a quick demo.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _cli_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Collect only the options the user actually set, so CLI wins cleanly."""
    overrides: dict[str, Any] = {}
    if args.projects:
        overrides["projects"] = args.projects
    if args.billing_account:
        overrides["billing_account_id"] = args.billing_account
    if args.bq_table:
        overrides["bq_table"] = args.bq_table
    if args.billing_project:
        overrides["billing_project"] = args.billing_project
    if args.time_range is not None:
        overrides["time_range_days"] = args.time_range
    if args.trend:
        overrides["trend"] = True
    if args.report_name:
        overrides["report_name"] = args.report_name
    if args.report_type:
        overrides["report_types"] = args.report_type
    if args.output_dir:
        overrides["output_dir"] = args.output_dir
    if args.audit:
        overrides["audit"] = True
    if args.required_labels:
        overrides["required_labels"] = args.required_labels
    if args.dry_run:
        overrides["dry_run"] = True
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    try:
        config = load_config(_cli_overrides(args), config_file=args.config_file)
    except Exception as exc:  # config errors are user-facing
        console.print(f"[red]Configuration error:[/red] {exc}")
        return 2

    # Imported here so --help/--version work even without GCP libs installed.
    from gcp_finops_dashboard import visualize
    from gcp_finops_dashboard.dashboard import build_dashboard

    try:
        data = build_dashboard(config)
    except Exception as exc:
        console.print(f"[red]Failed to build dashboard:[/red] {exc}")
        return 1

    visualize.render(data, console=console, show_trend=config.trend)

    if config.report_types:
        from gcp_finops_dashboard.exporters import export_all

        try:
            written = export_all(
                data, config.report_types, config.output_dir, config.report_name
            )
        except Exception as exc:
            console.print(f"[red]Export failed:[/red] {exc}")
            return 1
        for path in written:
            console.print(f"[green]Wrote[/green] {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
