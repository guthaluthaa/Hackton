using MediatR;
using ReportService.Domain.Entities;
using ReportService.Domain.Interfaces;

namespace ReportService.Application.Queries;

public class GetReportByJobIdQueryHandler : IRequestHandler<GetReportByJobIdQuery, Report?>
{
    private readonly IReportRepository _reportRepository;

    public GetReportByJobIdQueryHandler(IReportRepository reportRepository)
    {
        _reportRepository = reportRepository;
    }

    public async Task<Report?> Handle(GetReportByJobIdQuery request, CancellationToken cancellationToken)
    {
        return await _reportRepository.GetByJobIdAsync(request.JobId, cancellationToken);
    }
}
