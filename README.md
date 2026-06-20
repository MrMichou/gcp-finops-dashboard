# GCP FinOps Dashboard

A terminal-based FinOps dashboard for Google Cloud — the GCP counterpart to
[aws-finops-dashboard](https://github.com/ravikiranvm/aws-finops-dashboard).
It gives you consolidated cost visibility across projects with rich,
formatted tables right in your terminal, plus CSV/JSON exports.

```
╭─────────────────────── GCP FinOps Dashboard ────────────────────────╮
│ Billing account: 01ABCD-23EFGH-456789                               │
│ Export table: demo-proj.billing_export.gcp_billing_export_v1_sample │
│ Window: last 30 days                                                │
│ Projects: prod-app, data-platform, sandbox                          │
╰─────────────────────────────────────────────────────────────────────╯
```

## Features

- **Cost by service** — net cost per GCP service over a configurable window, ranked by spend.
- **Cost by project** — spend broken down per project (the GCP equivalent of AWS "profiles").
- **6-month cost trend** — a terminal bar chart of monthly invoiced cost.
- **Budget tracking** — configured budgets and threshold rules from the Cloud Billing Budgets API.
- **Resource audit** — flag wasteful or non-compliant resources: stopped Compute instances, unattached persistent disks, idle reserved static IPs, GCS buckets without lifecycle rules, and resources missing required labels.
- **Exports** — CSV, JSON and PDF reports for spreadsheets or downstream tooling.
- **Slack notifications** — post a run summary (total cost, top services, budget alerts, audit findings) to an incoming webhook.
- **Multi-project** — analyse every project on a billing account by default, or filter to a list.
- **Dry-run mode** — explore the full output with bundled sample data, no GCP access needed.

> Net cost accounts for credits (`cost + sum(credits.amount)`), matching how
> Google reports your effective spend.

## Why BigQuery?

Unlike AWS Cost Explorer, GCP has no API that returns your detailed spend
directly. The standard way to get cost data is the **Cloud Billing export to
BigQuery**. This tool queries that export table for costs and trends, and uses
the **Cloud Billing Budgets API** for budgets. You must
[enable the BigQuery billing export](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)
on your billing account first (standard usage cost export).

## Installation

```bash
pip install -e .
# optional YAML config support:
pip install -e '.[yaml]'
# optional PDF export support:
pip install -e '.[pdf]'
```

This installs the `gcp-finops` command (also runnable as `python -m gcp_finops_dashboard`).

## Authentication

Clients use Application Default Credentials (ADC). Use either:

```bash
gcloud auth application-default login
# or, for automation:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

The service account / user needs read access to the BigQuery export dataset
(BigQuery Data Viewer + Job User on the billing project) and, for budgets,
`billing.budgets.list` on the billing account. For `--audit`, it also needs
read (`*.list`) access to Compute Engine, Cloud Storage and Cloud Functions on
the audited projects (e.g. the `roles/viewer` role); resources whose API is
unavailable or unauthorised are skipped rather than failing the run.

## Usage

Try it with no credentials using sample data:

```bash
gcp-finops --dry-run --trend
```

A real run:

```bash
gcp-finops \
  --bq-table my-proj.billing_export.gcp_billing_export_v1_01ABCD_23EFGH_456789 \
  --billing-account 01ABCD-23EFGH-456789 \
  --time-range 30 --trend \
  --report-type csv json --dir ./reports
```

Filter to specific projects:

```bash
gcp-finops --bq-table my-proj.billing_export.gcp_billing_export_v1_xxx \
  --projects prod-app data-platform
```

### Options

| Flag | Description |
|------|-------------|
| `--projects ID [ID ...]` | Filter to specific project IDs (default: all projects on the billing account). |
| `--all` | Explicitly analyse all projects (default behaviour). |
| `--billing-account ID` | Billing account ID, used for budgets and project listing. |
| `--bq-table P.D.T` | Fully-qualified BigQuery billing export table. |
| `--billing-project ID` | Project that runs/pays for BigQuery jobs (defaults to the table's project). |
| `--time-range DAYS` | Lookback window for service/project costs (default 30). |
| `--trend` | Show the 6-month cost trend chart. |
| `--audit` | Audit resources for waste/compliance (stopped VMs, unattached disks, idle IPs, buckets without lifecycle, untagged resources). |
| `--required-labels KEY [KEY ...]` | Label keys every resource must carry; missing ones are flagged as untagged. |
| `--report-name NAME` | Base filename for exports (default `gcp-finops`). |
| `--report-type csv json pdf` | Export formats (`pdf` needs the `pdf` extra). |
| `--dir PATH` | Output directory for reports (default `./reports`). |
| `--slack-webhook URL` | Post a run summary to a Slack incoming webhook (env `GCP_FINOPS_SLACK_WEBHOOK`). |
| `--config-file PATH` | TOML/YAML/JSON config file. |
| `--dry-run` | Use bundled sample data — no GCP calls. |

Audit resources and post the summary to Slack:

```bash
gcp-finops --bq-table my-proj.billing_export.gcp_billing_export_v1_xxx \
  --billing-account 01ABCD-23EFGH-456789 \
  --audit --required-labels team env \
  --slack-webhook https://hooks.slack.com/services/T00/B00/XXXX
```

CLI flags override config-file values, which override environment variables
(`GCP_FINOPS_BILLING_ACCOUNT`, `GCP_FINOPS_BQ_TABLE`, `GCP_FINOPS_BILLING_PROJECT`,
`GCP_FINOPS_SLACK_WEBHOOK`).

## Configuration file

Drop a `gcp-finops.toml` in the working directory (or pass `--config-file`):

```toml
billing_account_id = "01ABCD-23EFGH-456789"
bq_table = "my-proj.billing_export.gcp_billing_export_v1_01ABCD_23EFGH_456789"
billing_project = "my-proj"
projects = ["prod-app", "data-platform"]
time_range_days = 30
trend = true
report_types = ["csv", "json"]
output_dir = "./reports"
```

YAML and JSON files are also supported (detected by extension).

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest            # full offline test suite (mocked GCP clients)
ruff check .
```

The codebase keeps all GCP I/O in `auth.py`, `projects.py`, `bigquery_client.py`
and `budgets.py`; the rest (config, SQL builders, rendering, exporters) is pure
and unit-tested without credentials.

### Releasing

Releases are automated with [release-please](https://github.com/googleapis/release-please).
Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`,
`fix:`, …) and merge to `main`; a release PR is opened automatically, and
merging it tags the release, publishes the GitHub Release and pushes to PyPI.
See [RELEASING.md](RELEASING.md) for details.

## Roadmap

Growing toward parity with the AWS tool. Delivered in v0.2:

- [x] Resource audit (stopped/idle/unattached/untagged Compute, GCS, Functions)
- [x] PDF export
- [x] Slack notifications

Still planned:

- [ ] Cloud SQL coverage in the resource audit (via the Cloud SQL Admin API)
- [ ] GCS report upload

The exporter factory and the `CostSource` protocol remain the extension points
for these.

## License

MIT — see [LICENSE](LICENSE).
