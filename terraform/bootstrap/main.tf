locals {
  services = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "this" {
  for_each = toset(local.services)

  service = each.value
  # Keep APIs enabled on destroy; other workloads in the project may rely on them.
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Container images built by Cloud Build."
  format        = "DOCKER"

  # Delete policies run only when this is false.
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-10-most-recent"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.this]
}

# Identity used by the Cloud Build trigger to build, push and deploy.
resource "google_service_account" "build" {
  account_id   = var.build_service_account_id
  display_name = "Cloud Build deployer"

  depends_on = [google_project_service.this]
}

# Identity the Cloud Run service runs as. Intentionally has no roles.
resource "google_service_account" "runtime" {
  account_id   = var.runtime_service_account_id
  display_name = "Cloud Run runtime"

  depends_on = [google_project_service.this]
}

# Project-level roles: manage Cloud Run services and write build logs.
resource "google_project_iam_member" "build" {
  for_each = toset([
    "roles/run.admin",
    "roles/logging.logWriter",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.build.member

  depends_on = [google_project_service.this]
}

# Push images to this repository only.
resource "google_artifact_registry_repository_iam_member" "build_writer" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.build.member

  depends_on = [google_project_service.this]
}

# Allow deploying services that run as the runtime SA (and nothing else).
resource "google_service_account_iam_member" "build_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.build.member

  depends_on = [google_project_service.this]
}

# Read/write Terraform state for the service layer.
resource "google_storage_bucket_iam_member" "build_state" {
  bucket = var.tf_state_bucket
  role   = "roles/storage.objectUser"
  member = google_service_account.build.member

  depends_on = [google_project_service.this]
}
