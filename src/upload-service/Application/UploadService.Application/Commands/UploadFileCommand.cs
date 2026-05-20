using MediatR;

namespace UploadService.Application.Commands;

public record UploadFileCommand(
    Stream FileStream,
    string FileName,
    string ContentType,
    long FileSize
) : IRequest<UploadFileResult>;

public record UploadFileResult(Guid JobId, string FileName, string FilePath);
