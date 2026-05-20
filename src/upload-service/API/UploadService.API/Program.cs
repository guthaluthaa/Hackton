using FluentValidation;
using MassTransit;
using MediatR;
using Microsoft.EntityFrameworkCore;
using Serilog;
using UploadService.Application.Commands;
using UploadService.Application.Validators;
using UploadService.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

// Serilog
builder.Host.UseSerilog((context, loggerConfig) =>
{
    loggerConfig
        .ReadFrom.Configuration(context.Configuration)
        .WriteTo.Console()
        .WriteTo.Seq(context.Configuration["Seq:Url"] ?? "http://localhost:5341");
});

// MediatR
builder.Services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssemblyContaining<UploadFileCommand>());

// FluentValidation
builder.Services.AddValidatorsFromAssemblyContaining<UploadFileCommandValidator>();

// MassTransit + RabbitMQ
builder.Services.AddMassTransit(x =>
{
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

// Infrastructure (EF Core, MinIO, Repositories)
builder.Services.AddInfrastructure(builder.Configuration);

// Swagger / OpenAPI
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new() { Title = "Upload Service", Version = "v1" });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<UploadService.Infrastructure.Persistence.UploadDbContext>();
    await db.Database.EnsureCreatedAsync();
}

// Minimal API endpoint
app.MapPost("/api/upload", async (IFormFile file, IMediator mediator, IValidator<UploadFileCommand> validator) =>
{
    if (file is null || file.Length == 0)
    {
        return Results.BadRequest(new { Error = "No file provided." });
    }

    var command = new UploadFileCommand(
        FileStream: file.OpenReadStream(),
        FileName: file.FileName,
        ContentType: file.ContentType,
        FileSize: file.Length
    );

    var validationResult = await validator.ValidateAsync(command);
    if (!validationResult.IsValid)
    {
        return Results.BadRequest(new { Errors = validationResult.Errors.Select(e => e.ErrorMessage) });
    }

    try
    {
        var result = await mediator.Send(command);
        return Results.Ok(new
        {
            result.JobId,
            result.FileName,
            result.FilePath,
            Message = "File uploaded successfully."
        });
    }
    catch (Exception ex)
    {
        Log.Error(ex, "Error uploading file {FileName}", file.FileName);
        return Results.StatusCode(500);
    }
})
.DisableAntiforgery();

app.Run();
