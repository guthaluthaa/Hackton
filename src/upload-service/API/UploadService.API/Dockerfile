FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8080

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy project files
COPY src/shared/Shared/Shared.csproj src/shared/Shared/
COPY src/upload-service/Domain/UploadService.Domain/UploadService.Domain.csproj src/upload-service/Domain/UploadService.Domain/
COPY src/upload-service/Application/UploadService.Application/UploadService.Application.csproj src/upload-service/Application/UploadService.Application/
COPY src/upload-service/Infrastructure/UploadService.Infrastructure/UploadService.Infrastructure.csproj src/upload-service/Infrastructure/UploadService.Infrastructure/
COPY src/upload-service/API/UploadService.API/UploadService.API.csproj src/upload-service/API/UploadService.API/

# Restore
RUN dotnet restore src/upload-service/API/UploadService.API/UploadService.API.csproj

# Copy everything
COPY src/shared/ src/shared/
COPY src/upload-service/ src/upload-service/

# Build
WORKDIR /src/src/upload-service/API/UploadService.API
RUN dotnet build -c Release -o /app/build

FROM build AS publish
RUN dotnet publish -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "UploadService.API.dll"]
