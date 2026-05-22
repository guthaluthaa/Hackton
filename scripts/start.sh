#!/bin/bash
# ==================================================
# Hackton - Quick Start Script
# Starts all infrastructure and microservices
# ==================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$ROOT_DIR/docker"

echo "=========================================="
echo "  Hackton - Quick Start"
echo "=========================================="
echo ""

# Create .env if it doesn't exist
if [ ! -f "$DOCKER_DIR/.env" ]; then
    echo "[*] Creating .env from .env.example..."
    cp "$ROOT_DIR/.env.example" "$DOCKER_DIR/.env"
    echo "    Done. Edit docker/.env to customize credentials."
    echo ""
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH."
    echo "        Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo "[ERROR] Docker daemon is not running. Start Docker Desktop."
    exit 1
fi

echo "[1/3] Starting infrastructure (Postgres, RabbitMQ, MinIO, Seq)..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d postgres rabbitmq minio seq

echo ""
echo "[2/3] Waiting for services to be healthy..."
echo "      This may take 15-30 seconds on first run..."

# Wait for health checks
for service in postgres rabbitmq minio; do
    printf "      Waiting for $service"
    until docker inspect --format='{{.State.Health.Status}}' "hackton-$service" 2>/dev/null | grep -q "healthy"; do
        printf "."
        sleep 2
    done
    echo " OK"
done

echo ""
echo "[3/3] Starting microservices (Gateway, Upload, Orchestrator, Report)..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d --build

echo ""
echo "=========================================="
echo "  All services are up!"
echo "=========================================="
echo ""
echo "  Endpoints:"
echo "    Gateway API:       http://localhost:5010"
echo "    Upload Service:    http://localhost:5001"
echo "    Orchestrator:      http://localhost:5002"
echo "    Report Service:    http://localhost:5003"
echo ""
echo "  Management UIs:"
echo "    RabbitMQ:          http://localhost:15672  (hackton/hackton123)"
echo "    MinIO Console:     http://localhost:9001   (hackton/hackton123)"
echo "    Seq (Logs):        http://localhost:8081   (admin/hackton123)"
echo ""
echo "  Commands:"
echo "    Stop all:          docker compose -f docker/docker-compose.yml down"
echo "    View logs:         docker compose -f docker/docker-compose.yml logs -f"
echo "    Rebuild:           docker compose -f docker/docker-compose.yml up -d --build"
echo "=========================================="
