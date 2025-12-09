"""Job vacancy data models."""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ExperienceLevel(str, Enum):
    """Experience level required for a job."""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class LocationType(str, Enum):
    """Work location type."""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class Job(BaseModel):
    """Job vacancy model."""
    
    id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    description: str = Field(..., description="Job description")
    required_skills: list[str] = Field(default_factory=list, description="Required skills")
    preferred_skills: list[str] = Field(default_factory=list, description="Preferred skills")
    experience_level: ExperienceLevel = Field(..., description="Required experience level")
    min_years_experience: int = Field(0, description="Minimum years of experience")
    location_type: LocationType = Field(..., description="Work location type")
    location: Optional[str] = Field(None, description="Physical location if applicable")
    salary_min: int = Field(..., description="Minimum salary in USD")
    salary_max: int = Field(..., description="Maximum salary in USD")
    industry: str = Field(..., description="Industry sector")
    department: str = Field(..., description="Department within company")
    benefits: list[str] = Field(default_factory=list, description="Job benefits")
    
    def to_embedding_text(self) -> str:
        """Convert job to text for embedding generation."""
        skills_text = ", ".join(self.required_skills + self.preferred_skills)
        return (
            f"Job Title: {self.title}\n"
            f"Company: {self.company}\n"
            f"Description: {self.description}\n"
            f"Skills: {skills_text}\n"
            f"Experience Level: {self.experience_level.value}\n"
            f"Location: {self.location_type.value}"
            f"{f' - {self.location}' if self.location else ''}\n"
            f"Salary Range: ${self.salary_min:,} - ${self.salary_max:,}\n"
            f"Industry: {self.industry}\n"
            f"Department: {self.department}"
        )


class JobCreate(BaseModel):
    """Model for creating a new job."""
    
    title: str
    company: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_level: ExperienceLevel
    min_years_experience: int = 0
    location_type: LocationType
    location: Optional[str] = None
    salary_min: int
    salary_max: int
    industry: str
    department: str
    benefits: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    """Job response model for API."""
    
    id: str
    title: str
    company: str
    description: str
    required_skills: list[str]
    experience_level: str
    location_type: str
    location: Optional[str]
    salary_range: str
    industry: str
    department: str
    
    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        """Create response from Job model."""
        return cls(
            id=job.id,
            title=job.title,
            company=job.company,
            description=job.description,
            required_skills=job.required_skills,
            experience_level=job.experience_level.value,
            location_type=job.location_type.value,
            location=job.location,
            salary_range=f"${job.salary_min:,} - ${job.salary_max:,}",
            industry=job.industry,
            department=job.department,
        )

