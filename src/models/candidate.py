"""Candidate data models."""

from typing import Optional
from pydantic import BaseModel, Field

from src.models.job import ExperienceLevel, LocationType


class Candidate(BaseModel):
    """Candidate profile model."""
    
    id: str = Field(..., description="Unique candidate identifier")
    name: str = Field(..., description="Candidate name")
    email: str = Field(..., description="Candidate email")
    summary: str = Field(..., description="Professional summary")
    skills: list[str] = Field(default_factory=list, description="Candidate skills")
    years_experience: int = Field(0, description="Total years of experience")
    current_title: Optional[str] = Field(None, description="Current job title")
    
    # Preferences
    preferred_titles: list[str] = Field(default_factory=list, description="Preferred job titles")
    preferred_location_types: list[LocationType] = Field(
        default_factory=list, description="Preferred work locations"
    )
    preferred_locations: list[str] = Field(
        default_factory=list, description="Preferred physical locations"
    )
    min_salary: int = Field(0, description="Minimum acceptable salary")
    max_salary: Optional[int] = Field(None, description="Maximum expected salary")
    preferred_industries: list[str] = Field(
        default_factory=list, description="Preferred industries"
    )
    
    # Tracking
    declined_job_ids: list[str] = Field(
        default_factory=list, description="IDs of declined jobs"
    )
    accepted_job_id: Optional[str] = Field(None, description="ID of accepted job")
    
    def to_embedding_text(self) -> str:
        """Convert candidate profile to text for embedding generation."""
        skills_text = ", ".join(self.skills)
        titles_text = ", ".join(self.preferred_titles) if self.preferred_titles else "Open to opportunities"
        locations_text = ", ".join([loc.value for loc in self.preferred_location_types]) if self.preferred_location_types else "Flexible"
        industries_text = ", ".join(self.preferred_industries) if self.preferred_industries else "Open to all industries"
        
        return (
            f"Professional Summary: {self.summary}\n"
            f"Skills: {skills_text}\n"
            f"Years of Experience: {self.years_experience}\n"
            f"Current Title: {self.current_title or 'Not specified'}\n"
            f"Looking for: {titles_text}\n"
            f"Preferred Work Style: {locations_text}\n"
            f"Minimum Salary: ${self.min_salary:,}\n"
            f"Preferred Industries: {industries_text}"
        )
    
    def get_experience_level(self) -> ExperienceLevel:
        """Determine experience level based on years of experience."""
        if self.years_experience < 2:
            return ExperienceLevel.JUNIOR
        elif self.years_experience < 5:
            return ExperienceLevel.MID
        elif self.years_experience < 8:
            return ExperienceLevel.SENIOR
        elif self.years_experience < 12:
            return ExperienceLevel.LEAD
        else:
            return ExperienceLevel.PRINCIPAL


class CandidateCreate(BaseModel):
    """Model for creating a new candidate."""
    
    name: str
    email: str
    summary: str
    skills: list[str] = Field(default_factory=list)
    years_experience: int = 0
    current_title: Optional[str] = None
    preferred_titles: list[str] = Field(default_factory=list)
    preferred_location_types: list[LocationType] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    min_salary: int = 0
    max_salary: Optional[int] = None
    preferred_industries: list[str] = Field(default_factory=list)


class CandidateUpdate(BaseModel):
    """Model for updating candidate preferences."""
    
    summary: Optional[str] = None
    skills: Optional[list[str]] = None
    years_experience: Optional[int] = None
    current_title: Optional[str] = None
    preferred_titles: Optional[list[str]] = None
    preferred_location_types: Optional[list[LocationType]] = None
    preferred_locations: Optional[list[str]] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    preferred_industries: Optional[list[str]] = None


class CandidateResponse(BaseModel):
    """Candidate response model for API."""
    
    id: str
    name: str
    email: str
    summary: str
    skills: list[str]
    years_experience: int
    current_title: Optional[str]
    preferred_titles: list[str]
    preferred_location_types: list[str]
    min_salary: int
    preferred_industries: list[str]
    has_accepted_job: bool
    declined_jobs_count: int
    
    @classmethod
    def from_candidate(cls, candidate: Candidate) -> "CandidateResponse":
        """Create response from Candidate model."""
        return cls(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            summary=candidate.summary,
            skills=candidate.skills,
            years_experience=candidate.years_experience,
            current_title=candidate.current_title,
            preferred_titles=candidate.preferred_titles,
            preferred_location_types=[loc.value for loc in candidate.preferred_location_types],
            min_salary=candidate.min_salary,
            preferred_industries=candidate.preferred_industries,
            has_accepted_job=candidate.accepted_job_id is not None,
            declined_jobs_count=len(candidate.declined_job_ids),
        )

