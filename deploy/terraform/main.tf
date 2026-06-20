locals {
  export_project = coalesce(var.billing_export_project_id, var.project_id)
}

# Identity the dashboard runs as.
resource "google_service_account" "finops" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = "GCP FinOps Dashboard"
  description  = "Runs the gcp-finops-dashboard CronJob (read-only cost/budget/audit access)."
}

# --- BigQuery: read the billing-export dataset and run query jobs -----------
resource "google_project_iam_member" "bq_data_viewer" {
  count   = var.grant_bigquery_roles ? 1 : 0
  project = local.export_project
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.finops.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  count   = var.grant_bigquery_roles ? 1 : 0
  project = local.export_project
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.finops.email}"
}

# --- Budgets: billing.budgets.list at the billing-account level --------------
resource "google_billing_account_iam_member" "budgets_viewer" {
  billing_account_id = var.billing_account_id
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.finops.email}"
}

# --- Resource audit (--audit): read-only listing on audited projects --------
resource "google_project_iam_member" "audit_viewer" {
  for_each = toset(var.audited_project_ids)
  project  = each.value
  role     = "roles/viewer"
  member   = "serviceAccount:${google_service_account.finops.email}"
}

# --- Workload Identity: let the GKE KSA impersonate this GSA -----------------
resource "google_service_account_iam_member" "workload_identity" {
  count              = var.workload_identity.enabled ? 1 : 0
  service_account_id = google_service_account.finops.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.workload_identity.namespace}/${var.workload_identity.kubernetes_sa_name}]"
}
