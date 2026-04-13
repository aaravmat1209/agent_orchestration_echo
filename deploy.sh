#!/bin/bash
# =============================================================================
# Deploy script for Echo A2A Multi-Agent Educational Platform
# Designed to run on AWS CloudShell or any bash environment with AWS CLI
# =============================================================================
set -euo pipefail

REGION="us-west-2"
CONFIG_FILE=".a2a.config"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}ℹ $1${NC}"; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $1${NC}"; }
error()   { echo -e "${RED}✗ $1${NC}"; }
header()  { echo -e "\n${BOLD}======== $1 ========${NC}"; }

# ---------------------------------------------------------------------------
# Pre-checks
# ---------------------------------------------------------------------------
header "Pre-Deployment Checks"

if ! command -v aws &>/dev/null; then
  error "AWS CLI not found. Install it first."
  exit 1
fi
success "AWS CLI installed"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
  error "AWS credentials not configured"; exit 1;
}
success "AWS credentials valid — Account: $ACCOUNT_ID"

CURRENT_REGION=$(aws configure get region 2>/dev/null || echo "")
if [[ "$CURRENT_REGION" != "$REGION" ]]; then
  warn "Region is '$CURRENT_REGION', setting to $REGION"
  export AWS_DEFAULT_REGION="$REGION"
fi
success "Region: $REGION"

# ---------------------------------------------------------------------------
# Collect parameters (use defaults or existing config)
# ---------------------------------------------------------------------------
header "Configuration"

prompt_val() {
  local prompt="$1" default="$2" val
  read -rp "$(echo -e "${CYAN}$prompt [$default]: ${NC}")" val
  echo "${val:-$default}"
}

prompt_secret() {
  local prompt="$1" val
  read -rsp "$(echo -e "${CYAN}$prompt: ${NC}")" val; echo
  echo "$val"
}

BEDROCK_MODEL_ID=$(prompt_val "Bedrock Model ID" "global.anthropic.claude-sonnet-4-5-20250929-v1:0")

COGNITO_STACK=$(prompt_val "Cognito Stack Name" "cognito-stack-a2a")
ECHOINK_STACK=$(prompt_val "Echo Ink Agent Stack Name" "echo-ink-agent-a2a")
ECHOPREPARE_STACK=$(prompt_val "Echo Prepare Agent Stack Name" "echo-prepare-agent-a2a")
VIDEO_STACK=$(prompt_val "Video Agent Stack Name" "video-agent-a2a")
DOCUMENTS_STACK=$(prompt_val "Documents Agent Stack Name" "documents-agent-a2a")
HOST_STACK=$(prompt_val "Host Agent Stack Name" "host-agent-a2a")

UNIQUE_ID=$(uuidgen | cut -c1-8 | tr '[:upper:]' '[:lower:]')
S3_BUCKET=$(prompt_val "S3 Bucket for templates" "a2a-smithy-models-${ACCOUNT_ID}-${UNIQUE_ID}")
COGNITO_DOMAIN=$(prompt_val "Cognito Domain Name" "agentcore-m2m-${ACCOUNT_ID}-${UNIQUE_ID}")
ADMIN_EMAIL=$(prompt_val "Admin Email" "")
TAVILY_KEY=$(prompt_secret "Tavily API Key")
GITHUB_URL=$(prompt_val "GitHub Repo URL" "https://github.com/aaravmat1209/agent_orchestration_echo.git")
HOST_MODEL=$(prompt_val "Host Agent Model ID" "$BEDROCK_MODEL_ID")

