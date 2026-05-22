using FluentAssertions;
using Xunit;
using MassTransit;
using Microsoft.Extensions.Logging;
using NSubstitute;
using ReportService.Application.Consumers;
using ReportService.Domain.Entities;
using ReportService.Domain.Interfaces;
using Shared.Events;

namespace ReportService.Tests;

public class GenerateReportCommandConsumerTests
{
    private readonly IReportRepository _reportRepository = Substitute.For<IReportRepository>();
    private readonly IPublishEndpoint _publishEndpoint = Substitute.For<IPublishEndpoint>();
    private readonly ILogger<GenerateReportCommandConsumer> _logger = Substitute.For<ILogger<GenerateReportCommandConsumer>>();
    private readonly GenerateReportCommandConsumer _consumer;

    public GenerateReportCommandConsumerTests()
    {
        _consumer = new GenerateReportCommandConsumer(_reportRepository, _publishEndpoint, _logger);
    }

    [Fact]
    public async Task Consume_ShouldCreateReportAndPublishEvent()
    {
        var jobId = Guid.NewGuid();
        var command = new GenerateReportCommand
        {
            JobId = jobId,
            Components = ["ComponentA", "ComponentB"],
            Risks = ["Risk1"],
            Recommendations = ["Recommendation1"]
        };

        var context = Substitute.For<ConsumeContext<GenerateReportCommand>>();
        context.Message.Returns(command);
        context.CancellationToken.Returns(CancellationToken.None);

        await _consumer.Consume(context);

        await _reportRepository.Received(1).AddAsync(
            Arg.Is<Report>(r => r.JobId == jobId),
            Arg.Any<CancellationToken>());

        await context.Received(1).Publish(
            Arg.Is<ReportGeneratedEvent>(e => e.JobId == jobId),
            Arg.Any<CancellationToken>());
    }

    [Fact]
    public async Task Consume_ShouldSerializeComponentsAndRisks()
    {
        var command = new GenerateReportCommand
        {
            JobId = Guid.NewGuid(),
            Components = ["Auth", "DB"],
            Risks = ["SQL Injection"],
            Recommendations = ["Use parameterized queries"]
        };

        var context = Substitute.For<ConsumeContext<GenerateReportCommand>>();
        context.Message.Returns(command);
        context.CancellationToken.Returns(CancellationToken.None);

        await _consumer.Consume(context);

        await _reportRepository.Received(1).AddAsync(
            Arg.Is<Report>(r =>
                r.Components.Contains("Auth") &&
                r.Risks.Contains("SQL Injection") &&
                r.Recommendations.Contains("parameterized")),
            Arg.Any<CancellationToken>());
    }
}
