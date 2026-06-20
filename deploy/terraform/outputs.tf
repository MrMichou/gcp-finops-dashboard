output "service_account_email" {
  description = "Email of the created service account. Annotate the Helm KSA with this (serviceAccount.annotations 'iam.gke.io/gcp-service-account')."
  value       = google_service_account.finops.email
}

output "service_account_name" {
  description = "Fully-qualified resource name of the service account."
  value       = google_service_account.finops.name
}

output "workload_identity_member" {
  description = "The Workload Identity member string bound to the GSA (empty if disabled)."
  value       = var.workload_identity.enabled ? "serviceAccount:${var.project_id}.svc.id.goog[${var.workload_identity.namespace}/${var.workload_identity.kubernetes_sa_name}]" : ""
}