# Save config for cleanup
cat > "$CONFIG_FILE" <<EOF
REGION=$REGION
ACCOUNT_ID=$ACCOUNT_ID
BEDROCK_MODEL_ID=$BEDROCK_MODEL_ID
COGNITO_STACK=$COGNITO_STACK
ECHOINK_STACK=$ECHOINK_STACK
ECHOPREPARE_STACK=$ECHOPREPARE_STACK
VIDEO_STACK=$VIDEO_STACK
DOCUMENTS_STACK=$DOCUMENTS_STACK
HOST_STACK=$HOST_STACK
S3_BUCKET=$S3_BUCKET
COGNITO_DOMAIN=$COGNITO_DOMAIN
ADMIN_EMAIL=$ADMIN_EMAIL
GITHUB_URL=$GITHUB_URL
HOST_MODEL=$HOST_MODEL
EOF
success "Config saved to $CONFIG_FILE"

# ---------------------------------------------------------------------------
# Helper: wait for stack
# ---------------------------------------------------------------------------
wait_for_stack() {
  local stack="$1" op="${2:-create}"
  local target="${op^^}_COMPLETE" fail="${op^^}_FAILED"
  info "Waiting for $stack ($op)..."
  while true; do
    STATUS=$(aws cloudformation describe-stacks --stack-name "$stack" \
      --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "GONE")
    case "$STATUS" in
      "$target"|"GONE"|"DELETE_COMPLETE") success "$stack — $STATUS"; return 0 ;;
      "$fail"|"ROLLBACK_COMPLETE"|"ROLLBACK_FAILED") error "$stack — $STATUS"; return 1 ;;
      *) info "  $stack: $STATUS …"; sleep 15 ;;
    esac
  done
}

deploy_stack() {
  local name="$1" template="$2"; shift 2
  local params=("$@")
  header "Deploying $name"

  # Upload template to S3
  local s3key="cloudformation-templates/$(basename "$template")"
  aws s3 cp "$template" "s3://${S3_BUCKET}/${s3key}" --region "$REGION" >/dev/null
  local s3url="https://${S3_BUCKET}.s3.${REGION}.amazonaws.com/${s3key}"

  if aws cloudformation describe-stacks --stack-name "$name" --region "$REGION" &>/dev/null; then
    warn "$name already exists, skipping"
    return 0
  fi

  aws cloudformation create-stack \
    --stack-name "$name" \
    --template-url "$s3url" \
    --parameters "${params[@]}" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" >/dev/null

  wait_for_stack "$name" create
}

# ---------------------------------------------------------------------------
# Step 0: S3 buckets
# ---------------------------------------------------------------------------
header "Creating S3 Buckets"

if ! aws s3api head-bucket --bucket "$S3_BUCKET" --region "$REGION" 2>/dev/null; then
  aws s3 mb "s3://${S3_BUCKET}" --region "$REGION"
  success "Created $S3_BUCKET"
else
  info "$S3_BUCKET already exists"
fi

ECHO_DOCS_BUCKET="echo-docs-${ACCOUNT_ID}"
if ! aws s3api head-bucket --bucket "$ECHO_DOCS_BUCKET" --region "$REGION" 2>/dev/null; then
  aws s3 mb "s3://${ECHO_DOCS_BUCKET}" --region "$REGION"
  aws s3api put-bucket-versioning --bucket "$ECHO_DOCS_BUCKET" \
    --versioning-configuration Status=Enabled --region "$REGION"
  success "Created $ECHO_DOCS_BUCKET with versioning"
else
  info "$ECHO_DOCS_BUCKET already exists"
fi

# ---------------------------------------------------------------------------
# Step 0.5: Tavily secret
# ---------------------------------------------------------------------------
header "Creating Tavily Secret"
if aws secretsmanager describe-secret --secret-id tavily-api-key --region "$REGION" &>/dev/null; then
  info "tavily-api-key secret already exists"
else
  aws secretsmanager create-secret \
    --name tavily-api-key \
    --description "Tavily API key for web search" \
    --secret-string "{\"TAVILY_API_KEY\":\"${TAVILY_KEY}\"}" \
    --region "$REGION" >/dev/null
  success "Tavily secret created"
fi

