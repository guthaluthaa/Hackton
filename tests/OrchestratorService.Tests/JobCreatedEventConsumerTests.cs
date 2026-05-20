using FluentAssertions;
using Xunit;
using MassTransit;
using Microsoft.Extensions.Logging;
using NSubstitute;
using OrchestratorService.Application.Consumers;
using OrchestratorService.Domain.Entities;
using OrchestratorService.Domain.Interfaces;
using Shared.Enums;
using Shared.Events;

namespace OrchestratorService.Tests;

public class JobCreatedEventConsumerTests
{
    private readonly IJobRepository _jobRepository = Substitute.For<IJobRepository>();
    private readonly IPublishEndpoint _publishEndpoint = Substitute.For<IPublishEndpoint>();
    private readonly ILogger<JobCreatedEventConsumer> _logger = Substitute.For<ILogger<JobCreatedEventConsumer>>();
    private readonly JobCreatedEventConsumer _consumer;

    public JobCreatedEventConsumerTests()
    {
        _consumer = new JobCreatedEventConsumer(_jobRepository, _publishEndpoint, _logger);
    }

    [Fact]
    public async Task Consume_ShouldPersistJobAndPublishAnalysisRequest()
    {
        var jobId = Guid.NewGuid();
        var message = new JobCreatedEvent
        {
            JobId = jobId,
            FileName = "test.pdf",
            FilePath = "/uploads/test.pdf",
            ContentType = "application/pdf",
            FileSize = 1024,
            CreatedAt = DateTime.UtcNow
        };

        var context = Substitute.For<ConsumeContext<JobCreatedEvent>>();
        context.Message.Returns(message);
        context.CancellationToken.Returns(CancellationToken.None);

        await _consumer.Consume(context);

        await _jobRepository.Received(1).AddAsync(
            Arg.Is<Job>(j => j.Id == jobId && j.Status == JobStatus.Received),
            Arg.Any<CancellationToken>());

        await _publishEndpoint.Received(1).Publish(
            Arg.Is<AnalysisRequestedEvent>(e => e.JobId == jobId),
            Arg.Any<CancellationToken>());
    }

    [Fact]
    public async Task Consume_ShouldSetCorrectJobProperties()
    {
        var jobId = Guid.NewGuid();
        var createdAt = DateTime.UtcNow.AddMinutes(-5);
        var message = new JobCreatedEvent
        {
            JobId = jobId,
            FileName = "report.png",
            FilePath = "/uploads/report.png",
            ContentType = "image/png",
            FileSize = 5000,
            CreatedAt = createdAt
        };

        var context = Substitute.For<ConsumeContext<JobCreatedEvent>>();
        context.Message.Returns(message);
        context.CancellationToken.Returns(CancellationToken.None);

        await _consumer.Consume(context);

        await _jobRepository.Received(1).AddAsync(
            Arg.Is<Job>(j =>
                j.FileName == "report.png" &&
                j.FilePath == "/uploads/report.png" &&
                j.CreatedAt == createdAt),
            Arg.Any<CancellationToken>());
    }
}
