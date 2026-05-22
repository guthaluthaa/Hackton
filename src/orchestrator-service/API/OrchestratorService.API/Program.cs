using MassTransit;
using MediatR;
using Microsoft.EntityFrameworkCore;
using OrchestratorService.Application.Consumers;
using OrchestratorService.Application.Queries;
using OrchestratorService.Infrastructure;
using OrchestratorService.Infrastructure.Persistence;
using Serilog;

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .CreateBootstrapLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);

    builder.Host.UseSerilog((context, services, configuration) => configuration
        .ReadFrom.Configuration(context.Configuration)
        .ReadFrom.Services(services)
        .Enrich.FromLogContext()
        .Enrich.WithProperty("ServiceName", "OrchestratorService")
        .WriteTo.Console()
        .WriteTo.Seq(context.Configuration["Seq:Url"] ?? "http://localhost:5341"));

    // Add Infrastructure (EF Core + Repository)
    builder.Services.AddInfrastructure(builder.Configuration);

    // Add MediatR
    builder.Services.AddMediatR(cfg =>
        cfg.RegisterServicesFromAssemblyContaining<GetJobStatusQuery>());

    // Add MassTransit with RabbitMQ
    builder.Services.AddMassTransit(x =>
    {
        x.AddConsumer<JobCreatedEventConsumer>();
        x.AddConsumer<AnalysisCompletedEventConsumer>();
        x.AddConsumer<AnalysisFailedEventConsumer>();

        x.UsingRabbitMq((context, cfg) =>
        {
            cfg.Host(builder.Configuration["RabbitMq:Host"] ?? "localhost", "/", h =>
            {
                h.Username(builder.Configuration["RabbitMq:Username"] ?? "guest");
                h.Password(builder.Configuration["RabbitMq:Password"] ?? "guest");
            });

            cfg.ConfigureEndpoints(context);
        });
    });

    // Swagger / OpenAPI
    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddSwaggerGen(c =>
    {
        c.SwaggerDoc("v1", new() { Title = "Orchestrator Service", Version = "v1" });
    });

    var app = builder.Build();

    if (app.Environment.IsDevelopment())
    {
        app.UseSwagger();
        app.UseSwaggerUI();
    }

    using (var scope = app.Services.CreateScope())
    {
        var dbContext = scope.ServiceProvider.GetRequiredService<OrchestratorDbContext>();
        await dbContext.Database.EnsureCreatedAsync();
    }

    app.UseSerilogRequestLogging();

    // Minimal API endpoints
    app.MapGet("/api/status/{jobId:guid}", async (Guid jobId, IMediator mediator, ILogger<Program> logger) =>
    {
        logger.LogInformation("GET /api/status/{JobId} requested", jobId);

        var job = await mediator.Send(new GetJobStatusQuery(jobId));

        if (job is null)
        {
            logger.LogWarning("Job {JobId} not found", jobId);
            return Results.NotFound(new { message = $"Job {jobId} not found" });
        }

        logger.LogInformation("Job {JobId} status: {Status}", jobId, job.Status);

        return Results.Ok(new
        {
            job.Id,
            job.FileName,
            job.FilePath,
            Status = job.Status.ToString(),
            job.CreatedAt,
            job.UpdatedAt,
            job.ErrorMessage
        });
    });

    app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}
