# ==================================================
# Hackton - Stop all services (Windows PowerShell)
# ==================================================

$RootDir = Split-Path -Parent $PSScriptRoot
$DockerDir = Join-Path $RootDir "docker"

Write-Host "Stopping all Hackton services..." -ForegroundColor Yellow
docker compose -f "$DockerDir/docker-compose.yml" down

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Green
Write-Host "To also remove volumes (databases, files): docker compose -f docker/docker-compose.yml down -v"
