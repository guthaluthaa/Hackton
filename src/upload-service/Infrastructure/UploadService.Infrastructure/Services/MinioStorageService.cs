using Microsoft.Extensions.Configuration;
using Minio;
using Minio.DataModel.Args;
using UploadService.Application.Interfaces;

namespace UploadService.Infrastructure.Services;

public class MinioStorageService : IStorageService
{
    private readonly IMinioClient _minioClient;
    private readonly string _bucketName;

    public MinioStorageService(IMinioClient minioClient, IConfiguration configuration)
    {
        _minioClient = minioClient;
        _bucketName = configuration["MinIO:BucketName"] ?? "uploads";
    }

    public async Task<string> UploadFileAsync(Stream fileStream, string fileName, string contentType, CancellationToken cancellationToken = default)
    {
        // Ensure bucket exists
        var bucketExists = await _minioClient.BucketExistsAsync(
            new BucketExistsArgs().WithBucket(_bucketName), cancellationToken);

        if (!bucketExists)
        {
            await _minioClient.MakeBucketAsync(
                new MakeBucketArgs().WithBucket(_bucketName), cancellationToken);
        }

        // Generate unique file path
        var objectName = $"{Guid.NewGuid()}/{fileName}";

        // Upload file
        await _minioClient.PutObjectAsync(new PutObjectArgs()
            .WithBucket(_bucketName)
            .WithObject(objectName)
            .WithStreamData(fileStream)
            .WithObjectSize(fileStream.Length)
            .WithContentType(contentType), cancellationToken);

        return $"{_bucketName}/{objectName}";
    }
}
