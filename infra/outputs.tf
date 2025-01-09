output "cluster_endpoint" {
  value = aws_eks_cluster.app_cluster.endpoint
}

output "cluster_security_group_id" {
  value = aws_security_group.eks_security_group.id
}

output "node_group_name" {
  value = aws_eks_node_group.app_node_group.node_group_name
}
