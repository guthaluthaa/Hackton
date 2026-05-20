namespace Shared.Events;

public record AnalysisRequestedEvent
{
    public Guid JobId { get; init; }
    public string FilePath { get; init; } = string.Empty;
    public DateTime RequestedAt { get; init; } = DateTime.UtcNow;
}
