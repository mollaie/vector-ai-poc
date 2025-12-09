"""Tests for API endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestPreferenceExtraction:
    """Tests for preference extraction from user messages."""
    
    def test_extract_salary_preference(self):
        """Test extracting salary from message."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I want minimum $50,000 salary", {}
        )
        
        assert prefs["min_salary"] == 50000
        assert changes["min_salary"] == 50000
    
    def test_extract_salary_with_k(self):
        """Test extracting salary with k notation."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "Looking for at least 75k", {}
        )
        
        assert prefs["min_salary"] == 75000
        assert changes["min_salary"] == 75000
    
    def test_extract_remote_preference(self):
        """Test extracting remote location preference."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I need a fully remote job", {}
        )
        
        assert prefs["location"] == "remote"
        assert changes["preferred_location_types"] == ["remote"]
    
    def test_extract_hybrid_preference(self):
        """Test extracting hybrid location preference."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I'm open to hybrid positions", {}
        )
        
        assert prefs["location"] == "hybrid"
        assert changes["preferred_location_types"] == ["hybrid"]
    
    def test_extract_onsite_preference(self):
        """Test extracting onsite location preference."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I prefer on-site work", {}
        )
        
        assert prefs["location"] == "onsite"
        assert changes["preferred_location_types"] == ["onsite"]
    
    def test_extract_driver_job_interest(self):
        """Test extracting driver job interest."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I'm looking for driver jobs", {}
        )
        
        assert prefs["job_interest"] == "driver"
        assert "Driver" in changes["preferred_titles"]
    
    def test_extract_engineer_job_interest(self):
        """Test extracting engineer job interest."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I want an engineer position", {}
        )
        
        assert prefs["job_interest"] == "engineer"
        assert "Engineer" in changes["preferred_titles"]
    
    def test_extract_driving_license_yes(self):
        """Test extracting driver's license confirmation."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "Yes, I have a driving license", {}
        )
        
        assert prefs["has_license"] == "yes"
        assert changes["add_skill"] == "Valid Driver's License"
    
    def test_extract_driving_license_mentioned(self):
        """Test extracting driver's license mention."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "Do I need a driving license?", {}
        )
        
        assert prefs["has_license"] == "mentioned"
        assert "add_skill" not in changes  # Only add skill when confirmed
    
    def test_extract_industry_preference(self):
        """Test extracting industry preference."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "I want to work in logistics", {}
        )
        
        assert prefs["industry"] == "Logistics"
        assert changes["preferred_industries"] == ["Logistics"]
    
    def test_no_changes_from_irrelevant_message(self):
        """Test that irrelevant messages don't extract preferences."""
        from src.api.routes import extract_preferences_from_message
        
        prefs, changes = extract_preferences_from_message(
            "Hello, how are you today?", {}
        )
        
        assert changes == {}
    
    def test_preserves_existing_preferences(self):
        """Test that existing preferences are preserved."""
        from src.api.routes import extract_preferences_from_message
        
        existing = {"min_salary": 50000, "location": "remote"}
        prefs, changes = extract_preferences_from_message(
            "I want driver jobs", existing
        )
        
        assert prefs["min_salary"] == 50000  # Preserved
        assert prefs["location"] == "remote"  # Preserved
        assert prefs["job_interest"] == "driver"  # Added


class TestPreferencePersistence:
    """Tests for preference persistence to candidate profile."""
    
    def test_persist_salary_change(self, test_client, mock_candidate_service):
        """Test persisting salary preference change."""
        from src.api.routes import persist_preference_changes
        
        result = persist_preference_changes(
            "candidate-test-001",
            {"min_salary": 100000}
        )
        
        assert result == True
    
    def test_persist_empty_changes(self, test_client, mock_candidate_service):
        """Test that empty changes return False."""
        from src.api.routes import persist_preference_changes
        
        result = persist_preference_changes(
            "candidate-test-001",
            {}
        )
        
        assert result == False
    
    def test_persist_invalid_candidate(self, test_client, mock_candidate_service):
        """Test persisting to invalid candidate."""
        from src.api.routes import persist_preference_changes
        
        result = persist_preference_changes(
            "non-existent-candidate",
            {"min_salary": 100000}
        )
        
        assert result == False


