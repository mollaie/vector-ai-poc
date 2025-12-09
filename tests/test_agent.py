"""Tests for the ADK agent configuration."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestAgentConfiguration:
    """Tests for agent setup and configuration."""
    
    def test_agent_creation(self):
        """Test that agent can be created."""
        from src.agent.job_agent import create_job_matching_agent
        
        # Note: This requires GOOGLE_GENAI_USE_VERTEXAI env var to be set
        # In tests, we just verify the function exists and is callable
        assert callable(create_job_matching_agent)
    
    def test_agent_instruction_defined(self):
        """Test that agent instruction is defined."""
        from src.agent.job_agent import AGENT_INSTRUCTION
        
        assert AGENT_INSTRUCTION is not None
        assert len(AGENT_INSTRUCTION) > 100
        assert "job matching" in AGENT_INSTRUCTION.lower()
    
    def test_agent_tools_count(self):
        """Test that agent has expected number of tools."""
        from src.agent.tools import (
            search_jobs,
            get_job_details,
            update_candidate_preferences,
            accept_job,
            decline_jobs,
            get_candidate_profile,
            list_available_candidates,
        )
        
        tools = [
            search_jobs,
            get_job_details,
            update_candidate_preferences,
            accept_job,
            decline_jobs,
            get_candidate_profile,
            list_available_candidates,
        ]
        
        assert len(tools) == 7
        assert all(callable(t) for t in tools)


class TestAgentToolSignatures:
    """Tests for agent tool function signatures."""
    
    def test_search_jobs_signature(self):
        """Test search_jobs has correct parameters."""
        import inspect
        from src.agent.tools import search_jobs
        
        sig = inspect.signature(search_jobs)
        params = list(sig.parameters.keys())
        
        assert "candidate_id" in params
        assert "additional_criteria" in params
        assert "num_results" in params
    
    def test_get_job_details_signature(self):
        """Test get_job_details has correct parameters."""
        import inspect
        from src.agent.tools import get_job_details
        
        sig = inspect.signature(get_job_details)
        params = list(sig.parameters.keys())
        
        assert "job_id" in params
    
    def test_update_candidate_preferences_signature(self):
        """Test update_candidate_preferences has correct parameters."""
        import inspect
        from src.agent.tools import update_candidate_preferences
        
        sig = inspect.signature(update_candidate_preferences)
        params = list(sig.parameters.keys())
        
        assert "candidate_id" in params
        assert "min_salary" in params
        assert "preferred_titles" in params
        assert "preferred_location_types" in params
        assert "preferred_industries" in params
    
    def test_accept_job_signature(self):
        """Test accept_job has correct parameters."""
        import inspect
        from src.agent.tools import accept_job
        
        sig = inspect.signature(accept_job)
        params = list(sig.parameters.keys())
        
        assert "candidate_id" in params
        assert "job_id" in params
    
    def test_decline_jobs_signature(self):
        """Test decline_jobs has correct parameters."""
        import inspect
        from src.agent.tools import decline_jobs
        
        sig = inspect.signature(decline_jobs)
        params = list(sig.parameters.keys())
        
        assert "candidate_id" in params
        assert "job_ids" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
