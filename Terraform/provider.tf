terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.10.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "5.10.0"
    }
  }
}
##teste
provider "google" {
  credentials = file("tcb-k8s-394716-8b1b906a988b.json")
  project     = var.project_id
  region      = "us-west1"
  zone        = "us-west1-a"
  #request_timeout = "60s"
}


provider "google-beta" {
  credentials = file("tcb-k8s-394716-8b1b906a988b.json")
  project     = var.project_id
  region      = "us-west1"
  zone        = "us-west1-a"
  #request_timeout = "60s"
}