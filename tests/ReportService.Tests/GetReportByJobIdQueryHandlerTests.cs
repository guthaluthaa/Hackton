using FluentAssertions;
using Xunit;
using NSubstitute;
using ReportService.Application.Queries;
using ReportService.Domain.Entities;
using ReportService.Domain.Interfaces;

namespace ReportService.Tests;

public class GetReportByJobIdQueryHandlerTests
{
    private readonly IReportRepository _reportRepository = Substitute.For<IReportRepository>();
    private readonly GetReportByJobIdQueryHandler _handler;

    public GetReportByJobIdQueryHandlerTests()
    {
        _handler = new GetReportByJobIdQueryHandler(_reportRepository);
    }

    [Fact]
    public async Task Handle_WhenReportExists_ShouldReturnReport()
    {
        var jobId = Guid.NewGuid();
        var expectedReport = new Report
        {
            Id = Guid.NewGuid(),
            JobId = jobId,
            Components = "[\"Auth\"]",
            Risks = "[\"XSS\"]",
            Recommendations = "[\"Sanitize input\"]"
        };

        _reportRepository.GetByJobIdAsync(jobId, Arg.Any<CancellationToken>())
            .Returns(expectedReport);

        var query = new GetReportByJobIdQuery(jobId);
        var result = await _handler.Handle(query, CancellationToken.None);

        result.Should().NotBeNull();
        result!.JobId.Should().Be(jobId);
        result.Components.Should().Contain("Auth");
    }

    [Fact]
    public async Task Handle_WhenReportDoesNotExist_ShouldReturnNull()
    {
        var jobId = Guid.NewGuid();
        _reportRepository.GetByJobIdAsync(jobId, Arg.Any<CancellationToken>())
            .Returns((Report?)null);

        var query = new GetReportByJobIdQuery(jobId);
        var result = await _handler.Handle(query, CancellationToken.None);

        result.Should().BeNull();
    }
}
