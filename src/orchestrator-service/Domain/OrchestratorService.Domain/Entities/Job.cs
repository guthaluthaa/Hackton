using Shared.Enums;

namespace OrchestratorService.Domain.Entities;

public class Job
{
    public Guid Id { get; set; }
    public string FileName { get; set; } = string.Empty;
    public string FilePath { get; set; } = string.Empty;
    public JobStatus Status { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public string? ErrorMessage { get; set; }
}
