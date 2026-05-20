namespace Shared.Events;

public record GenerateReportCommand
{
    public Guid JobId { get; init; }
    public List<string> Components { get; init; } = [];
    public List<string> Risks { get; init; } = [];
    public List<string> Recommendations { get; init; } = [];
    public DateTime RequestedAt { get; init; } = DateTime.UtcNow;
}
