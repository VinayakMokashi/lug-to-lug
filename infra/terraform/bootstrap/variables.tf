variable "project_id" {
  description = "The dedicated Google Cloud project for Lug to Lug."
  type        = string
  default     = "lug-to-lug"
}

variable "region" {
  description = "Region for Cloud Run, Artifact Registry and buckets (ADR-0003)."
  type        = string
  default     = "asia-south1"
}

variable "billing_account" {
  description = "Billing account ID that pays for the project. Kept out of the repository: pass it as TF_VAR_billing_account."
  type        = string
  sensitive   = true
}

variable "monthly_budget_usd" {
  description = "Monthly budget for the project, measured before credits so the trial credit can't hide spending."
  type        = number
  default     = 10
}

variable "github_repository_id" {
  description = "Numeric ID of the GitHub repository allowed to deploy (stable across renames and transfers)."
  type        = string
  default     = "1433709982"
}

variable "github_owner_id" {
  description = "Numeric ID of the repository owner on GitHub."
  type        = string
  default     = "88434571"
}

variable "secrets" {
  description = "Secret Manager secrets. Terraform creates them empty; values are added with gcloud, so they never enter the Terraform state."
  type        = set(string)
  default     = ["neon-database-url", "modal-token-id", "modal-token-secret"]
}
