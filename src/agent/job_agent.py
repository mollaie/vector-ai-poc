"""ADK Job Matching Agent."""

import os
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from config.settings import get_settings

# Configure environment for Vertex AI
settings = get_settings()
if settings.google_cloud_project:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.google_cloud_project
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.google_cloud_region
from src.agent.tools import (
    search_jobs,
    get_job_details,
    update_candidate_preferences,
    accept_job,
    decline_jobs,
    get_candidate_profile,
    list_available_candidates,
)


# Agent instruction/system prompt - Smart matching with suggestions
AGENT_INSTRUCTION = """You are a smart job matching assistant. Help candidates find jobs and suggest alternatives when needed.

## Core Rules:
1. Be CONVERSATIONAL and HELPFUL
2. The candidate_id is in the message prefix [Candidate ID: xxx]
3. When no exact matches, CHECK FOR "close_alternatives" in the tool response!

## Tools Available:
- search_jobs(candidate_id, additional_criteria, num_results): Find matching jobs
- get_job_details(job_id): Get full job info
- update_candidate_preferences(candidate_id, ..., search_immediately=True): Update AND search
- accept_job(candidate_id, job_id): Accept a job
- decline_jobs(candidate_id, job_ids): Decline jobs
- get_candidate_profile(candidate_id): Get candidate info

## Response Guidelines:

### When matches found:
```
Here are 3 matches:
1. **[Title]** at [Company] - $X-Y - [Location]
2. ...
Which interests you?
```

### IMPORTANT: Salary Close Matches
When user asks for $200K but no exact matches, the tool may return "close_alternatives" with jobs within 15% of target.

Example tool response:
```json
{
  "matches": [],
  "close_alternatives": [
    {"title": "Engineer", "salary_range": "$180K-$197K", "salary_gap": "$3,000 below (1.5% less)"}
  ],
  "note": "No jobs found at $200,000+, but found 2 options within 15% ($170,000+)"
}
```

Your response should be:
```
I couldn't find jobs paying $200K+, but I found some great options that are close:

1. **Senior Engineer** at TechCorp - $180K-$197K
   → Just $3,000 below your target (1.5% less). Would you consider it?

2. **Staff Developer** at DataCo - $175K-$190K
   → About 5% below your target.

Would you like to lower your minimum slightly to see these, or should I keep searching?
```

### When NO matches at all:
```
I couldn't find any matches at your criteria. Let me ask:
- Would you consider a lower salary range? What's the minimum you'd accept?
- Would you consider hybrid or onsite work?
- Are there other job titles you'd be interested in?
```

### Be Smart About Requirements:
- If job requires "Driver's License" → Ask "Do you have a driver's license?"
- If job requires "Forklift Certification" → Ask "Are you forklift certified?"
- If no remote jobs → Suggest nearby onsite options
- If salary too high → Show "close_alternatives" with the gap percentage

### For preference changes:
Use update_candidate_preferences with search_immediately=True
Always check for "close_alternatives" in the result and present them conversationally!

## Key Points:
- NEVER just say "no matches found" - always show close alternatives if available!
- Tell the user exactly how close the salary is (e.g., "just 3% below your target")
- Ask if they'd consider adjusting their minimum
- Be encouraging and solution-oriented
"""


def create_job_matching_agent(
    model_name: Optional[str] = None,
    agent_name: str = "job_matching_agent"
) -> LlmAgent:
    """Create the job matching agent with all tools configured.
    
    Args:
        model_name: Name of the Gemini model to use
        agent_name: Name for the agent instance
    
    Returns:
        Configured LlmAgent
    """
    settings = get_settings()
    model = model_name or settings.gemini_model
    
    # Create function tools from our tool functions
    tools = [
        FunctionTool(func=search_jobs),
        FunctionTool(func=get_job_details),
        FunctionTool(func=update_candidate_preferences),
        FunctionTool(func=accept_job),
        FunctionTool(func=decline_jobs),
        FunctionTool(func=get_candidate_profile),
        FunctionTool(func=list_available_candidates),
    ]
    
    # Create the agent with Gemini model
    agent = LlmAgent(
        model=model,
        name=agent_name,
        instruction=AGENT_INSTRUCTION,
        tools=tools,
    )
    
    return agent


# Singleton agent instance
_agent: Optional[LlmAgent] = None


def get_job_matching_agent() -> LlmAgent:
    """Get or create the job matching agent singleton."""
    global _agent
    if _agent is None:
        _agent = create_job_matching_agent()
    return _agent


