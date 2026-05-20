# ==================================================
# Hackton - Quick Start Script (Windows PowerShell)
# Starts all infrastructure and microservices
# ==================================================

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
$DockerDir = Join-Path $RootDir "docker"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Hackton - Quick Start" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Create .env if it doesn't exist
$EnvFile = Join-Path $DockerDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[*] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $RootDir ".env.example") $EnvFile
    Write-Host "    Done. Edit docker/.env to customize credentials."
    Write-Host ""
}

# Check Docker
try {
    docker info 2>$null | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running. Start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Starting infrastructure (Postgres, RabbitMQ, MinIO, Seq)..." -ForegroundColor Green
docker compose -f "$DockerDir/docker-compose.yml" up -d postgres rabbitmq minio seq

Write-Host ""
Write-Host "[2/3] Waiting for services to be healthy..." -ForegroundColor Green
Write-Host "      This may take 15-30 seconds on first run..."

$services = @("postgres", "rabbitmq", "minio")
foreach ($service in $services) {
    Write-Host "      Waiting for $service" -NoNewline
    do {
        Start-Sleep -Seconds 2
        Write-Host "." -NoNewline
        $status = docker inspect --format='{{.State.Health.Status}}' "hackton-$service" 2>$null
    } while ($status -ne "healthy")
    Write-Host " OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Starting microservices (Gateway, Upload, Orchestrator, Report)..." -ForegroundColor Green
docker compose -f "$DockerDir/docker-compose.yml" up -d --build

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  All services are up!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Endpoints:" -ForegroundColor White
Write-Host "    Gateway API:       http://localhost:5000"
Write-Host "    Upload Service:    http://localhost:5001"
Write-Host "    Orchestrator:      http://localhost:5002"
Write-Host "    Report Service:    http://localhost:5003"
Write-Host ""
Write-Host "  Management UIs:" -ForegroundColor White
Write-Host "    RabbitMQ:          http://localhost:15672  (hackton/hackton123)"
Write-Host "    MinIO Console:     http://localhost:9001   (hackton/hackton123)"
Write-Host "    Seq (Logs):        http://localhost:8081   (admin/hackton123)"
Write-Host ""
Write-Host "  Commands:" -ForegroundColor White
Write-Host "    Stop all:          docker compose -f docker/docker-compose.yml down"
Write-Host "    View logs:         docker compose -f docker/docker-compose.yml logs -f"
Write-Host "    Rebuild:           docker compose -f docker/docker-compose.yml up -d --build"
Write-Host "==========================================" -ForegroundColor Cyan
