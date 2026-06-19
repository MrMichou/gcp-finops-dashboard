"""Configuration loading and precedence resolution.

Precedence (highest wins): CLI flag > config file > environment variable >
built-in default. The result is a single :class:`Config` consumed by the rest
of the application.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

DEFAULT_TIME_RANGE_DAYS = 30
DEFAULT_REPORT_NAME = "gcp-finops"
DEFAULT_OUTPUT_DIR = "./reports"
DEFAULT_TREND_MONTHS = 6

# Searched in order when --config-file is not provided.
_DEFAULT_CONFIG_PATHS = (
    Path("gcp-finops.toml"),
    Path("gcp-finops.yaml"),
    Path("gcp-finops.json"),
    Path.home() / ".config" / "gcp-finops" / "config.toml",
)

# Maps config keys to the environment variable that can supply them.
_ENV_KEYS = {
    "billing_account_id": "GCP_FINOPS_BILLING_ACCOUNT",
    "bq_table": "GCP_FINOPS_BQ_TABLE",
    "billing_project": "GCP_FINOPS_BILLING_PROJECT",
}


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""


@dataclass(frozen=True)
class Config:
    """Resolved, immutable runtime configuration."""

    billing_account_id: str | None = None
    bq_table: str | None = None
    billing_project: str | None = None
    projects: list[str] = field(default_factory=list)
    time_range_days: int = DEFAULT_TIME_RANGE_DAYS
    trend: bool = False
    trend_months: int = DEFAULT_TREND_MONTHS
    report_name: str = DEFAULT_REPORT_NAME
    report_types: list[str] = field(default_factory=list)
    output_dir: str = DEFAULT_OUTPUT_DIR
    currency: str | None = None
    audit: bool = False
    required_labels: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def effective_billing_project(self) -> str | None:
        """Project that runs/pays for BigQuery jobs.

        Defaults to the project component of the export table when not set.
        """
        if self.billing_project:
            return self.billing_project
        if self.bq_table and "." in self.bq_table:
            return self.bq_table.split(".", 1)[0]
        return None


def _load_file(path: Path) -> dict[str, Any]:
    """Parse a TOML/YAML/JSON config file based on its extension."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".toml":
        return tomllib.loads(text)
    if suffix == ".json":
        return json.loads(text)
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ConfigError(
                "YAML config requires PyYAML. Install with: pip install 'gcp-finops-dashboard[yaml]'"
            ) from exc
        return yaml.safe_load(text) or {}
    raise ConfigError(f"Unsupported config file type: {suffix} (use .toml, .yaml or .json)")


def _find_default_config() -> Path | None:
    for candidate in _DEFAULT_CONFIG_PATHS:
        if candidate.exists():
            return candidate
    return None


def _from_env() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, env_var in _ENV_KEYS.items():
        raw = os.environ.get(env_var)
        if raw:
            values[key] = raw
    return values


def _coerce(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only known keys and normalise their types."""
    allowed = {f for f in Config.__dataclass_fields__}  # noqa: SIM118
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key not in allowed or value is None:
            continue
        if key in ("projects", "report_types", "required_labels"):
            out[key] = list(value) if not isinstance(value, str) else [value]
        elif key == "time_range_days":
            out[key] = int(value)
        elif key in ("trend", "dry_run", "audit"):
            out[key] = bool(value)
        else:
            out[key] = value
    return out


def load_config(cli_overrides: dict[str, Any], config_file: str | None = None) -> Config:
    """Merge config file + environment + CLI overrides into a :class:`Config`.

    ``cli_overrides`` should already contain only keys the user actually set on
    the command line (``None``/empty values are ignored), so CLI always wins.
    """
    merged: dict[str, Any] = {}

    # Lowest precedence: environment variables.
    merged.update(_from_env())

    # Next: config file (explicit path, else first default found).
    path = Path(config_file) if config_file else _find_default_config()
    if path is not None:
        merged.update(_coerce(_load_file(path)))

    # Highest precedence: CLI overrides.
    merged.update(_coerce(cli_overrides))

    config = replace(Config(), **merged)
    return config
