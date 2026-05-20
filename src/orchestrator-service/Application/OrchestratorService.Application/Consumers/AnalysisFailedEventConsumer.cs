using MassTransit;
using Microsoft.Extensions.Logging;
using OrchestratorService.Domain.Interfaces;
using Shared.Enums;
using Shared.Events;

namespace OrchestratorService.Application.Consumers;

public class AnalysisFailedEventConsumer : IConsumer<AnalysisFailedEvent>
{
    private readonly IJobRepository _jobRepository;
    private readonly ILogger<AnalysisFailedEventConsumer> _logger;

    public AnalysisFailedEventConsumer(
        IJobRepository jobRepository,
        ILogger<AnalysisFailedEventConsumer> logger)
    {
        _jobRepository = jobRepository;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<AnalysisFailedEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Received AnalysisFailedEvent for JobId: {JobId}, Reason: {Reason}", message.JobId, message.Reason);

        var job = await _jobRepository.GetByIdAsync(message.JobId, context.CancellationToken);
        if (job is null)
        {
            _logger.LogWarning("Job not found for JobId: {JobId}", message.JobId);
            return;
        }

        job.Status = JobStatus.Failed;
        job.ErrorMessage = message.Reason;
        job.UpdatedAt = DateTime.UtcNow;

        await _jobRepository.UpdateAsync(job, context.CancellationToken);

        _logger.LogInformation("Job {JobId} marked as Failed", message.JobId);
    }
}
