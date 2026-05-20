using MediatR;
using ReportService.Domain.Entities;

namespace ReportService.Application.Queries;

public record GetReportByJobIdQuery(Guid JobId) : IRequest<Report?>;
