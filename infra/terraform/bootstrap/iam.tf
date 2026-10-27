# Keyless deploys: GitHub Actions exchanges its OIDC token for a short-lived token of
# the deployer service account. Only this repository's main branch is accepted, and no
# service-account key exists anywhere (ADR-0003).

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "Deploys from the lug-to-lug repository"

  depends_on = [google_project_service.this]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "lug-to-lug"
  display_name                       = "lug-to-lug repository"

  attribute_mapping = {
    "google.subject"          = "assertion.sub"
    "attribute.repository"    = "assertion.repository"
    "attribute.repository_id" = "assertion.repository_id"
    "attribute.ref"           = "assertion.ref"
  }
  attribute_condition = join(" && ", [
    "assertion.repository_id == '${var.github_repository_id}'",
    "assertion.repository_owner_id == '${var.github_owner_id}'",
    "assertion.ref == 'refs/heads/main'",
  ])

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# The identities the services run as. Each gets access to a secret only when its
# service starts using it.
resource "google_service_account" "runtime" {
  for_each = {
    api = "Lug to Lug API at runtime"
    web = "Lug to Lug web app at runtime"
  }

  account_id   = "${each.key}-runtime"
  display_name = each.value

  depends_on = [google_project_service.this]
}

resource "google_service_account" "deployer" {
  account_id   = "github-deployer"
  display_name = "GitHub Actions deployer"
  description  = "Pushes images and rolls out Cloud Run revisions from main"

  depends_on = [google_project_service.this]
}

resource "google_service_account_iam_member" "deployer_from_github" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${var.github_repository_id}"
}

resource "google_artifact_registry_repository_iam_member" "deployer_pushes_images" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.repository_id
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.deployer.member
}

# Update services and roll out revisions, but not change who may call them.
resource "google_project_iam_member" "deployer_updates_services" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = google_service_account.deployer.member
}

# A new revision runs as its runtime account, so the deployer must be allowed to act as it.
resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  for_each = google_service_account.runtime

  service_account_id = each.value.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deployer.member
}
