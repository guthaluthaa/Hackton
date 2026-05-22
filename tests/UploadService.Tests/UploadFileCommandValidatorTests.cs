using FluentAssertions;
using Xunit;
using UploadService.Application.Validators;
using UploadService.Application.Commands;

namespace UploadService.Tests;

public class UploadFileCommandValidatorTests
{
    private readonly UploadFileCommandValidator _validator = new();

    [Theory]
    [InlineData("document.pdf")]
    [InlineData("image.png")]
    [InlineData("photo.jpg")]
    [InlineData("picture.jpeg")]
    public void Validate_WithAllowedExtension_ShouldPass(string fileName)
    {
        var command = new UploadFileCommand(
            FileStream: Stream.Null,
            FileName: fileName,
            ContentType: "application/octet-stream",
            FileSize: 1024,
            LlmProvider: null,
            LlmApiKey: null);

        var result = _validator.Validate(command);

        result.IsValid.Should().BeTrue();
    }

    [Theory]
    [InlineData("script.exe")]
    [InlineData("virus.bat")]
    [InlineData("hack.sh")]
    [InlineData("")]
    public void Validate_WithInvalidExtensionOrEmpty_ShouldFail(string fileName)
    {
        var command = new UploadFileCommand(
            FileStream: Stream.Null,
            FileName: fileName,
            ContentType: "application/octet-stream",
            FileSize: 1024,
            LlmProvider: null,
            LlmApiKey: null);

        var result = _validator.Validate(command);

        result.IsValid.Should().BeFalse();
    }
}
