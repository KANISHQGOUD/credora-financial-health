#!/bin/sh
# Runs every automated check inside the dev containers.
# Usage (from the project folder, with `docker compose up -d` running):
#   sh scripts/check.sh
set -e
cd "$(dirname "$0")/.."

echo "==> Backend tests (pytest)"
docker compose exec -T backend pytest

echo "==> Frontend type-check, tests and production build"
docker compose exec -T frontend npm run check

echo "==> All checks passed"
