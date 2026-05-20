using Microsoft.EntityFrameworkCore;
using UploadService.Domain.Entities;

namespace UploadService.Infrastructure.Persistence;

public class UploadDbContext : DbContext
{
    public UploadDbContext(DbContextOptions<UploadDbContext> options) : base(options)
    {
    }

    public DbSet<UploadJob> UploadJobs => Set<UploadJob>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<UploadJob>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.FileName).IsRequired().HasMaxLength(256);
            entity.Property(e => e.FilePath).IsRequired().HasMaxLength(1024);
            entity.Property(e => e.ContentType).IsRequired().HasMaxLength(128);
            entity.Property(e => e.FileSize).IsRequired();
            entity.Property(e => e.Status).IsRequired().HasConversion<string>();
            entity.Property(e => e.CreatedAt).IsRequired();
            entity.Property(e => e.UpdatedAt).IsRequired();
        });
    }
}
