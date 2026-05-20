using MediatR;
using OrchestratorService.Domain.Entities;
using OrchestratorService.Domain.Interfaces;

namespace OrchestratorService.Application.Queries;

public record GetJobStatusQuery(Guid JobId) : IRequest<Job?>;

public class GetJobStatusQueryHandler : IRequestHandler<GetJobStatusQuery, Job?>
{
    private readonly IJobRepository _jobRepository;

    public GetJobStatusQueryHandler(IJobRepository jobRepository)
    {
        _jobRepository = jobRepository;
    }

    public async Task<Job?> Handle(GetJobStatusQuery request, CancellationToken cancellationToken)
    {
        return await _jobRepository.GetByIdAsync(request.JobId, cancellationToken);
    }
}
