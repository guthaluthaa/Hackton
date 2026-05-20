namespace Shared.Events;

public record ReportGeneratedEvent
{
    public Guid JobId { get; init; }
    public Guid ReportId { get; init; }
    public DateTime GeneratedAt { get; init; } = DateTime.UtcNow;
}
