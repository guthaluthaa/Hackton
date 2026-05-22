using System.Diagnostics;
using System.Text.Json;
using MassTransit;
using Microsoft.Extensions.Logging;
using ReportService.Domain.Entities;
using ReportService.Domain.Interfaces;
using Shared.Events;

namespace ReportService.Application.Consumers;

public class GenerateReportCommandConsumer : IConsumer<GenerateReportCommand>
{
    private readonly IReportRepository _reportRepository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<GenerateReportCommandConsumer> _logger;

    public GenerateReportCommandConsumer(
        IReportRepository reportRepository,
        IPublishEndpoint publishEndpoint,
        ILogger<GenerateReportCommandConsumer> logger)
    {
        _reportRepository = reportRepository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<GenerateReportCommand> context)
    {
        var sw = Stopwatch.StartNew();
        var command = context.Message;

        _logger.LogInformation("Received GenerateReportCommand for JobId: {JobId}", command.JobId);

        var report = new Report
        {
            Id = Guid.NewGuid(),
            JobId = command.JobId,
            Components = JsonSerializer.Serialize(command.Components),
            Risks = JsonSerializer.Serialize(command.Risks),
            Recommendations = JsonSerializer.Serialize(command.Recommendations),
            CreatedAt = DateTime.UtcNow
        };

        await _reportRepository.AddAsync(report, context.CancellationToken);

        _logger.LogInformation("Report {ReportId} created for JobId: {JobId} (Components={ComponentCount}, Risks={RiskCount}, Recommendations={RecommendationCount})",
            report.Id, command.JobId, command.Components?.Count ?? 0, command.Risks?.Count ?? 0, command.Recommendations?.Count ?? 0);

        await context.Publish(new ReportGeneratedEvent
        {
            JobId = command.JobId,
            ReportId = report.Id,
            GeneratedAt = report.CreatedAt
        });

        sw.Stop();
        _logger.LogInformation("Published ReportGeneratedEvent for JobId: {JobId} | Elapsed: {ElapsedMs}ms",
            command.JobId, sw.ElapsedMilliseconds);
    }
}
