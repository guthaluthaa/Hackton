using Microsoft.EntityFrameworkCore;
using ReportService.Domain.Entities;

namespace ReportService.Infrastructure.Persistence;

public class ReportDbContext : DbContext
{
    public ReportDbContext(DbContextOptions<ReportDbContext> options) : base(options)
    {
    }

    public DbSet<Report> Reports => Set<Report>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Report>(entity =>
        {
            entity.HasKey(r => r.Id);
            entity.HasIndex(r => r.JobId).IsUnique();
            entity.Property(r => r.Components).IsRequired();
            entity.Property(r => r.Risks).IsRequired();
            entity.Property(r => r.Recommendations).IsRequired();
            entity.Property(r => r.CreatedAt).IsRequired();
        });
    }
}
