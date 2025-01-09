#!/bin/bash

# Step 1: Freeze dependencies
echo "Freezing dependencies..."
pip freeze > requirements.txt

# Step 2: Build the Docker image
IMAGE_NAME="zsedefian/arabic-dict-api:latest"
ECR_REMOTE_IMAGE="864899862988.dkr.ecr.us-east-2.amazonaws.com/arabic-dict-api:latest"
echo "Building Docker image: $IMAGE_NAME"
docker build --platform=linux/amd64 -t $IMAGE_NAME .

echo "Tagging Docker image: $IMAGE_NAME as $ECR_REMOTE_IMAGE"
docker tag $IMAGE_NAME $ECR_REMOTE_IMAGE

# Step 3: Push the Docker image to a registry (adjust registry as needed)
echo "Pushing Docker image to registry..."
docker push $ECR_REMOTE_IMAGE

# Step 4: Ask for confirmation before deploying
read -p "Ready to deploy? (y/N): " confirmation
if [[ "$confirmation" != "y" ]]; then
    echo "Deployment aborted."
    exit 0
fi

# Step 5: Deploy the image using kubectl (optional)
echo "Deploying to Kubernetes..."
kubectl apply -f k8s/deployment.yaml

echo "Done!"
