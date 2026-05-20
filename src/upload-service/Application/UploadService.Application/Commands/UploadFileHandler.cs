using MassTransit;
using MediatR;
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

    public UploadFileHandler(
        IStorageService storageService,
        IUploadJobRepository uploadJobRepository,
        IPublishEndpoint publishEndpoint)
    {
        _storageService = storageService;
        _uploadJobRepository = uploadJobRepository;
        _publishEndpoint = publishEndpoint;
    }

    public async Task<UploadFileResult> Handle(UploadFileCommand request, CancellationToken cancellationToken)
    {
        // Upload file to MinIO
        var filePath = await _storageService.UploadFileAsync(
            request.FileStream,
            request.FileName,
            request.ContentType,
            cancellationToken);

        // Create domain entity
        var uploadJob = UploadJob.Create(
            request.FileName,
            filePath,
            request.ContentType,
            request.FileSize);

        // Persist to database
        await _uploadJobRepository.AddAsync(uploadJob, cancellationToken);

        // Publish event
        await _publishEndpoint.Publish(new JobCreatedEvent
        {
            JobId = uploadJob.Id,
            FileName = uploadJob.FileName,
            FilePath = uploadJob.FilePath,
            ContentType = uploadJob.ContentType,
            FileSize = uploadJob.FileSize,
            CreatedAt = uploadJob.CreatedAt
        }, cancellationToken);

        return new UploadFileResult(uploadJob.Id, uploadJob.FileName, uploadJob.FilePath);
    }
}
