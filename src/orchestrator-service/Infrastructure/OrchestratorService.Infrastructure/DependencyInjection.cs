using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using OrchestratorService.Domain.Interfaces;
using OrchestratorService.Infrastructure.Persistence;
using OrchestratorService.Infrastructure.Repositories;

namespace OrchestratorService.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddDbContext<OrchestratorDbContext>(options =>
            options.UseNpgsql(configuration.GetConnectionString("DefaultConnection")));

        services.AddScoped<IJobRepository, JobRepository>();

        return services;
    }
}
