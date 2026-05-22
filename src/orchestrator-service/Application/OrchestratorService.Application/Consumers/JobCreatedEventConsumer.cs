using System.Diagnostics;
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
        var sw = Stopwatch.StartNew();
        var message = context.Message;
        _logger.LogInformation("Received JobCreatedEvent for JobId: {JobId}, FileName: {FileName}, FileSize: {FileSize} bytes",
            message.JobId, message.FileName, message.FileSize);

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

        _logger.LogInformation("Job {JobId} persisted with status {Status}", message.JobId, JobStatus.Received);

        var analysisRequest = new AnalysisRequestedEvent
        {
            JobId = message.JobId,
            FilePath = message.FilePath,
            LlmProvider = message.LlmProvider,
            LlmApiKey = message.LlmApiKey,
            RequestedAt = DateTime.UtcNow
        };

        await _publishEndpoint.Publish(analysisRequest, context.CancellationToken);

        job.Status = JobStatus.Processing;
        job.UpdatedAt = DateTime.UtcNow;
        await _jobRepository.UpdateAsync(job, context.CancellationToken);

        sw.Stop();
        _logger.LogInformation("Published AnalysisRequestedEvent for JobId: {JobId}, status updated to {Status} | Elapsed: {ElapsedMs}ms",
            message.JobId, JobStatus.Processing, sw.ElapsedMilliseconds);
    }
}
