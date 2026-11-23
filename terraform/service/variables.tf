variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Cloud Run region."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "cloudbuild-demo"
}

variable "image" {
  description = "Full container image URI including tag, e.g. us-central1-docker.pkg.dev/my-gcp-project/cloudbuild-demo/web:abc1234."
  type        = string

  validation {
    condition     = can(regex(":[^/]+$", var.image)) || can(regex("@sha256:", var.image))
    error_message = "image must include a tag or digest (avoid implicit :latest)."
  }
}

variable "runtime_service_account_email" {
  description = "Service account the service runs as (bootstrap output runtime_service_account_email)."
  type        = string
}

variable "allow_unauthenticated" {
  description = "Grant roles/run.invoker to allUsers, making the service public."
  type        = bool
  default     = false
}

variable "min_instance_count" {
  description = "Minimum number of instances (0 allows scale to zero)."
  type        = number
  default     = 0

  validation {
    condition     = var.min_instance_count >= 0
    error_message = "min_instance_count must be >= 0."
  }
}

variable "max_instance_count" {
  description = "Maximum number of instances."
  type        = number
  default     = 2

  validation {
    condition     = var.max_instance_count >= 1 && var.max_instance_count >= var.min_instance_count
    error_message = "max_instance_count must be >= 1 and >= min_instance_count."
  }
}

variable "cpu" {
  description = "CPU limit per instance."
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit per instance."
  type        = string
  default     = "512Mi"
}

variable "container_port" {
  description = "Port the container listens on."
  type        = number
  default     = 8080
}

variable "deletion_protection" {
  description = "Block terraform destroy of the service. Defaults to false because this is a demo; set true for real workloads."
  type        = bool
  default     = false
}
