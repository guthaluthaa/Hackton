namespace Shared.Events;

public record AnalysisCompletedEvent
{
    public Guid JobId { get; init; }
    public string Status { get; init; } = "ANALYZED";
    public List<string> Components { get; init; } = [];
    public List<string> Risks { get; init; } = [];
    public List<string> Recommendations { get; init; } = [];
    public DateTime CompletedAt { get; init; } = DateTime.UtcNow;
}
