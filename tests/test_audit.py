"""Resource-audit detection rules — pure, offline, no GCP credentials."""

from __future__ import annotations

from types import SimpleNamespace

from gcp_finops_dashboard import audit
from gcp_finops_dashboard.audit import AuditClients, run_audit


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


# --- Compute instances ------------------------------------------------------


def test_terminated_instance_flagged_stopped():
    inst = ns(name="vm-1", zone="proj/zones/us-central1-a", status="TERMINATED", labels={})
    findings = audit.check_instance(inst, "proj", required_labels=[])
    assert [f.issue for f in findings] == ["stopped"]
    assert findings[0].location == "us-central1-a"
    assert findings[0].resource_type == "compute_instance"


def test_running_instance_not_flagged_when_labelled():
    inst = ns(name="vm-2", zone="proj/zones/us-central1-a", status="RUNNING", labels={"team": "x"})
    assert audit.check_instance(inst, "proj", required_labels=["team"]) == []


def test_instance_missing_label_flagged_untagged():
    inst = ns(name="vm-3", zone="proj/zones/eu-west1-b", status="RUNNING", labels={"env": "prod"})
    findings = audit.check_instance(inst, "proj", required_labels=["team", "env"])
    assert len(findings) == 1
    assert findings[0].issue == "untagged"
    assert "team" in findings[0].detail


# --- Persistent disks -------------------------------------------------------


def test_unattached_disk_flagged():
    disk = ns(name="disk-1", zone="proj/zones/us-central1-a", users=[], size_gb=200, labels={})
    findings = audit.check_disk(disk, "proj", required_labels=[])
    assert [f.issue for f in findings] == ["unattached"]
    assert "200 GB" in findings[0].detail


def test_attached_disk_not_flagged():
    disk = ns(name="disk-2", zone="z", users=["vm-1"], size_gb=50, labels={"team": "x"})
    assert audit.check_disk(disk, "proj", required_labels=["team"]) == []


# --- Static IP addresses ----------------------------------------------------


def test_reserved_address_flagged_idle():
    addr = ns(name="ip-1", region="proj/regions/us-central1", status="RESERVED")
    findings = audit.check_address(addr, "proj")
    assert [f.issue for f in findings] == ["idle"]
    assert findings[0].location == "us-central1"


def test_in_use_address_not_flagged():
    addr = ns(name="ip-2", region="proj/regions/us-central1", status="IN_USE")
    assert audit.check_address(addr, "proj") == []


def test_reserved_address_with_users_not_flagged():
    # Some attached addresses still report RESERVED; a non-empty `users` means
    # the address is in use and must not be flagged as idle.
    addr = ns(
        name="ip-3",
        region="proj/regions/us-central1",
        status="RESERVED",
        users=["projects/proj/.../forwardingRules/fr-1"],
    )
    assert audit.check_address(addr, "proj") == []


def test_reserved_address_without_users_flagged():
    addr = ns(name="ip-4", region="proj/regions/us-central1", status="RESERVED", users=[])
    findings = audit.check_address(addr, "proj")
    assert [f.issue for f in findings] == ["idle"]


# --- GCS buckets ------------------------------------------------------------


def test_bucket_without_lifecycle_flagged():
    bucket = ns(name="b-1", location="US", lifecycle_rules=[], labels={"team": "x"})
    findings = audit.check_bucket(bucket, "proj", required_labels=["team"])
    assert [f.issue for f in findings] == ["no_lifecycle"]


def test_bucket_with_lifecycle_and_labels_clean():
    bucket = ns(name="b-2", location="US", lifecycle_rules=[{"action": {}}], labels={"team": "x"})
    assert audit.check_bucket(bucket, "proj", required_labels=["team"]) == []


def test_bucket_untagged_and_no_lifecycle_yields_two_findings():
    bucket = ns(name="b-3", location="EU", lifecycle_rules=[], labels={})
    issues = {f.issue for f in audit.check_bucket(bucket, "proj", required_labels=["team"])}
    assert issues == {"no_lifecycle", "untagged"}


# --- Cloud Functions --------------------------------------------------------


