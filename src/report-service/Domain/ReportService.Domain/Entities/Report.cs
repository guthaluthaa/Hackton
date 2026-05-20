namespace ReportService.Domain.Entities;

public class Report
{
    public Guid Id { get; set; }
    public Guid JobId { get; set; }
    public string Components { get; set; } = string.Empty;
    public string Risks { get; set; } = string.Empty;
    public string Recommendations { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
