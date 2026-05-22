namespace Shared.Events;

public record JobCreatedEvent
{
    public Guid JobId { get; init; }
    public string FileName { get; init; } = string.Empty;
    public string FilePath { get; init; } = string.Empty;
    public string ContentType { get; init; } = string.Empty;
    public long FileSize { get; init; }
    public string LlmProvider { get; init; } = string.Empty;
    public string LlmApiKey { get; init; } = string.Empty;
    public DateTime CreatedAt { get; init; } = DateTime.UtcNow;
}
