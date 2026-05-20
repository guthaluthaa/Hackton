using UploadService.Domain.Entities;

namespace UploadService.Domain.Interfaces;

public interface IUploadJobRepository
{
    Task<UploadJob?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task AddAsync(UploadJob uploadJob, CancellationToken cancellationToken = default);
    Task UpdateAsync(UploadJob uploadJob, CancellationToken cancellationToken = default);
}
