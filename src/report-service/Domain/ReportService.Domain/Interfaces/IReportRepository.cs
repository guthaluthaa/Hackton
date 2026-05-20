using ReportService.Domain.Entities;

namespace ReportService.Domain.Interfaces;

public interface IReportRepository
{
    Task<Report?> GetByJobIdAsync(Guid jobId, CancellationToken cancellationToken = default);
    Task AddAsync(Report report, CancellationToken cancellationToken = default);
}
