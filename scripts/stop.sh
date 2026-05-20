#!/bin/bash
# ==================================================
# Hackton - Stop all services
# ==================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$ROOT_DIR/docker"

echo "Stopping all Hackton services..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" down

echo ""
echo "All services stopped."
echo "To also remove volumes (databases, files): docker compose -f docker/docker-compose.yml down -v"
