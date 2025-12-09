#!/usr/bin/env python3
"""Generate mock job and candidate data."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from data_generator import DataGenerator


def main():
    """Generate mock jobs and candidates."""
    print("=" * 50)
    print("Vector AI PoC - Data Generation")
    print("=" * 50)
    
    settings = get_settings()
    generator = DataGenerator(seed=42)  # Fixed seed for reproducibility
    
    # Generate tech jobs
    print("\n📊 Generating 100 tech job vacancies...")
    tech_jobs = generator.generate_jobs(count=100)
    
    # Generate blue-collar jobs
    print("🔧 Generating 200 blue-collar job vacancies...")
    bluecollar_jobs = generator.generate_bluecollar_jobs(count=200)
    
    # Combine all jobs
    all_jobs = tech_jobs + bluecollar_jobs
    generator.save_jobs(all_jobs, settings.jobs_file)
    print(f"✓ Saved {len(all_jobs)} total jobs to {settings.jobs_file}")
    
    # Print sample tech jobs
    print("\nSample tech jobs:")
    for job in tech_jobs[:2]:
        print(f"  - {job.title} at {job.company} (${job.salary_min:,} - ${job.salary_max:,}/year)")
    
    # Print sample blue-collar jobs  
    print("\nSample blue-collar jobs:")
    for job in bluecollar_jobs[:3]:
        # Convert annual back to hourly for display
        hourly = job.salary_min // 2080
        print(f"  - {job.title} at {job.company} (~${hourly}/hour)")
    
    # Generate tech candidates
    print("\n👔 Generating 10 tech candidate profiles...")
    tech_candidates = generator.generate_candidates(count=10)
    
    # Generate blue-collar candidates
    print("👷 Generating 20 blue-collar candidate profiles...")
    bluecollar_candidates = generator.generate_bluecollar_candidates(count=20)
    
    # Combine all candidates
    all_candidates = tech_candidates + bluecollar_candidates
    generator.save_candidates(all_candidates, settings.candidates_file)
    print(f"✓ Saved {len(all_candidates)} total candidates to {settings.candidates_file}")
    
    # Print sample tech candidates
    print("\nSample tech candidates:")
    for candidate in tech_candidates[:2]:
        print(f"  - {candidate.name}: {candidate.current_title} ({candidate.years_experience} years)")
    
    # Print sample blue-collar candidates
    print("\nSample blue-collar candidates:")
    for candidate in bluecollar_candidates[:3]:
        hourly = candidate.min_salary // 2080
        print(f"  - {candidate.name}: {candidate.current_title} (looking for ~${hourly}/hour)")
    
    print("\n" + "=" * 50)
    print("Data generation complete!")
    print("=" * 50)
    print(f"\nTotal: {len(all_jobs)} jobs, {len(all_candidates)} candidates")
    print("\nNext step: python scripts/create_embeddings.py")


if __name__ == "__main__":
    main()

