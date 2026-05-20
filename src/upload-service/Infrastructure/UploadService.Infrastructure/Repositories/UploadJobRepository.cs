using Microsoft.EntityFrameworkCore;
using UploadService.Domain.Entities;
using UploadService.Domain.Interfaces;
using UploadService.Infrastructure.Persistence;

namespace UploadService.Infrastructure.Repositories;

public class UploadJobRepository : IUploadJobRepository
{
    private readonly UploadDbContext _dbContext;

    public UploadJobRepository(UploadDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<UploadJob?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _dbContext.UploadJobs.FirstOrDefaultAsync(x => x.Id == id, cancellationToken);
    }

    public async Task AddAsync(UploadJob uploadJob, CancellationToken cancellationToken = default)
    {
        await _dbContext.UploadJobs.AddAsync(uploadJob, cancellationToken);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task UpdateAsync(UploadJob uploadJob, CancellationToken cancellationToken = default)
    {
        _dbContext.UploadJobs.Update(uploadJob);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
