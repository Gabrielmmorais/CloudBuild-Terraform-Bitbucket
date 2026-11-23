# Uses Application Default auth (ADC): `gcloud auth application-default login`
# locally, the trigger service account inside Cloud Build. No key files.
provider "google" {
  project = var.project_id
  region  = var.region
}
