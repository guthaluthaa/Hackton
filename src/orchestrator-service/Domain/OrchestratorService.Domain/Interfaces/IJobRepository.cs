using OrchestratorService.Domain.Entities;

namespace OrchestratorService.Domain.Interfaces;

public interface IJobRepository
{
    Task<Job?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task AddAsync(Job job, CancellationToken cancellationToken = default);
    Task UpdateAsync(Job job, CancellationToken cancellationToken = default);
}
