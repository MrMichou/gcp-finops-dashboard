"""auth: credential resolution branches with ``google.auth`` fully mocked.

No real Application Default Credentials are ever touched.
"""

from __future__ import annotations

import pytest

from gcp_finops_dashboard import auth


class _Creds:
    """Minimal stand-in for a google-auth credentials object."""

    def __init__(self, quota=None):
        self.quota = quota

    def with_quota_project(self, project):
        return _Creds(quota=project)


def test_get_credentials_raises_friendly_autherror(monkeypatch):
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    def boom(*args, **kwargs):
        raise DefaultCredentialsError("no creds")

    monkeypatch.setattr(google.auth, "default", boom)
    with pytest.raises(auth.AuthError) as exc:
        auth.get_credentials()
    # The raw library error is replaced with actionable remediation.
    assert "gcloud auth application-default login" in str(exc.value)


def test_get_credentials_applies_quota_project(monkeypatch):
    import google.auth

    monkeypatch.setattr(google.auth, "default", lambda *a, **k: (_Creds(), "default-proj"))
    creds, project = auth.get_credentials(quota_project="bill-proj")
    assert project == "default-proj"
    assert creds.quota == "bill-proj"


def test_get_credentials_without_quota_project(monkeypatch):
    import google.auth

    original = _Creds()
    monkeypatch.setattr(google.auth, "default", lambda *a, **k: (original, "p"))
    creds, project = auth.get_credentials()
    # Untouched when no quota project is requested.
    assert creds is original
    assert project == "p"


def test_make_bigquery_client_prefers_billing_project(monkeypatch):
    from google.cloud import bigquery

    monkeypatch.setattr(auth, "get_credentials", lambda quota_project=None: ("creds", "default-proj"))
    captured = {}
    monkeypatch.setattr(
        bigquery, "Client", lambda project, credentials: captured.update(project=project) or "C"
    )
    assert auth.make_bigquery_client("bill-proj") == "C"
    assert captured["project"] == "bill-proj"


def test_make_bigquery_client_falls_back_to_default_project(monkeypatch):
    from google.cloud import bigquery

    monkeypatch.setattr(auth, "get_credentials", lambda quota_project=None: ("creds", "default-proj"))
    monkeypatch.setattr(bigquery, "Client", lambda project, credentials: project)
    assert auth.make_bigquery_client(None) == "default-proj"
