#!/usr/bin/env bash
# One-command frontend deploy: build → sync to S3 → invalidate CloudFront cache.
# Run from the repo root: bash scripts/deploy_frontend.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env.agent"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env.agent not found. Run 'python api/setup_api.py' first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${S3_BUCKET:?S3_BUCKET not set in .env.agent}"
: "${CLOUDFRONT_DISTRIBUTION_ID:?CLOUDFRONT_DISTRIBUTION_ID not set in .env.agent — run 'python api/setup_api.py' to create CloudFront}"
: "${CLOUDFRONT_URL:?CLOUDFRONT_URL not set in .env.agent}"

echo "Building frontend..."
cd "$REPO_ROOT/frontend"
npm run build

echo "Syncing to S3 (s3://$S3_BUCKET/)..."
aws s3 sync dist/ "s3://$S3_BUCKET/" --delete

echo "Invalidating CloudFront cache ($CLOUDFRONT_DISTRIBUTION_ID)..."
aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*" \
  --output text --query 'Invalidation.Id'

echo ""
echo "Deployed: https://$CLOUDFRONT_URL"
