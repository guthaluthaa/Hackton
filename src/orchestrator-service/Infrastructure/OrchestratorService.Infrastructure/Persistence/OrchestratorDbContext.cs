using Microsoft.EntityFrameworkCore;
using OrchestratorService.Domain.Entities;

namespace OrchestratorService.Infrastructure.Persistence;

public class OrchestratorDbContext : DbContext
{
    public OrchestratorDbContext(DbContextOptions<OrchestratorDbContext> options) : base(options)
    {
    }

    public DbSet<Job> Jobs => Set<Job>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Job>(entity =>
        {
            entity.HasKey(j => j.Id);
            entity.Property(j => j.FileName).IsRequired().HasMaxLength(500);
            entity.Property(j => j.FilePath).IsRequired().HasMaxLength(1000);
            entity.Property(j => j.Status).IsRequired().HasConversion<string>();
            entity.Property(j => j.ErrorMessage).HasMaxLength(2000);
        });
    }
}
