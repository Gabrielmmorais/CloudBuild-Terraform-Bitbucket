# TFLint configuration shared by every Terraform stack under terraform/.
# Run from the repository root: tflint --init && tflint --recursive

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "google" {
  enabled = true
  version = "0.41.0"
  source  = "github.com/terraform-linters/tflint-ruleset-google"
}
