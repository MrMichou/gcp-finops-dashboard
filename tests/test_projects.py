"""Project scope resolution: explicit filter vs full billing account."""

from __future__ import annotations

from types import SimpleNamespace

from gcp_finops_dashboard.projects import resolve_project_scope


class FakeBillingClient:
    def __init__(self, infos):
        self._infos = infos
        self.last_name = None

    def list_project_billing_info(self, name):
        self.last_name = name
        return list(self._infos)


def _info(project_id, enabled=True):
    return SimpleNamespace(
        project_id=project_id, name=f"projects/{project_id}", billing_enabled=enabled
    )


def test_explicit_projects_win():
    client = FakeBillingClient([_info("a"), _info("b")])
    assert resolve_project_scope(["only-this"], client, "acct") == ["only-this"]
    # The billing client is not consulted when an explicit list is given.
    assert client.last_name is None


def test_lists_all_enabled_projects():
    client = FakeBillingClient([_info("a"), _info("b"), _info("c", enabled=False)])
    scope = resolve_project_scope(None, client, "acct-123")
    assert scope == ["a", "b"]
    assert client.last_name == "billingAccounts/acct-123"


def test_no_client_means_no_filter():
    assert resolve_project_scope(None, None, None) == []
