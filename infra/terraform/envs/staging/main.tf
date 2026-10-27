# Staging: the web app and the API on Cloud Run. Images are rolled out by the deploy
# workflow on every push to main; this root owns everything else about the services.

terraform {
  required_version = ">= 1.10"

  backend "gcs" {
    bucket = "lug-to-lug-tfstate"
    prefix = "envs/staging"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.8"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "The dedicated Google Cloud project for Lug to Lug."
  type        = string
  default     = "lug-to-lug"
}

variable "region" {
  description = "Cloud Run region (ADR-0003)."
  type        = string
  default     = "asia-south1"
}

module "api" {
  source = "../../modules/cloud-run-service"

  name            = "api-staging"
  region          = var.region
  service_account = "api-runtime@${var.project_id}.iam.gserviceaccount.com"
  env = {
    ENVIRONMENT = "staging"
  }
}

module "web" {
  source = "../../modules/cloud-run-service"

  name            = "web-staging"
  region          = var.region
  service_account = "web-runtime@${var.project_id}.iam.gserviceaccount.com"
  env = {
    ENVIRONMENT = "staging"
    API_URL     = module.api.uri
  }
}

output "api_url" {
  description = "Staging API address."
  value       = module.api.uri
}

output "web_url" {
  description = "Staging web app address."
  value       = module.web.uri
}
