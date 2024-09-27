resource "google_artifact_registry_repository" "cloudbuild-html" {
    location     = "us-east1"
    repository_id = "cloudbuild-html"
    description  = ""
    format       = "DOCKER"
}


