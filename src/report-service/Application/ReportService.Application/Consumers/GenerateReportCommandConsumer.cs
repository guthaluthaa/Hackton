using System.Text.Json;
using MassTransit;
using ReportService.Domain.Entities;
using ReportService.Domain.Interfaces;
using Shared.Events;

namespace ReportService.Application.Consumers;

public class GenerateReportCommandConsumer : IConsumer<GenerateReportCommand>
{
    private readonly IReportRepository _reportRepository;
    private readonly IPublishEndpoint _publishEndpoint;

    public GenerateReportCommandConsumer(IReportRepository reportRepository, IPublishEndpoint publishEndpoint)
    {
        _reportRepository = reportRepository;
        _publishEndpoint = publishEndpoint;
    }

    public async Task Consume(ConsumeContext<GenerateReportCommand> context)
    {
        var command = context.Message;

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

        await context.Publish(new ReportGeneratedEvent
        {
            JobId = command.JobId,
            ReportId = report.Id,
            GeneratedAt = report.CreatedAt
        });
    }
}
