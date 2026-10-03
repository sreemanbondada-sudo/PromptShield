import pytest

from fastapi.testclient import TestClient

from auth_dependencies import require_admin
from auth_service import create_access_token
from main import app


client = TestClient(app)

TEST_ADMIN_USERNAME = "promptshield-test-admin"
TEST_ADMIN_PASSWORD = "promptshield-test-password"

DIFFERENT_JWT_SECRET = (
    "different-test-jwt-secret-"
    "with-at-least-32-characters"
)


@pytest.fixture
def enforce_real_authentication(
    configure_test_environment,
):
    """Remove the general-test authentication override."""
    previous_override = (
        app.dependency_overrides.pop(
            require_admin,
            None,
        )
    )

    yield

    if previous_override is not None:
        app.dependency_overrides[
            require_admin
        ] = previous_override


def login() -> dict:
    """Log in using the configured test administrator."""
    response = client.post(
        "/auth/login",
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": TEST_ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()


def test_login_returns_access_token(
    enforce_real_authentication,
):
    result = login()

    assert isinstance(
        result["access_token"],
        str,
    )

    assert result["access_token"]
    assert result["token_type"] == "bearer"
    assert result["expires_in"] == 1800


def test_incorrect_login_is_rejected(
    enforce_real_authentication,
):
    response = client.post(
        "/auth/login",
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_missing_token_is_rejected(
    enforce_real_authentication,
):
    response = client.get("/events")

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_valid_token_allows_protected_request(
    enforce_real_authentication,
):
    token = login()["access_token"]

    response = client.get(
        "/events",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert "events" in response.json()


def test_invalid_token_is_rejected(
    enforce_real_authentication,
):
    response = client.get(
        "/events",
        headers={
            "Authorization": (
                "Bearer not-a-valid-token"
            ),
        },
    )

    assert response.status_code == 401


def test_wrongly_signed_token_is_rejected(
    enforce_real_authentication,
):
    token = create_access_token(
        subject=TEST_ADMIN_USERNAME,
        secret=DIFFERENT_JWT_SECRET,
    )

    response = client.get(
        "/events",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401


def test_token_for_another_user_is_rejected(
    enforce_real_authentication,
):
    token = create_access_token(
        subject="different-user",
    )

    response = client.get(
        "/events",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401


def test_public_health_endpoint_needs_no_token(
    enforce_real_authentication,
):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }