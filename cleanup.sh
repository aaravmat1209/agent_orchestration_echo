#!/bin/bash
# =============================================================================
# Cleanup script for Echo A2A Multi-Agent Educational Platform
# Designed to run on AWS CloudShell or any bash environment with AWS CLI
# =============================================================================
set -euo pipefail

CONFIG_FILE=".a2a.config"

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
# Load config
# ---------------------------------------------------------------------------
if [[ ! -f "$CONFIG_FILE" ]]; then
  error "Config file '$CONFIG_FILE' not found. Run deploy.sh first."
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG_FILE"
success "Config loaded from $CONFIG_FILE"

# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------
header "Resources to Delete"
echo "  Stacks: $HOST_STACK, $VIDEO_STACK, $DOCUMENTS_STACK, $ECHOPREPARE_STACK, $ECHOINK_STACK, $COGNITO_STACK"
echo "  Buckets: $S3_BUCKET, echo-docs-${ACCOUNT_ID}"
echo "  Region: $REGION"
echo ""
echo -e "${RED}${BOLD}This will permanently delete ALL resources. Cannot be undone.${NC}"
read -rp "Type DELETE to confirm: " CONFIRM
if [[ "$CONFIRM" != "DELETE" ]]; then
  warn "Cleanup cancelled."
  exit 0
fi

# ---------------------------------------------------------------------------
# Helper: delete stack and wait
# ---------------------------------------------------------------------------
delete_stack() {
  local stack="$1"
  if ! aws cloudformation describe-stacks --stack-name "$stack" --region "$REGION" &>/dev/null; then
    info "$stack does not exist, skipping"
    return 0
  fi
  info "Deleting $stack..."
  aws cloudformation delete-stack --stack-name "$stack" --region "$REGION"

  info "Waiting for $stack deletion..."
  while true; do
    STATUS=$(aws cloudformation describe-stacks --stack-name "$stack" \
      --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "GONE")
    case "$STATUS" in
      "GONE"|"DELETE_COMPLETE") success "$stack deleted"; return 0 ;;
      "DELETE_FAILED")          error "$stack deletion failed"; return 1 ;;
      *)                        info "  $stack: $STATUS …"; sleep 15 ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Step 1: Delete Host Agent first (depends on others)
# ---------------------------------------------------------------------------
header "Deleting Host Agent"
delete_stack "$HOST_STACK" || warn "Host stack deletion had issues"

# ---------------------------------------------------------------------------
# Step 2: Delete agent stacks in parallel
# ---------------------------------------------------------------------------
header "Deleting Agent Stacks (parallel)"
delete_stack "$VIDEO_STACK" &
PID1=$!
delete_stack "$DOCUMENTS_STACK" &
PID2=$!
delete_stack "$ECHOPREPARE_STACK" &
PID3=$!
delete_stack "$ECHOINK_STACK" &
PID4=$!

FAIL=0
wait $PID1 || FAIL=1
wait $PID2 || FAIL=1
wait $PID3 || FAIL=1
wait $PID4 || FAIL=1

if [[ $FAIL -ne 0 ]]; then
  warn "Some agent stacks had deletion issues — continuing"
fi

# ---------------------------------------------------------------------------
# Step 3: Delete Cognito
# ---------------------------------------------------------------------------
header "Deleting Cognito Stack"
delete_stack "$COGNITO_STACK" || warn "Cognito deletion had issues"

# ---------------------------------------------------------------------------
# Step 4: Empty and delete S3 buckets
# ---------------------------------------------------------------------------
header "Cleaning Up S3 Buckets"

cleanup_bucket() {
  local bucket="$1"
  if aws s3api head-bucket --bucket "$bucket" --region "$REGION" 2>/dev/null; then
    info "Emptying $bucket..."
    aws s3 rm "s3://${bucket}" --recursive --region "$REGION" 2>/dev/null || true
    aws s3 rb "s3://${bucket}" --region "$REGION" 2>/dev/null || true
    success "$bucket deleted"
  else
    info "$bucket does not exist"
  fi
}

cleanup_bucket "$S3_BUCKET"
cleanup_bucket "echo-docs-${ACCOUNT_ID}"

# ---------------------------------------------------------------------------
# Step 5: Remove config
# ---------------------------------------------------------------------------
rm -f "$CONFIG_FILE"
success "Removed $CONFIG_FILE"

header "Cleanup Complete!"
success "All resources deleted. Run deploy.sh to redeploy."
