#!/bin/bash

if which docker
then
    CMD=docker
elif  which podman
then
    CMD=podman
fi

$CMD kill wf-incident-ai-assistant
$CMD rm wf-incident-ai-assistant
$CMD run \
--detach \
--publish 5200:5200 \
--volume ~/.aws:/home/appuser/.aws \
-e DB_HOST="cfapgada-cluster.cluster-cq3nyfn9rutv.us-east-1.rds.amazonaws.com" \
-e DB_PORT="5432" \
-e DB_NAME="cfapgda" \
-e DB_USER="incidentuser" \
-e AWS_PROFILE="cccis-estimating-nonprod-dev" \
-e AWS_REGION="us-east-1" \
-e PORT="5200" \
-e DB_PASSWORD="\$x" \
-e MICROSOFT_APP_ID = "1833927a-479c-4dc9-8a75-32345c55faf4" \
-e MICROSOFT_APP_PASSWORD = "" \
-e MICROSOFT_TENANT_ID = "1a188ae6-a002-4149-8234-e47371d17cce" \
-e MICROSOFT_APP_TYPE="SingleTenant" \
--name "wf-incident-ai-assistant" \
test

$CMD logs -f wf-incident-ai-assistant