class TestConversationContext:
    """Tests for conversation context building."""
    
    def test_build_context_with_history(self):
        """Test building context includes conversation history."""
        from src.api.routes import build_conversation_context, _sessions
        
        # Create a test session
        _sessions["test-session"] = {
            "candidate_id": "test-candidate",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            "preferences": {"location": "remote"}
        }
        
        context = build_conversation_context(
            "test-session",
            "What jobs do you have?",
            "test-candidate"
        )
        
        assert "[Candidate ID: test-candidate]" in context
        assert "[Stated Preferences:" in context
        assert "remote" in context
        assert "[Recent Conversation:]" in context
        assert "Hello" in context
        assert "[Current Message]: What jobs do you have?" in context
        
        # Cleanup
        del _sessions["test-session"]
    
    def test_build_context_empty_session(self):
        """Test building context for new session."""
        from src.api.routes import build_conversation_context, _sessions
        
        _sessions["new-session"] = {
            "candidate_id": "test-candidate",
            "messages": [],
            "preferences": {}
        }
        
        context = build_conversation_context(
            "new-session",
            "Find me jobs",
            "test-candidate"
        )
        
        assert "[Candidate ID: test-candidate]" in context
        assert "[Current Message]: Find me jobs" in context
        assert "[Recent Conversation:]" not in context  # No history
        
        # Cleanup
        del _sessions["new-session"]


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, test_client):
        """Test health endpoint returns healthy status."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "models" in data


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_returns_info(self, test_client):
        """Test root endpoint returns API info."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Vector AI Job Matching PoC"
        assert "endpoints" in data


class TestCandidatesAPI:
    """Tests for candidates API endpoints."""
    
    def test_list_candidates(self, test_client):
        """Test listing all candidates."""
        response = test_client.get("/api/candidates")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # From fixtures
    
    def test_get_candidate_exists(self, test_client):
        """Test getting existing candidate."""
        response = test_client.get("/api/candidates/candidate-test-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "candidate-test-001"
        assert data["name"] == "John Doe"
    
    def test_get_candidate_not_found(self, test_client):
        """Test getting non-existent candidate."""
        response = test_client.get("/api/candidates/non-existent")
        
        assert response.status_code == 404
    
    def test_update_candidate(self, test_client):
        """Test updating candidate."""
        response = test_client.patch(
            "/api/candidates/candidate-test-001",
            json={"min_salary": 200000}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["min_salary"] == 200000
    
    def test_update_candidate_not_found(self, test_client):
        """Test updating non-existent candidate."""
        response = test_client.patch(
            "/api/candidates/non-existent",
            json={"min_salary": 100000}
        )
        
        assert response.status_code == 404


class TestJobsAPI:
    """Tests for jobs API endpoints."""
    
    def test_list_jobs(self, test_client):
        """Test listing jobs."""
        response = test_client.get("/api/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20  # Default limit
    
    def test_list_jobs_pagination(self, test_client):
        """Test jobs pagination."""
        response = test_client.get("/api/jobs?offset=0&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_job_exists(self, test_client):
        """Test getting existing job."""
        response = test_client.get("/api/jobs/job-test-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-test-001"
        assert data["title"] == "Software Engineer"
    
    def test_get_job_not_found(self, test_client):
        """Test getting non-existent job."""
        response = test_client.get("/api/jobs/non-existent")
        
        assert response.status_code == 404


class TestSessionsAPI:
    """Tests for sessions API endpoints."""
    
    def test_create_session(self, test_client):
        """Test creating a session."""
        response = test_client.post(
            "/api/sessions",
            json={"candidate_id": "candidate-test-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["candidate_id"] == "candidate-test-001"
        assert data["message_count"] == 0
    
    def test_create_session_invalid_candidate(self, test_client):
        """Test creating session for non-existent candidate."""
        response = test_client.post(
            "/api/sessions",
            json={"candidate_id": "non-existent"}
        )
        
        assert response.status_code == 404
    
    def test_get_session_not_found(self, test_client):
        """Test getting non-existent session."""
        response = test_client.get("/api/sessions/non-existent-session")
        
        assert response.status_code == 404


class TestAgentTools:
    """Tests for agent tool functions."""
    
    def test_tools_exist(self):
        """Test that all agent tools are defined."""
        from src.agent.tools import (
            search_jobs,
            get_job_details,
            update_candidate_preferences,
            accept_job,
            decline_jobs,
            get_candidate_profile,
            list_available_candidates,
        )
        
        assert callable(search_jobs)
        assert callable(get_job_details)
        assert callable(update_candidate_preferences)
        assert callable(accept_job)
        assert callable(decline_jobs)
        assert callable(get_candidate_profile)
        assert callable(list_available_candidates)
    
    def test_get_job_details_returns_json(self):
        """Test get_job_details returns valid JSON."""
        import json
        from unittest.mock import MagicMock
        from src.agent.tools import get_job_details
        
        # Mock ToolContext
        mock_context = MagicMock()
        mock_context.state = {}
        
        # This will return error JSON since no data is loaded
        result = get_job_details(mock_context, "non-existent")
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert "error" in parsed
    
    def test_get_candidate_profile_returns_json(self):
        """Test get_candidate_profile returns valid JSON."""
        import json
        from unittest.mock import MagicMock
        from src.agent.tools import get_candidate_profile
        
        # Mock ToolContext
        mock_context = MagicMock()
        mock_context.state = {}
        
        result = get_candidate_profile(mock_context, "non-existent")
        
        parsed = json.loads(result)
        assert "error" in parsed

