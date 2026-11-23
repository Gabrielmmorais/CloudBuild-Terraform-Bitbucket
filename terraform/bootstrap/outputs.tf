output "artifact_registry_repository_url" {
  description = "Docker repository URL, e.g. us-central1-docker.pkg.dev/my-gcp-project/cloudbuild-demo."
  value       = "${google_artifact_registry_repository.images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "build_service_account_email" {
  description = "Service account to select on the Cloud Build trigger."
  value       = google_service_account.build.email
}

output "runtime_service_account_email" {
  description = "Service account passed to the service layer as runtime_service_account_email."
  value       = google_service_account.runtime.email
}
