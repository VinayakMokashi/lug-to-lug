# A Cloud Run service that scales to zero. Terraform owns its configuration; the
# deploy workflow owns the image, so a deploy never shows up as drift here.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.8"
    }
  }
}

resource "google_cloud_run_v2_service" "this" {
  name                = var.name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.deletion_protection

  template {
    service_account                  = var.service_account
    max_instance_request_concurrency = var.concurrency
    timeout                          = "${var.timeout_seconds}s"

    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      # The first image is Google's sample; every deploy replaces it.
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = var.memory
        }
        cpu_idle          = true # CPU is billed only while a request is in flight
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.public ? 1 : 0

  name     = google_cloud_run_v2_service.this.name
  location = google_cloud_run_v2_service.this.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
