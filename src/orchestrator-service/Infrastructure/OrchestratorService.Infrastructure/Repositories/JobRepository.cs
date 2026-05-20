using Microsoft.EntityFrameworkCore;
using OrchestratorService.Domain.Entities;
using OrchestratorService.Domain.Interfaces;
using OrchestratorService.Infrastructure.Persistence;

namespace OrchestratorService.Infrastructure.Repositories;

public class JobRepository : IJobRepository
{
    private readonly OrchestratorDbContext _context;

    public JobRepository(OrchestratorDbContext context)
    {
        _context = context;
    }

    public async Task<Job?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _context.Jobs.FirstOrDefaultAsync(j => j.Id == id, cancellationToken);
    }

    public async Task AddAsync(Job job, CancellationToken cancellationToken = default)
    {
        await _context.Jobs.AddAsync(job, cancellationToken);
        await _context.SaveChangesAsync(cancellationToken);
    }

    public async Task UpdateAsync(Job job, CancellationToken cancellationToken = default)
    {
        _context.Jobs.Update(job);
        await _context.SaveChangesAsync(cancellationToken);
    }
}
