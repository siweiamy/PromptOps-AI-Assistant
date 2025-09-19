# Requires PowerShell

# Required
$env:DB_PASSWORD = ''

# Optional (will use defaults if not set)
$env:DB_HOST = "cfapgada-cluster.cluster-cq3nyfn9rutv.us-east-1.rds.amazonaws.com"
$env:DB_PORT = "5432"
$env:DB_NAME = "cfapgda"
$env:DB_USER = "incidentuser"
#$env:AWS_PROFILE = "cccis-estimating-nonprod-dev"
$env:AWS_ACCESS_KEY_ID="ASIASPENLKCL4BOS27HR"
$env:AWS_SECRET_ACCESS_KEY=""
$env:AWS_SESSION_TOKEN=""
$env:HOST = "127.0.0.1"
$env:PORT = "5200"
$env:CONTEXT_PATH = "/ai-assistant"
$env:MICROSOFT_APP_ID = "1833927a-479c-4dc9-8a75-32345c55faf4"
$env:MICROSOFT_APP_PASSWORD = ""
$env:MICROSOFT_TENANT_ID = "1a188ae6-a002-4149-8234-e47371d17cce"
$env:MICROSOFT_APP_TYPE="SingleTenant"

python app.py
