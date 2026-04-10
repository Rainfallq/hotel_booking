import pytest
from rest_framework.test import APIClient
from tests.conftest import UserFactory

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
PROFILE_URL = "/api/auth/profile/"


@pytest.mark.django_db
class TestRegistration:
    """TC01 – TC04"""

    def setup_method(self):
        self.client = APIClient()
        self.valid_payload = {
            "username": "amir",
            "email": "amir@test.com",
            "password": "securepass123",
        }

    def test_valid_registration_returns_201(self):
        """TC01 – Valid data returns 201 and user fields."""
        r = self.client.post(REGISTER_URL, self.valid_payload, format="json")
        assert r.status_code == 201
        assert r.data["email"] == "amir@test.com"
        assert r.data["username"] == "amir"
        assert "id" in r.data

    def test_password_not_returned_in_response(self):
        """TC01 ext – Password must never appear in the response body."""
        r = self.client.post(REGISTER_URL, self.valid_payload, format="json")
        assert "password" not in r.data

    def test_duplicate_email_returns_400(self):
        """TC02 – Duplicate email must be rejected."""
        UserFactory(email="amir@test.com")
        r = self.client.post(REGISTER_URL, self.valid_payload, format="json")
        assert r.status_code == 400

    def test_password_too_short_returns_400(self):
        """TC03 – Password shorter than 8 chars must be rejected."""
        payload = {**self.valid_payload, "password": "short"}
        r = self.client.post(REGISTER_URL, payload, format="json")
        assert r.status_code == 400

    def test_missing_email_returns_400(self):
        """TC04 – Missing email field must return 400."""
        payload = {"username": "amir", "password": "securepass123"}
        r = self.client.post(REGISTER_URL, payload, format="json")
        assert r.status_code == 400

    def test_missing_username_returns_400(self):
        """Extra – Missing username field must return 400."""
        payload = {"email": "amir@test.com", "password": "securepass123"}
        r = self.client.post(REGISTER_URL, payload, format="json")
        assert r.status_code == 400

    def test_missing_password_returns_400(self):
        """Extra – Missing password field must return 400."""
        payload = {"username": "amir", "email": "amir@test.com"}
        r = self.client.post(REGISTER_URL, payload, format="json")
        assert r.status_code == 400


@pytest.mark.django_db
class TestLogin:
    """TC05 – TC07"""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_user(self, db):
        self.user = UserFactory(email="login@test.com")
        self.user.set_password("correctpass123")
        self.user.save()

    def test_valid_credentials_return_tokens(self):
        """TC05 – Valid login returns access and refresh tokens."""
        r = self.client.post(
            LOGIN_URL,
            {"email": "login@test.com", "password": "correctpass123"},
            format="json",
        )
        assert r.status_code == 200
        assert "access" in r.data
        assert "refresh" in r.data

    def test_wrong_password_returns_401(self):
        """TC06 – Wrong password must return 401."""
        r = self.client.post(
            LOGIN_URL,
            {"email": "login@test.com", "password": "wrongpass"},
            format="json",
        )
        assert r.status_code == 401

    def test_nonexistent_email_returns_401(self):
        """TC07 – Non-existent email must return 401."""
        r = self.client.post(
            LOGIN_URL,
            {"email": "nobody@test.com", "password": "correctpass123"},
            format="json",
        )
        assert r.status_code == 401

    def test_missing_fields_returns_400(self):
        """Extra – Empty body must return 400."""
        r = self.client.post(LOGIN_URL, {}, format="json")
        assert r.status_code == 400


@pytest.mark.django_db
class TestTokenRefresh:
    """TC08 – TC09"""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def get_tokens(self, db):
        self.user = UserFactory(email="refresh@test.com")
        self.user.set_password("testpass123")
        self.user.save()
        r = self.client.post(
            LOGIN_URL,
            {"email": "refresh@test.com", "password": "testpass123"},
            format="json",
        )
        self.refresh_token = r.data.get("refresh")
        self.access_token = r.data.get("access")

    def test_valid_refresh_returns_new_access_token(self):
        """TC08 – Valid refresh token returns a new access token."""
        r = self.client.post(
            REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert r.status_code == 200
        assert "access" in r.data

    def test_invalid_refresh_token_returns_401(self):
        """TC09 – Malformed/invalid refresh token must return 401."""
        r = self.client.post(
            REFRESH_URL, {"refresh": "this.is.not.a.token"}, format="json"
        )
        assert r.status_code == 401

    def test_missing_refresh_field_returns_400(self):
        """Extra – Missing refresh field must return 400."""
        r = self.client.post(REFRESH_URL, {}, format="json")
        assert r.status_code == 400


@pytest.mark.django_db
class TestProfile:
    """TC10 – TC11"""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_user(self, db):
        self.user = UserFactory(email="profile@test.com", username="profileuser")

    def test_authenticated_request_returns_user_data(self):
        """TC10 – Authenticated GET returns correct user fields."""
        self.client.force_authenticate(user=self.user)
        r = self.client.get(PROFILE_URL)
        assert r.status_code == 200
        assert r.data["email"] == "profile@test.com"
        assert r.data["username"] == "profileuser"
        assert "id" in r.data

    def test_unauthenticated_request_returns_401(self):
        """TC11 – Request without token must return 401."""
        r = self.client.get(PROFILE_URL)
        assert r.status_code == 401

    def test_profile_returns_only_own_data(self):
        """Extra – Profile must return data for the authenticated user only."""
        other = UserFactory(email="other@test.com")
        self.client.force_authenticate(user=self.user)
        r = self.client.get(PROFILE_URL)
        assert r.data["email"] == self.user.email
        assert r.data["email"] != other.email
