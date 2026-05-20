using Microsoft.EntityFrameworkCore;
using ReportService.Domain.Entities;
using ReportService.Domain.Interfaces;
using ReportService.Infrastructure.Persistence;

namespace ReportService.Infrastructure.Repositories;

public class ReportRepository : IReportRepository
{
    private readonly ReportDbContext _context;

    public ReportRepository(ReportDbContext context)
    {
        _context = context;
    }

    public async Task<Report?> GetByJobIdAsync(Guid jobId, CancellationToken cancellationToken = default)
    {
        return await _context.Reports
            .FirstOrDefaultAsync(r => r.JobId == jobId, cancellationToken);
    }

    public async Task AddAsync(Report report, CancellationToken cancellationToken = default)
    {
        await _context.Reports.AddAsync(report, cancellationToken);
        await _context.SaveChangesAsync(cancellationToken);
    }
}
