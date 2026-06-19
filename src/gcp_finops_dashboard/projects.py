"""Project discovery and filtering.

The AWS tool iterates over "profiles"; the GCP equivalent is the set of projects
attached to a billing account. We default to all projects on the account and
allow narrowing to an explicit list of project IDs.
"""

from __future__ import annotations

from typing import Any


def _parent(billing_account_id: str) -> str:
    if billing_account_id.startswith("billingAccounts/"):
        return billing_account_id
    return f"billingAccounts/{billing_account_id}"


def list_billing_account_projects(billing_client: Any, billing_account_id: str) -> list[str]:
    """Return project IDs whose billing is enabled on the account.

    Uses ``CloudBillingClient.list_project_billing_info`` — the most direct
    equivalent of "all accounts for a billing scope" and avoids needing
    org-level Resource Manager permissions.
    """
    project_ids: list[str] = []
    for info in billing_client.list_project_billing_info(name=_parent(billing_account_id)):
        if getattr(info, "billing_enabled", False):
            # ``project_id`` field, else parse from "projects/{id}" resource name.
            project_id = getattr(info, "project_id", "") or ""
            if not project_id:
                name = getattr(info, "name", "") or ""
                project_id = name.split("/")[-1] if "/" in name else name
            if project_id:
                project_ids.append(project_id)
    return project_ids


def resolve_project_scope(
    explicit_projects: list[str] | None,
    billing_client: Any | None = None,
    billing_account_id: str | None = None,
) -> list[str]:
    """Resolve the effective project filter for the run.

    - An explicit list always wins (returned as-is).
    - Otherwise, if a billing client + account are available, list all projects
      on the account.
    - Otherwise, return an empty list meaning "no project filter" (queries then
      span whatever the export table contains).
    """
    if explicit_projects:
        return list(explicit_projects)
    if billing_client is not None and billing_account_id:
        return list_billing_account_projects(billing_client, billing_account_id)
    return []
