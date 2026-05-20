using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Minio;
using UploadService.Application.Interfaces;
using UploadService.Domain.Interfaces;
using UploadService.Infrastructure.Persistence;
using UploadService.Infrastructure.Repositories;
using UploadService.Infrastructure.Services;

namespace UploadService.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        // EF Core with PostgreSQL
        services.AddDbContext<UploadDbContext>(options =>
            options.UseNpgsql(configuration.GetConnectionString("DefaultConnection")));

        // Repositories
        services.AddScoped<IUploadJobRepository, UploadJobRepository>();

        // MinIO
        services.AddSingleton<IMinioClient>(sp =>
        {
            var endpoint = configuration["MinIO:Endpoint"] ?? "localhost:9000";
            var accessKey = configuration["MinIO:AccessKey"] ?? "minioadmin";
            var secretKey = configuration["MinIO:SecretKey"] ?? "minioadmin";

            return new MinioClient()
                .WithEndpoint(endpoint)
                .WithCredentials(accessKey, secretKey)
                .Build();
        });

        services.AddScoped<IStorageService, MinioStorageService>();

        return services;
    }
}
