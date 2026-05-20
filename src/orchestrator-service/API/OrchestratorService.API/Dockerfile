FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8080

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy project files
COPY src/shared/Shared/Shared.csproj src/shared/Shared/
COPY src/orchestrator-service/Domain/OrchestratorService.Domain/OrchestratorService.Domain.csproj src/orchestrator-service/Domain/OrchestratorService.Domain/
COPY src/orchestrator-service/Application/OrchestratorService.Application/OrchestratorService.Application.csproj src/orchestrator-service/Application/OrchestratorService.Application/
COPY src/orchestrator-service/Infrastructure/OrchestratorService.Infrastructure/OrchestratorService.Infrastructure.csproj src/orchestrator-service/Infrastructure/OrchestratorService.Infrastructure/
COPY src/orchestrator-service/API/OrchestratorService.API/OrchestratorService.API.csproj src/orchestrator-service/API/OrchestratorService.API/

# Restore
RUN dotnet restore src/orchestrator-service/API/OrchestratorService.API/OrchestratorService.API.csproj

# Copy source code
COPY src/shared/ src/shared/
COPY src/orchestrator-service/ src/orchestrator-service/

# Build
RUN dotnet build src/orchestrator-service/API/OrchestratorService.API/OrchestratorService.API.csproj -c Release -o /app/build

FROM build AS publish
RUN dotnet publish src/orchestrator-service/API/OrchestratorService.API/OrchestratorService.API.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "OrchestratorService.API.dll"]
