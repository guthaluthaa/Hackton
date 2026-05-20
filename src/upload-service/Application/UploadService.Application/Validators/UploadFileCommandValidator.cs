using FluentValidation;
using UploadService.Application.Commands;

namespace UploadService.Application.Validators;

public class UploadFileCommandValidator : AbstractValidator<UploadFileCommand>
{
    private const long MaxFileSize = 10 * 1024 * 1024; // 10 MB
    private static readonly string[] AllowedExtensions = { ".pdf", ".png", ".jpg", ".jpeg" };

    public UploadFileCommandValidator()
    {
        RuleFor(x => x.FileName)
            .NotEmpty().WithMessage("File name is required.")
            .Must(HaveAllowedExtension)
            .WithMessage($"File extension is not allowed. Allowed extensions: {string.Join(", ", AllowedExtensions)}");

        RuleFor(x => x.FileSize)
            .GreaterThan(0).WithMessage("File cannot be empty.")
            .LessThanOrEqualTo(MaxFileSize).WithMessage($"File size cannot exceed {MaxFileSize / (1024 * 1024)} MB.");

        RuleFor(x => x.ContentType)
            .NotEmpty().WithMessage("Content type is required.");

        RuleFor(x => x.FileStream)
            .NotNull().WithMessage("File stream is required.");
    }

    private static bool HaveAllowedExtension(string fileName)
    {
        if (string.IsNullOrWhiteSpace(fileName))
            return false;

        var extension = Path.GetExtension(fileName).ToLowerInvariant();
        return AllowedExtensions.Contains(extension);
    }
}
