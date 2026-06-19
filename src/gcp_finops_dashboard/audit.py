"""Resource audit — flag wasteful or non-compliant GCP resources.

Detection relies only on the *listing* APIs (Compute, Storage, Functions),
never on Cloud Monitoring, so the rules below are pure functions over already
listed objects. That keeps them deterministic and unit-testable without
credentials — the GCP I/O lives entirely in :mod:`auth` and the thin
``_list_*`` helpers here.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from gcp_finops_dashboard.models import ResourceFinding


def _labels_of(obj: Any) -> dict[str, str]:
    """Best-effort label extraction across GCP client object shapes."""
    labels = getattr(obj, "labels", None)
    if not labels:
        return {}
    # proto-plus MapComposite and plain dicts both support dict().
    try:
        return dict(labels)
    except (TypeError, ValueError):
        return {}


def _missing_labels(obj: Any, required_labels: Iterable[str]) -> list[str]:
    """Return the required label keys absent (or empty) on ``obj``."""
    present = _labels_of(obj)
    return [key for key in required_labels if not present.get(key)]


def _short(value: str) -> str:
    """Trailing path segment of a GCP self-link/zone URL (or the value as-is)."""
    return value.rsplit("/", 1)[-1] if value else ""


def check_instance(instance: Any, project_id: str, required_labels: list[str]) -> list[ResourceFinding]:
    """Flag a Compute Engine instance that is stopped or missing labels."""
    findings: list[ResourceFinding] = []
    name = getattr(instance, "name", "")
    zone = _short(getattr(instance, "zone", "") or "")
    status = getattr(instance, "status", "") or ""

    if status == "TERMINATED":
        findings.append(
            ResourceFinding(
                resource_type="compute_instance",
                name=name,
                project_id=project_id,
                location=zone,
                issue="stopped",
                detail="Instance is TERMINATED but still reserves disks/IPs that may bill.",
            )
        )

    missing = _missing_labels(instance, required_labels)
    if missing:
        findings.append(
            ResourceFinding(
                resource_type="compute_instance",
                name=name,
                project_id=project_id,
                location=zone,
                issue="untagged",
                detail=f"Missing required label(s): {', '.join(missing)}.",
            )
        )
    return findings


def check_disk(disk: Any, project_id: str, required_labels: list[str]) -> list[ResourceFinding]:
    """Flag an unattached persistent disk or one missing labels."""
    findings: list[ResourceFinding] = []
    name = getattr(disk, "name", "")
    zone = _short(getattr(disk, "zone", "") or getattr(disk, "region", "") or "")

    if not getattr(disk, "users", None):
        size = getattr(disk, "size_gb", None)
        size_note = f" ({size} GB)" if size else ""
        findings.append(
            ResourceFinding(
                resource_type="persistent_disk",
                name=name,
                project_id=project_id,
                location=zone,
                issue="unattached",
                detail=f"Disk is not attached to any instance{size_note} but still bills.",
            )
        )

    missing = _missing_labels(disk, required_labels)
    if missing:
        findings.append(
            ResourceFinding(
                resource_type="persistent_disk",
                name=name,
                project_id=project_id,
                location=zone,
                issue="untagged",
                detail=f"Missing required label(s): {', '.join(missing)}.",
            )
        )
    return findings


def check_address(address: Any, project_id: str) -> list[ResourceFinding]:
    """Flag a reserved-but-unused static IP address (these bill while idle)."""
    name = getattr(address, "name", "")
    region = _short(getattr(address, "region", "") or "")
    status = getattr(address, "status", "") or ""
    if status == "RESERVED":
        return [
            ResourceFinding(
                resource_type="static_ip",
                name=name,
                project_id=project_id,
                location=region or "global",
                issue="idle",
                detail="Static IP is RESERVED but not in use; reserved unused IPs bill.",
            )
        ]
    return []


def check_bucket(bucket: Any, project_id: str, required_labels: list[str]) -> list[ResourceFinding]:
    """Flag a GCS bucket with no lifecycle rules or missing labels."""
    findings: list[ResourceFinding] = []
    name = getattr(bucket, "name", "")
    location = getattr(bucket, "location", "") or ""

    lifecycle_rules = getattr(bucket, "lifecycle_rules", None)
    # google-cloud-storage exposes lifecycle_rules as an iterator; materialise it.
    has_lifecycle = bool(list(lifecycle_rules)) if lifecycle_rules else False
    if not has_lifecycle:
        findings.append(
            ResourceFinding(
                resource_type="gcs_bucket",
                name=name,
                project_id=project_id,
                location=location,
                issue="no_lifecycle",
                detail="Bucket has no lifecycle rules; old objects accumulate cost.",
            )
        )

    missing = _missing_labels(bucket, required_labels)
    if missing:
        findings.append(
            ResourceFinding(
                resource_type="gcs_bucket",
                name=name,
                project_id=project_id,
                location=location,
                issue="untagged",
                detail=f"Missing required label(s): {', '.join(missing)}.",
            )
        )
    return findings


def check_function(function: Any, project_id: str, required_labels: list[str]) -> list[ResourceFinding]:
    """Flag a Cloud Function missing required labels."""
    name = _short(getattr(function, "name", ""))
    missing = _missing_labels(function, required_labels)
    if missing:
        return [
            ResourceFinding(
                resource_type="cloud_function",
                name=name,
                project_id=project_id,
                location="",
                issue="untagged",
                detail=f"Missing required label(s): {', '.join(missing)}.",
            )
        ]
    return []


class AuditClients:
    """Bundle of GCP clients the audit needs (created lazily by the caller).

    Any client may be ``None`` to skip that resource type — useful in tests and
    when a particular API is not enabled.
    """

    def __init__(
        self,
        instances: Any = None,
        disks: Any = None,
        addresses: Any = None,
        storage: Any = None,
        functions: Any = None,
    ) -> None:
        self.instances = instances
        self.disks = disks
        self.addresses = addresses
        self.storage = storage
        self.functions = functions


def run_audit(
    clients: AuditClients,
    project_ids: list[str],
    required_labels: list[str] | None = None,
) -> list[ResourceFinding]:
    """Audit every project in ``project_ids`` and return all findings.

    Listing failures for a single project/resource are swallowed so a missing
    API or permission on one project never aborts the whole run.
    """
    required = required_labels or []
    findings: list[ResourceFinding] = []

    for project_id in project_ids:
        if clients.instances is not None:
            for inst in _safe_list(lambda: _list_instances(clients.instances, project_id)):
                findings.extend(check_instance(inst, project_id, required))
        if clients.disks is not None:
            for disk in _safe_list(lambda: _list_disks(clients.disks, project_id)):
                findings.extend(check_disk(disk, project_id, required))
        if clients.addresses is not None:
            for addr in _safe_list(lambda: _list_addresses(clients.addresses, project_id)):
                findings.extend(check_address(addr, project_id))
        if clients.storage is not None:
            for bucket in _safe_list(lambda: _list_buckets(clients.storage, project_id)):
                findings.extend(check_bucket(bucket, project_id, required))
        if clients.functions is not None:
            for fn in _safe_list(lambda: _list_functions(clients.functions, project_id)):
                findings.extend(check_function(fn, project_id, required))

    return findings


def _safe_list(fetch: Any) -> Iterable[Any]:
    try:
        return list(fetch())
    except Exception:  # noqa: BLE001 - one project's failure must not abort the audit
        return []


# --- Thin listing helpers (the only GCP I/O in this module) -----------------


def _list_instances(client: Any, project_id: str) -> Iterable[Any]:
    """Aggregated list of all instances across zones in a project."""
    from google.cloud import compute_v1

    request = compute_v1.AggregatedListInstancesRequest(project=project_id)
    for _zone, scoped in client.aggregated_list(request=request):
        for instance in getattr(scoped, "instances", []) or []:
            yield instance


def _list_disks(client: Any, project_id: str) -> Iterable[Any]:
    from google.cloud import compute_v1

    request = compute_v1.AggregatedListDisksRequest(project=project_id)
    for _zone, scoped in client.aggregated_list(request=request):
        for disk in getattr(scoped, "disks", []) or []:
            yield disk


def _list_addresses(client: Any, project_id: str) -> Iterable[Any]:
    from google.cloud import compute_v1

    request = compute_v1.AggregatedListAddressesRequest(project=project_id)
    for _region, scoped in client.aggregated_list(request=request):
        for address in getattr(scoped, "addresses", []) or []:
            yield address


def _list_buckets(client: Any, project_id: str) -> Iterable[Any]:
    return client.list_buckets(project=project_id)


def _list_functions(client: Any, project_id: str) -> Iterable[Any]:
    from google.cloud import functions_v2

    parent = f"projects/{project_id}/locations/-"
    request = functions_v2.ListFunctionsRequest(parent=parent)
    return client.list_functions(request=request)
