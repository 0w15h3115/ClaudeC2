#!/bin/bash
# Deploy C2 Framework

set -e

# Configuration
DEPLOY_USER="c2admin"
DEPLOY_HOST="c2.example.com"
DEPLOY_PATH="/opt/c2-framework"
DEPLOY_ENV="production"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

# Check arguments
if [ "$1" == "--help" ]; then
    echo "Usage: $0 [environment]"
    echo "Environments: production, staging, development"
    exit 0
fi

if [ ! -z "$1" ]; then
    DEPLOY_ENV=$1
fi

print_status "Deploying to $DEPLOY_ENV environment..."

# Build Docker images
print_status "Building Docker images..."
docker-compose build

# Tag images
docker tag c2-framework_server:latest $DEPLOY_USER@$DEPLOY_HOST:5000/c2-server:$DEPLOY_ENV
docker tag c2-framework_client:latest $DEPLOY_USER@$DEPLOY_HOST:5000/c2-client:$DEPLOY_ENV

# Push images
print_status "Pushing images to registry..."
docker push $DEPLOY_USER@$DEPLOY_HOST:5000/c2-server:$DEPLOY_ENV
docker push $DEPLOY_USER@$DEPLOY_HOST:5000/c2-client:$DEPLOY_ENV

# Deploy via SSH
print_status "Deploying to remote server..."
ssh $DEPLOY_USER@$DEPLOY_HOST << EOF
    cd $DEPLOY_PATH
    
    # Backup current deployment
    if [ -d "current" ]; then
        mv current backup-$(date +%Y%m%d-%H%M%S)
    fi
    
    # Pull latest code
    git pull origin main
    
    # Update images
    docker-compose pull
    
    # Run database migrations
    docker-compose run --rm server alembic upgrade head
    
    # Restart services
    docker-compose down
    docker-compose up -d
    
    # Health check
    sleep 10
    curl -f http://localhost:8000/api/health || exit 1
EOF

print_status "Deployment complete!"
print_status "Access the C2 server at https://$DEPLOY_HOST"
