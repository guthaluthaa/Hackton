using Shared.Enums;

namespace UploadService.Domain.Entities;

public class UploadJob
{
    public Guid Id { get; set; }
    public string FileName { get; set; } = string.Empty;
    public string FilePath { get; set; } = string.Empty;
    public string ContentType { get; set; } = string.Empty;
    public long FileSize { get; set; }
    public JobStatus Status { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public static UploadJob Create(string fileName, string filePath, string contentType, long fileSize)
    {
        var now = DateTime.UtcNow;
        return new UploadJob
        {
            Id = Guid.NewGuid(),
            FileName = fileName,
            FilePath = filePath,
            ContentType = contentType,
            FileSize = fileSize,
            Status = JobStatus.Received,
            CreatedAt = now,
            UpdatedAt = now
        };
    }
}
