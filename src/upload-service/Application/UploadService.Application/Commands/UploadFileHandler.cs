using MassTransit;
using MediatR;
using Microsoft.Extensions.Logging;
using Shared.Events;
using UploadService.Application.Interfaces;
using UploadService.Domain.Entities;
using UploadService.Domain.Interfaces;

namespace UploadService.Application.Commands;

public class UploadFileHandler : IRequestHandler<UploadFileCommand, UploadFileResult>
{
    private readonly IStorageService _storageService;
    private readonly IUploadJobRepository _uploadJobRepository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<UploadFileHandler> _logger;

    public UploadFileHandler(
        IStorageService storageService,
        IUploadJobRepository uploadJobRepository,
        IPublishEndpoint publishEndpoint,
        ILogger<UploadFileHandler> logger)
    {
        _storageService = storageService;
        _uploadJobRepository = uploadJobRepository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task<UploadFileResult> Handle(UploadFileCommand request, CancellationToken cancellationToken)
    {
        _logger.LogInformation("Processing upload for {FileName} ({FileSize} bytes, {ContentType})",
            request.FileName, request.FileSize, request.ContentType);

        var filePath = await _storageService.UploadFileAsync(
            request.FileStream,
            request.FileName,
            request.ContentType,
            cancellationToken);

        _logger.LogInformation("File stored at {FilePath}", filePath);

        var uploadJob = UploadJob.Create(
            request.FileName,
            filePath,
            request.ContentType,
            request.FileSize);

        await _uploadJobRepository.AddAsync(uploadJob, cancellationToken);

        _logger.LogInformation("UploadJob created with JobId: {JobId}", uploadJob.Id);

        await _publishEndpoint.Publish(new JobCreatedEvent
        {
            JobId = uploadJob.Id,
            FileName = uploadJob.FileName,
            FilePath = uploadJob.FilePath,
            ContentType = uploadJob.ContentType,
            FileSize = uploadJob.FileSize,
            LlmProvider = request.LlmProvider ?? string.Empty,
            LlmApiKey = request.LlmApiKey ?? string.Empty,
            CreatedAt = uploadJob.CreatedAt
        }, cancellationToken);

        _logger.LogInformation("Published JobCreatedEvent for JobId: {JobId}", uploadJob.Id);

        return new UploadFileResult(uploadJob.Id, uploadJob.FileName, uploadJob.FilePath);
    }
}
