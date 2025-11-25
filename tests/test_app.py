"""
Test suite for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_activity_structure(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        email = "test@mergington.edu"
        activity = "Chess Club"
        
        # Remove test email if it exists
        if email in activities[activity]["participants"]:
            activities[activity]["participants"].remove(email)
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was added
        assert email in activities[activity]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup with non-existent activity"""
        response = client.post("/activities/Nonexistent Club/signup?email=test@mergington.edu")
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_already_registered(self, client):
        """Test signup when student is already registered"""
        email = "test@mergington.edu"
        activity = "Chess Club"
        
        # Ensure student is registered
        if email not in activities[activity]["participants"]:
            activities[activity]["participants"].append(email)
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_multiple_students(self, client):
        """Test signing up multiple students for the same activity"""
        activity = "Swimming Club"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            # Remove if already exists
            if email in activities[activity]["participants"]:
                activities[activity]["participants"].remove(email)
            
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
            assert email in activities[activity]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client):
        """Test successful unregistration from an activity"""
        email = "test@mergington.edu"
        activity = "Chess Club"
        
        # Ensure student is registered
        if email not in activities[activity]["participants"]:
            activities[activity]["participants"].append(email)
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was removed
        assert email not in activities[activity]["participants"]
    
    def test_unregister_activity_not_found(self, client):
        """Test unregister with non-existent activity"""
        response = client.delete("/activities/Nonexistent Club/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_registered(self, client):
        """Test unregister when student is not registered"""
        email = "notregistered@mergington.edu"
        activity = "Chess Club"
        
        # Ensure student is not registered
        if email in activities[activity]["participants"]:
            activities[activity]["participants"].remove(email)
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_and_signup_again(self, client):
        """Test that a student can unregister and then sign up again"""
        email = "test@mergington.edu"
        activity = "Drama Club"
        
        # Sign up
        if email not in activities[activity]["participants"]:
            activities[activity]["participants"].append(email)
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Sign up again
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        assert email in activities[activity]["participants"]


class TestDataIntegrity:
    """Tests for data integrity and edge cases"""
    
    def test_activity_participant_limit_not_exceeded(self, client):
        """Test that participants list doesn't exceed max_participants"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            participant_count = len(activity_details["participants"])
            max_participants = activity_details["max_participants"]
            assert participant_count <= max_participants, \
                f"{activity_name} has {participant_count} participants but max is {max_participants}"
    
    def test_email_format_in_signup(self, client):
        """Test signup with various email formats"""
        activity = "Art Studio"
        valid_emails = [
            "valid@mergington.edu",
            "first.last@mergington.edu",
            "student123@mergington.edu"
        ]
        
        for email in valid_emails:
            # Remove if exists
            if email in activities[activity]["participants"]:
                activities[activity]["participants"].remove(email)
            
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
