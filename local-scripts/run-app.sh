#!/bin/bash
#source myenv/bin/activate
# Required
export DB_PASSWORD=''

# Optional (will use defaults if not set)
export DB_HOST="cfapgada-cluster.cluster-cq3nyfn9rutv.us-east-1.rds.amazonaws.com"
export DB_PORT="5432"
export DB_NAME="cfapgda"
export DB_USER="incidentuser"
#export AWS_PROFILE="cccis-estimating-nonprod-dev"
export AWS_ACCESS_KEY_ID="ASIA4YXUBRY5JL6FE4CZ"
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""
export HOST = "127.0.0.1"
export PORT="5200"
export CONTEXT_PATH="/ai-assistant"
export MICROSOFT_APP_ID = "1833927a-479c-4dc9-8a75-32345c55faf4"
export MICROSOFT_APP_PASSWORD = ""
export MICROSOFT_TENANT_ID = "1a188ae6-a002-4149-8234-e47371d17cce"
export MICROSOFT_APP_TYPE="SingleTenant"
python app.py
