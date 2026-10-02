from fastapi import FastAPI
from fastapi.testclient import TestClient

from security_headers import (
    SECURITY_HEADERS,
    SecurityHeadersMiddleware,
)


def create_test_client():
    test_app = FastAPI()

    test_app.add_middleware(
        SecurityHeadersMiddleware
    )

    @test_app.get("/health")
    def health_endpoint():
        return {
            "status": "healthy",
        }

    return TestClient(test_app)


def test_security_headers_are_added():
    test_client = create_test_client()

    response = test_client.get("/health")

    assert response.status_code == 200

    for header_name, expected_value in (
        SECURITY_HEADERS.items()
    ):
        assert (
            response.headers[header_name]
            == expected_value
        )


def test_security_headers_are_added_to_errors():
    test_client = create_test_client()

    response = test_client.get(
        "/endpoint-that-does-not-exist"
    )

    assert response.status_code == 404

    for header_name, expected_value in (
        SECURITY_HEADERS.items()
    ):
        assert (
            response.headers[header_name]
            == expected_value
        )