def test_function_missing_label_flagged():
    fn = ns(name="projects/p/locations/us/functions/fn-1", labels={})
    findings = audit.check_function(fn, "proj", required_labels=["team"])
    assert [f.issue for f in findings] == ["untagged"]
    assert findings[0].name == "fn-1"


# --- Orchestration ----------------------------------------------------------


class _FakeStorage:
    def __init__(self, buckets):
        self._buckets = buckets

    def list_buckets(self, project):
        assert project == "proj"
        return list(self._buckets)


def test_run_audit_collects_across_clients():
    storage = _FakeStorage([ns(name="b", location="US", lifecycle_rules=[], labels={})])
    clients = AuditClients(storage=storage)
    findings = run_audit(clients, ["proj"], required_labels=[])
    assert len(findings) == 1
    assert findings[0].resource_type == "gcs_bucket"


def test_run_audit_no_clients_returns_empty():
    assert run_audit(AuditClients(), ["proj"]) == []


def test_run_audit_swallows_listing_errors():
    class _Boom:
        def list_buckets(self, project):
            raise RuntimeError("permission denied")

    findings = run_audit(AuditClients(storage=_Boom()), ["proj"])
    assert findings == []


# --- Listing helpers (thin GCP I/O wrappers) --------------------------------


class _FakeAggregatedClient:
    """Mimics a Compute client's ``aggregated_list`` over a single scope."""

    def __init__(self, attr, items):
        self._attr = attr
        self._items = items

    def aggregated_list(self, request=None):
        return [("scope-a", ns(**{self._attr: self._items}))]


def test_list_instances_flattens_zones():
    client = _FakeAggregatedClient("instances", [ns(name="vm-1"), ns(name="vm-2")])
    assert [i.name for i in audit._list_instances(client, "proj")] == ["vm-1", "vm-2"]


def test_list_disks_flattens_zones():
    client = _FakeAggregatedClient("disks", [ns(name="disk-1")])
    assert [d.name for d in audit._list_disks(client, "proj")] == ["disk-1"]


def test_list_addresses_flattens_regions():
    client = _FakeAggregatedClient("addresses", [ns(name="ip-1")])
    assert [a.name for a in audit._list_addresses(client, "proj")] == ["ip-1"]


def test_list_functions_passes_parent():
    class _FakeFunctions:
        def list_functions(self, request=None):
            assert request.parent == "projects/proj/locations/-"
            return [ns(name="fn")]

    assert [f.name for f in audit._list_functions(_FakeFunctions(), "proj")] == ["fn"]


def test_safe_list_returns_empty_on_error():
    def boom():
        raise RuntimeError("nope")

    assert audit._safe_list(boom) == []


# --- run_audit dispatches over every resource type --------------------------


def test_run_audit_flags_terminated_instance():
    inst = ns(name="vm", zone="z/zones/us-a", status="TERMINATED", labels={})
    client = _FakeAggregatedClient("instances", [inst])
    findings = run_audit(AuditClients(instances=client), ["proj"])
    assert [f.issue for f in findings] == ["stopped"]


def test_run_audit_flags_unattached_disk():
    disk = ns(name="d", zone="z/zones/us-a", users=[], size_gb=10, labels={})
    client = _FakeAggregatedClient("disks", [disk])
    findings = run_audit(AuditClients(disks=client), ["proj"])
    assert [f.issue for f in findings] == ["unattached"]


def test_run_audit_flags_reserved_address():
    addr = ns(name="ip", region="r/regions/us-central1", status="RESERVED")
    client = _FakeAggregatedClient("addresses", [addr])
    findings = run_audit(AuditClients(addresses=client), ["proj"])
    assert [f.issue for f in findings] == ["idle"]


def test_run_audit_flags_untagged_function():
    class _FakeFunctions:
        def list_functions(self, request=None):
            return [ns(name="projects/p/locations/us/functions/fn", labels={})]

    findings = run_audit(AuditClients(functions=_FakeFunctions()), ["proj"], ["team"])
    assert [f.issue for f in findings] == ["untagged"]
