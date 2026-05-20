using MassTransit;
using Microsoft.Extensions.Logging;
using OrchestratorService.Domain.Entities;
using OrchestratorService.Domain.Interfaces;
using Shared.Enums;
using Shared.Events;

namespace OrchestratorService.Application.Consumers;

public class JobCreatedEventConsumer : IConsumer<JobCreatedEvent>
{
    private readonly IJobRepository _jobRepository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<JobCreatedEventConsumer> _logger;

    public JobCreatedEventConsumer(
        IJobRepository jobRepository,
        IPublishEndpoint publishEndpoint,
        ILogger<JobCreatedEventConsumer> logger)
    {
        _jobRepository = jobRepository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<JobCreatedEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Received JobCreatedEvent for JobId: {JobId}, FileName: {FileName}", message.JobId, message.FileName);

        var job = new Job
        {
            Id = message.JobId,
            FileName = message.FileName,
            FilePath = message.FilePath,
            Status = JobStatus.Received,
            CreatedAt = message.CreatedAt,
            UpdatedAt = DateTime.UtcNow
        };

        await _jobRepository.AddAsync(job, context.CancellationToken);

        var analysisRequest = new AnalysisRequestedEvent
        {
            JobId = message.JobId,
            FilePath = message.FilePath,
            RequestedAt = DateTime.UtcNow
        };

        await _publishEndpoint.Publish(analysisRequest, context.CancellationToken);

        _logger.LogInformation("Published AnalysisRequestedEvent for JobId: {JobId}", message.JobId);
    }
}
