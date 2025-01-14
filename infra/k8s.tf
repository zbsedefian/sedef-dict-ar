provider "kubernetes" {
  host                   = aws_eks_cluster.app_cluster.endpoint
  token                  = data.aws_eks_cluster_auth.app.token
  cluster_ca_certificate = base64decode(aws_eks_cluster.app_cluster.certificate_authority[0].data)
}

data "aws_eks_cluster_auth" "app" {
  name = aws_eks_cluster.app_cluster.name
}

resource "kubernetes_config_map" "env" {
  metadata {
    name = "env"
  }

  data = {
    OPEN_API_KEY = var.open_api_key  # Pass this as a Terraform variable
  }
}

resource "kubernetes_deployment" "arabic_dict_app" {
  metadata {
    name = "arabic-dict-app"
    labels = {
      app = "arabic-dict-app"
    }
  }

  spec {
    replicas = 2

    selector {
      match_labels = {
        app = "arabic-dict-app"
      }
    }

    template {
      metadata {
        labels = {
          app = "arabic-dict-app"
        }
      }

      spec {
        container {
          name  = "arabic-dict-app"
          image = "864899862988.dkr.ecr.us-east-2.amazonaws.com/arabic-dict-api:latest"

          args = [
            "uvicorn",
            "arabic_dict_api:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000"
          ]

          env {
            name = "OPEN_API_KEY"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.env.metadata[0].name
                key  = "OPEN_API_KEY"
              }
            }
          }

          port {
            container_port = 8000
            protocol       = "TCP"
          }

          resources {
            requests = {
              memory = "128Mi"
              cpu    = "100m"
            }

            limits = {
              memory = "256Mi"
              cpu    = "500m"
            }
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 10
            period_seconds        = 30
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
        }

        restart_policy = "Always"
      }
    }
  }
}

resource "kubernetes_service" "arabic_dict_service" {
  metadata {
    name = "arabic-dict-service"
  }

  spec {
    selector = {
      app = kubernetes_deployment.arabic_dict_app.metadata[0].labels.app
    }

    port {
      protocol    = "TCP"
      port        = 80
      target_port = 8000
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_ingress" "arabic_dict_ingress" {
  metadata {
    name = "arabic-dict-ingress"
    annotations = {
      "alb.ingress.kubernetes.io/scheme"       = "internet-facing"
      "alb.ingress.kubernetes.io/target-type"  = "ip"
      "alb.ingress.kubernetes.io/listen-ports" = "[{\"HTTP\": 80}]"
    }
    labels = {
      app = "arabic-dict-app"
    }
  }

  spec {
    ingress_class_name = "alb"

    rule {
      http {
        path {
          path      = "/"

          backend {
            service_name = kubernetes_service.arabic_dict_service.metadata[0].name
            service_port = 80
          }
        }
      }
    }
  }
}

output "eks_cluster_name" {
  value = aws_eks_cluster.app_cluster.name
  description = "The name of the created EKS cluster."
}

resource "null_resource" "update_kubeconfig" {
  provisioner "local-exec" {
    command = "aws eks update-kubeconfig --region ${var.region} --name ${aws_eks_cluster.app_cluster.name}"
  }
  depends_on = [aws_eks_cluster.app_cluster]
}