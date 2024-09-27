output "image_tag" {
  description = "Tag da imagem Docker gerada pelo Cloud Build"
  value       = "${var.image_tag}"  # Certifique-se de que esta variável tenha um valor definido
}
