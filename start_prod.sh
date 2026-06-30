#!/bin/bash

# LLM Council - Production start script
# Builds the frontend and serves it (plus the API) from a single FastAPI
# process under DEPLOY_PREFIX, for deployment behind a reverse proxy
# sub-path (see docs/nginx-plan.md).

export PATH="$HOME/.local/bin:$PATH"

DEPLOY_PREFIX="${DEPLOY_PREFIX:-/content}"

echo "Building frontend..."
cd frontend
npm run build
cd ..

echo ""
echo "Starting LLM Council (production) under prefix ${DEPLOY_PREFIX} on http://localhost:8001${DEPLOY_PREFIX}/ ..."
DEPLOY_PREFIX="$DEPLOY_PREFIX" uv run python -m backend.main
