using MassTransit;
using MediatR;
using Microsoft.EntityFrameworkCore;
using ReportService.Application.Consumers;
using ReportService.Application.Queries;
using ReportService.Infrastructure;
using ReportService.Infrastructure.Persistence;
using Serilog;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);

// Serilog
builder.Host.UseSerilog((context, loggerConfig) =>
{
    loggerConfig
        .ReadFrom.Configuration(context.Configuration)
        .WriteTo.Console()
        .WriteTo.Seq(context.Configuration["Seq:Url"] ?? "http://seq:5341");
});

// Infrastructure (EF Core + Repository)
builder.Services.AddInfrastructure(builder.Configuration);

// MediatR
builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssemblyContaining<GetReportByJobIdQuery>());

// MassTransit + RabbitMQ
builder.Services.AddMassTransit(x =>
{
    x.AddConsumer<GenerateReportCommandConsumer>();

    x.UsingRabbitMq((context, cfg) =>
    {
        cfg.Host(builder.Configuration["RabbitMq:Host"] ?? "rabbitmq", "/", h =>
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
    c.SwaggerDoc("v1", new() { Title = "Report Service", Version = "v1" });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ReportDbContext>();
    await db.Database.EnsureCreatedAsync();
}

// Minimal API endpoints
app.MapGet("/api/report/{jobId:guid}", async (Guid jobId, IMediator mediator) =>
{
    var report = await mediator.Send(new GetReportByJobIdQuery(jobId));

    if (report is null)
        return Results.NotFound(new { message = $"Report for job {jobId} not found" });

    return Results.Ok(new
    {
        report.Id,
        report.JobId,
        Components      = JsonSerializer.Deserialize<List<string>>(report.Components),
        Risks           = JsonSerializer.Deserialize<List<string>>(report.Risks),
        Recommendations = JsonSerializer.Deserialize<List<string>>(report.Recommendations),
        report.CreatedAt
    });
});

app.MapGet("/health", () => Results.Ok("Healthy"));

app.Run();
