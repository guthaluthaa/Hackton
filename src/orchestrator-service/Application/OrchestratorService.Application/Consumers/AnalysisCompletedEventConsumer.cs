using MassTransit;
using Microsoft.Extensions.Logging;
using OrchestratorService.Domain.Interfaces;
using Shared.Enums;
using Shared.Events;

namespace OrchestratorService.Application.Consumers;

public class AnalysisCompletedEventConsumer : IConsumer<AnalysisCompletedEvent>
{
    private readonly IJobRepository _jobRepository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<AnalysisCompletedEventConsumer> _logger;

    public AnalysisCompletedEventConsumer(
        IJobRepository jobRepository,
        IPublishEndpoint publishEndpoint,
        ILogger<AnalysisCompletedEventConsumer> logger)
    {
        _jobRepository = jobRepository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<AnalysisCompletedEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Received AnalysisCompletedEvent for JobId: {JobId}", message.JobId);

        var job = await _jobRepository.GetByIdAsync(message.JobId, context.CancellationToken);
        if (job is null)
        {
            _logger.LogWarning("Job not found for JobId: {JobId}", message.JobId);
            return;
        }

        job.Status = JobStatus.Analyzed;
        job.UpdatedAt = DateTime.UtcNow;

        await _jobRepository.UpdateAsync(job, context.CancellationToken);

        var generateReportCommand = new GenerateReportCommand
        {
            JobId = message.JobId,
            Components = message.Components,
            Risks = message.Risks,
            Recommendations = message.Recommendations,
            RequestedAt = DateTime.UtcNow
        };

        await _publishEndpoint.Publish(generateReportCommand, context.CancellationToken);

        _logger.LogInformation("Published GenerateReportCommand for JobId: {JobId}", message.JobId);
    }
}
