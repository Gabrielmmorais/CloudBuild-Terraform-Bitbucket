resource "google_cloud_run_service" "cloudbuild-html" {
  name     = "cloudbuild-html"
  location = "us-east1"

  template {
    spec {
      containers {
        image = "us-east1-docker.pkg.dev/tcb-k8s-394716/cloudbuild-html/cloudbuild-html:${var.image_tag}"
        ports {
          container_port = 8080
        }
        resources {
          limits = {
            memory = "2Gi"
            cpu    = "1"
          }
        }
      }
    }
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "2"
        "autoscaling.knative.dev/maxScale" = "4"
      }
    }
  }

  traffic {
    percent          = 100
    latest_revision  = true
  }

  #depends_on = [google_artifact_registry_repository.cloudbuild-html]
}
