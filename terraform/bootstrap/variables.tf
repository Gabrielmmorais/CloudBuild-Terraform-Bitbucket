variable "project_id" {
  description = "GCP project ID where all resources are created."
  type        = string
}

variable "region" {
  description = "Region for the Artifact Registry repository."
  type        = string
  default     = "us-central1"
}

variable "repository_id" {
  description = "Artifact Registry repository ID that stores the container images."
  type        = string
  default     = "cloudbuild-demo"
}

variable "build_service_account_id" {
  description = "Account ID of the service account Cloud Build runs as."
  type        = string
  default     = "cloudbuild-deployer"
}

variable "runtime_service_account_id" {
  description = "Account ID of the identity the Cloud Run service runs as."
  type        = string
  default     = "cloudrun-runtime"
}

variable "tf_state_bucket" {
  description = "Existing GCS bucket holding Terraform state. Only used to grant the build service account access."
  type        = string
}
