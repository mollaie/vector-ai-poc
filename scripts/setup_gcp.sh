#!/bin/bash
# Google Cloud Platform Setup Script for Vector AI PoC
# This script helps configure your GCP project for the job matching PoC

set -e

echo "==================================="
echo "Vector AI PoC - GCP Setup Script"
echo "==================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
if [ -z "$1" ]; then
    echo ""
    echo "Usage: ./setup_gcp.sh <PROJECT_ID> [REGION]"
    echo ""
    echo "Example: ./setup_gcp.sh my-project-123 us-central1"
    echo ""
    
    # Try to get current project
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ -n "$CURRENT_PROJECT" ]; then
        echo "Current project: $CURRENT_PROJECT"
        read -p "Use this project? (y/n): " USE_CURRENT
        if [ "$USE_CURRENT" = "y" ]; then
            PROJECT_ID=$CURRENT_PROJECT
        else
            exit 1
        fi
    else
        exit 1
    fi
else
    PROJECT_ID=$1
fi

REGION=${2:-us-central1}

echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Confirm
read -p "Continue with setup? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Setup cancelled."
    exit 0
fi

# Set the project
echo ""
echo "Setting project..."
gcloud config set project $PROJECT_ID

# Authenticate (if needed)
echo ""
echo "Checking authentication..."
if ! gcloud auth print-access-token &> /dev/null; then
    echo "Authenticating..."
    gcloud auth login
fi

# Set up application default credentials
echo ""
echo "Setting up application default credentials..."
gcloud auth application-default login

# Enable required APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable compute.googleapis.com

# Create GCS bucket for embeddings
BUCKET_NAME="${PROJECT_ID}-vector-poc-embeddings"
echo ""
echo "Creating GCS bucket: $BUCKET_NAME..."
if gsutil ls gs://$BUCKET_NAME &> /dev/null; then
    echo "Bucket already exists."
else
    gsutil mb -l $REGION gs://$BUCKET_NAME
    echo "Bucket created."
fi

# Create .env file
ENV_FILE="../.env"
echo ""
echo "Creating .env file..."
cat > $ENV_FILE << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_REGION=$REGION

# Google Cloud Storage bucket for embeddings
GCS_BUCKET=$BUCKET_NAME

# Model Configuration
EMBEDDING_MODEL=text-embedding-005
GEMINI_MODEL=gemini-2.5-flash

# Vector Search Configuration (populated after index creation)
VECTOR_SEARCH_INDEX_ID=
VECTOR_SEARCH_ENDPOINT_ID=
DEPLOYED_INDEX_ID=job-vacancies-deployed

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
EOF

echo ".env file created."

echo ""
echo "==================================="
echo "GCP Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Generate mock data: python scripts/generate_data.py"
echo "2. Create embeddings: python scripts/create_embeddings.py"
echo "3. Deploy index: python scripts/deploy_index.py"
echo "4. Start the API: python -m src.api.main"
echo ""

