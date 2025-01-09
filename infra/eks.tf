# EKS Cluster
resource "aws_eks_cluster" "app_cluster" {
  name     = "sedef-dict-app-cluster"
  role_arn = aws_iam_role.eks_cluster_role.arn

  vpc_config {
    subnet_ids          = aws_subnet.app_subnets[*].id
    security_group_ids  = [aws_security_group.eks_security_group.id]
  }

  tags = {
    Name = "sedef-dict-app-cluster"
  }
}

# EKS Node Group
resource "aws_eks_node_group" "app_node_group" {
  cluster_name    = aws_eks_cluster.app_cluster.name
  node_group_name = "sedef-dict-node-group"
  node_role_arn   = aws_iam_role.eks_node_role.arn

  subnet_ids = aws_subnet.app_subnets[*].id

  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }

  tags = {
    Name = "sedef-dict-node-group"
  }
}
