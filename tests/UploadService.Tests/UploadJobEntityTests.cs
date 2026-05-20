using FluentAssertions;
using Xunit;
using Shared.Enums;
using UploadService.Domain.Entities;

namespace UploadService.Tests;

public class UploadJobEntityTests
{
    [Fact]
    public void Create_ShouldInitializeWithReceivedStatus()
    {
        var job = UploadJob.Create("test.pdf", "/uploads/test.pdf", "application/pdf", 2048);

        job.Id.Should().NotBeEmpty();
        job.FileName.Should().Be("test.pdf");
        job.FilePath.Should().Be("/uploads/test.pdf");
        job.ContentType.Should().Be("application/pdf");
        job.FileSize.Should().Be(2048);
        job.Status.Should().Be(JobStatus.Received);
        job.CreatedAt.Should().BeCloseTo(DateTime.UtcNow, TimeSpan.FromSeconds(2));
    }

    [Fact]
    public void Create_ShouldGenerateUniqueIds()
    {
        var job1 = UploadJob.Create("a.pdf", "/a.pdf", "application/pdf", 100);
        var job2 = UploadJob.Create("b.pdf", "/b.pdf", "application/pdf", 200);

        job1.Id.Should().NotBe(job2.Id);
    }
}
