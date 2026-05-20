namespace Shared.Events;

public record AnalysisFailedEvent
{
    public Guid JobId { get; init; }
    public string Reason { get; init; } = string.Empty;
    public DateTime FailedAt { get; init; } = DateTime.UtcNow;
}
