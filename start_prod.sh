#!/bin/bash

# LLM Council - Production start script
# Builds the frontend and serves it (plus the API) from a single FastAPI
# process under DEPLOY_PREFIX, for deployment behind a reverse proxy
# sub-path (see docs/nginx-plan.md).

export PATH="$HOME/.local/bin:$PATH"

# node/npm are installed via nvm, which is NOT on PATH under systemd's minimal
# environment. Source nvm (falling back to the newest installed node bin) so the
# frontend build below can run when this script is launched as a service.
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
  # shellcheck disable=SC1091
  . "$HOME/.nvm/nvm.sh"
fi
if ! command -v npm >/dev/null 2>&1; then
  _node_bin=$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)
  [ -n "$_node_bin" ] && export PATH="$_node_bin:$PATH"
fi

# Fail fast if the build can't run, so we never silently serve a stale dist.
set -e

DEPLOY_PREFIX="${DEPLOY_PREFIX:-/content}"

echo "Building frontend with prefix ${DEPLOY_PREFIX} ..."
cd frontend
DEPLOY_PREFIX="$DEPLOY_PREFIX" npm run build
cd ..

echo ""
echo "Starting LLM Council (production) under prefix ${DEPLOY_PREFIX} on http://localhost:8001${DEPLOY_PREFIX}/ ..."
DEPLOY_PREFIX="$DEPLOY_PREFIX" uv run python -m backend.main
