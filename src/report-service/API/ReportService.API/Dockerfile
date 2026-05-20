FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8080

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /build

# Copy project files
COPY src/shared/Shared/Shared.csproj src/shared/Shared/
COPY src/report-service/Domain/ReportService.Domain/ReportService.Domain.csproj src/report-service/Domain/ReportService.Domain/
COPY src/report-service/Application/ReportService.Application/ReportService.Application.csproj src/report-service/Application/ReportService.Application/
COPY src/report-service/Infrastructure/ReportService.Infrastructure/ReportService.Infrastructure.csproj src/report-service/Infrastructure/ReportService.Infrastructure/
COPY src/report-service/API/ReportService.API/ReportService.API.csproj src/report-service/API/ReportService.API/

# Restore
RUN dotnet restore src/report-service/API/ReportService.API/ReportService.API.csproj

# Copy source code
COPY src/shared/ src/shared/
COPY src/report-service/ src/report-service/

# Build
WORKDIR /build/src/report-service/API/ReportService.API
RUN dotnet build -c Release -o /app/build

FROM build AS publish
RUN dotnet publish -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "ReportService.API.dll"]
