using System.Diagnostics;
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
        var sw = Stopwatch.StartNew();
        var message = context.Message;
        _logger.LogInformation("Received AnalysisCompletedEvent for JobId: {JobId} (Components={ComponentCount}, Risks={RiskCount}, Recommendations={RecommendationCount})",
            message.JobId, message.Components?.Count ?? 0, message.Risks?.Count ?? 0, message.Recommendations?.Count ?? 0);

        var job = await _jobRepository.GetByIdAsync(message.JobId, context.CancellationToken);
        if (job is null)
        {
            _logger.LogWarning("Job not found for JobId: {JobId}", message.JobId);
            return;
        }

        var previousStatus = job.Status;
        job.Status = JobStatus.Analyzed;
        job.UpdatedAt = DateTime.UtcNow;

        await _jobRepository.UpdateAsync(job, context.CancellationToken);

        _logger.LogInformation("Job {JobId} status transition: {PreviousStatus} -> {NewStatus}",
            message.JobId, previousStatus, job.Status);

        var generateReportCommand = new GenerateReportCommand
        {
            JobId = message.JobId,
            Components = message.Components,
            Risks = message.Risks,
            Recommendations = message.Recommendations,
            RequestedAt = DateTime.UtcNow
        };

        await _publishEndpoint.Publish(generateReportCommand, context.CancellationToken);

        sw.Stop();
        _logger.LogInformation("Published GenerateReportCommand for JobId: {JobId} | Elapsed: {ElapsedMs}ms",
            message.JobId, sw.ElapsedMilliseconds);
    }
}
