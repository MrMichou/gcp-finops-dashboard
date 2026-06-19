"""Credential resolution and GCP client factories.

All clients use Application Default Credentials (ADC). Resolution order, handled
by ``google.auth.default``:

1. ``GOOGLE_APPLICATION_CREDENTIALS`` pointing at a service-account JSON key.
2. ``gcloud auth application-default login`` user credentials.
3. The attached service account (GCE / Cloud Run metadata server).

Centralising client creation here keeps GCP I/O in one place and makes the data
sources trivial to mock in tests.
"""

from __future__ import annotations

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class AuthError(Exception):
    """Raised when credentials cannot be resolved, with remediation guidance."""


def get_credentials(quota_project: str | None = None):
    """Return ``(credentials, project_id)`` via ADC.

    Raises :class:`AuthError` with actionable guidance when no credentials are
    available, instead of leaking the raw library exception.
    """
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    try:
        credentials, project_id = google.auth.default(scopes=_SCOPES)
    except DefaultCredentialsError as exc:
        raise AuthError(
            "Could not find Google Cloud credentials. Authenticate with one of:\n"
            "  - gcloud auth application-default login\n"
            "  - export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json"
        ) from exc

    if quota_project and hasattr(credentials, "with_quota_project"):
        credentials = credentials.with_quota_project(quota_project)
    return credentials, project_id


def make_bigquery_client(billing_project: str | None = None):
    """Client used to run billing-export queries (``billing_project`` pays)."""
    from google.cloud import bigquery

    credentials, default_project = get_credentials(quota_project=billing_project)
    return bigquery.Client(
        project=billing_project or default_project, credentials=credentials
    )


def make_budgets_client():
    from google.cloud.billing import budgets_v1

    credentials, _ = get_credentials()
    return budgets_v1.BudgetServiceClient(credentials=credentials)


def make_billing_client():
    from google.cloud import billing_v1

    credentials, _ = get_credentials()
    return billing_v1.CloudBillingClient(credentials=credentials)


def make_projects_client():
    from google.cloud import resourcemanager_v3

    credentials, _ = get_credentials()
    return resourcemanager_v3.ProjectsClient(credentials=credentials)


def make_compute_instances_client():
    from google.cloud import compute_v1

    credentials, _ = get_credentials()
    return compute_v1.InstancesClient(credentials=credentials)


def make_compute_disks_client():
    from google.cloud import compute_v1

    credentials, _ = get_credentials()
    return compute_v1.DisksClient(credentials=credentials)


def make_compute_addresses_client():
    from google.cloud import compute_v1

    credentials, _ = get_credentials()
    return compute_v1.AddressesClient(credentials=credentials)


def make_storage_client(project: str | None = None):
    from google.cloud import storage

    credentials, default_project = get_credentials(quota_project=project)
    return storage.Client(project=project or default_project, credentials=credentials)


def make_functions_client():
    from google.cloud import functions_v2

    credentials, _ = get_credentials()
    return functions_v2.FunctionServiceClient(credentials=credentials)
