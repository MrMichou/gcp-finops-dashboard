variable "project_id" {
  type        = string
  description = "Project that owns the service account and runs/pays for the BigQuery jobs (the billing-export project is a good choice)."
}

variable "billing_account_id" {
  type        = string
  description = "Cloud Billing account ID (e.g. 01ABCD-23EFGH-456789). Used to grant budget read access at the billing-account level."
}

variable "service_account_id" {
  type        = string
  description = "Account ID (the part before @) of the service account to create."
  default     = "gcp-finops-dashboard"
}

variable "billing_export_project_id" {
  type        = string
  description = "Project that holds the BigQuery billing-export dataset. Defaults to project_id."
  default     = null
}

variable "audited_project_ids" {
  type        = list(string)
  description = <<-EOT
    Project IDs the resource audit (--audit) inspects, each granted roles/viewer.
    Leave empty if you don't use --audit.
  EOT
  default     = []
}

variable "grant_bigquery_roles" {
  type        = bool
  description = "Grant BigQuery Data Viewer + Job User on the billing-export project."
  default     = true
}

variable "workload_identity" {
  type = object({
    enabled            = bool
    namespace          = string
    kubernetes_sa_name = string
  })
  description = <<-EOT
    Bind a GKE Kubernetes ServiceAccount to this GSA via Workload Identity.
    Set enabled=true and match namespace/kubernetes_sa_name to the Helm release
    (serviceAccount.name in values.yaml). The cluster must have Workload
    Identity enabled.
  EOT
  default = {
    enabled            = false
    namespace          = "default"
    kubernetes_sa_name = "gcp-finops-dashboard"
  }
}