# ---------------------------------------------------------------------------
# Step 1: Cognito
# ---------------------------------------------------------------------------
deploy_stack "$COGNITO_STACK" "cloudformation/cognito.yaml" \
  "ParameterKey=DomainName,ParameterValue=${COGNITO_DOMAIN}" \
  "ParameterKey=AdminUserEmail,ParameterValue=${ADMIN_EMAIL}"

# ---------------------------------------------------------------------------
# Upload Smithy model
# ---------------------------------------------------------------------------
header "Uploading Smithy Model"
aws s3 cp cloudformation/smithy-models/monitoring-service.json \
  "s3://${S3_BUCKET}/smithy-models/monitoring-service.json" --region "$REGION" >/dev/null
success "Smithy model uploaded"

# ---------------------------------------------------------------------------
# Steps 2-6: Deploy agent stacks (parallel where possible)
# ---------------------------------------------------------------------------
header "Deploying Agent Stacks"
info "Deploying Echo Ink, Echo Prepare, Video, and Documents agents..."

deploy_agent() {
  local name="$1" template="$2"; shift 2
  deploy_stack "$name" "$template" "$@"
}

# Deploy the 4 independent agent stacks in background
deploy_agent "$ECHOINK_STACK" "cloudformation/echo_ink_agent.yaml" \
  "ParameterKey=BedrockModelId,ParameterValue=${BEDROCK_MODEL_ID}" \
  "ParameterKey=GitHubURL,ParameterValue=${GITHUB_URL}" \
  "ParameterKey=CognitoStackName,ParameterValue=${COGNITO_STACK}" &
PID_INK=$!

deploy_agent "$ECHOPREPARE_STACK" "cloudformation/echo_prepare_agent.yaml" \
  "ParameterKey=BedrockModelId,ParameterValue=${BEDROCK_MODEL_ID}" \
  "ParameterKey=GitHubURL,ParameterValue=${GITHUB_URL}" \
  "ParameterKey=CognitoStackName,ParameterValue=${COGNITO_STACK}" &
PID_PREP=$!

deploy_agent "$VIDEO_STACK" "cloudformation/video_agent.yaml" \
  "ParameterKey=BedrockModelId,ParameterValue=${BEDROCK_MODEL_ID}" \
  "ParameterKey=GitHubURL,ParameterValue=${GITHUB_URL}" \
  "ParameterKey=CognitoStackName,ParameterValue=${COGNITO_STACK}" &
PID_VID=$!

deploy_agent "$DOCUMENTS_STACK" "cloudformation/documents_agent.yaml" \
  "ParameterKey=BedrockModelId,ParameterValue=${BEDROCK_MODEL_ID}" \
  "ParameterKey=GitHubURL,ParameterValue=${GITHUB_URL}" \
  "ParameterKey=CognitoStackName,ParameterValue=${COGNITO_STACK}" &
PID_DOC=$!

# Wait for all agent stacks
FAIL=0
wait $PID_INK  || FAIL=1
wait $PID_PREP || FAIL=1
wait $PID_VID  || FAIL=1
wait $PID_DOC  || FAIL=1

if [[ $FAIL -ne 0 ]]; then
  error "One or more agent stacks failed. Check CloudFormation console."
  exit 1
fi
success "All agent stacks deployed"

# Host agent depends on the others (reads their SSM params)
deploy_stack "$HOST_STACK" "cloudformation/host_agent.yaml" \
  "ParameterKey=BedrockModelId,ParameterValue=${HOST_MODEL}" \
  "ParameterKey=GitHubURL,ParameterValue=${GITHUB_URL}" \
  "ParameterKey=CognitoStackName,ParameterValue=${COGNITO_STACK}"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
header "Deployment Complete!"
success "All stacks deployed successfully."
info "Next steps:"
info "  1. Test agents:  uv run test/connect_agent.py --agent host"
info "  2. Run frontend: cd frontend && npm install && ./setup-env.sh && npm run dev"
info "  3. Cleanup:      bash cleanup.sh"
