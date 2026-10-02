import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from rate_limiter import (
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
)


def test_requests_within_limit_are_allowed():
    limiter = SlidingWindowRateLimiter(
        maximum_requests=3,
        window_seconds=60,
    )

    first_allowed, _ = limiter.check_request(
        "client-1",
        current_time=100.0,
    )

    second_allowed, _ = limiter.check_request(
        "client-1",
        current_time=101.0,
    )

    third_allowed, _ = limiter.check_request(
        "client-1",
        current_time=102.0,
    )

    assert first_allowed is True
    assert second_allowed is True
    assert third_allowed is True


def test_request_above_limit_is_rejected():
    limiter = SlidingWindowRateLimiter(
        maximum_requests=2,
        window_seconds=60,
    )

    limiter.check_request(
        "client-1",
        current_time=100.0,
    )

    limiter.check_request(
        "client-1",
        current_time=101.0,
    )

    allowed, retry_after = limiter.check_request(
        "client-1",
        current_time=102.0,
    )

    assert allowed is False
    assert retry_after > 0


def test_client_is_allowed_after_window_expires():
    limiter = SlidingWindowRateLimiter(
        maximum_requests=1,
        window_seconds=60,
    )

    limiter.check_request(
        "client-1",
        current_time=100.0,
    )

    allowed, retry_after = limiter.check_request(
        "client-1",
        current_time=161.0,
    )

    assert allowed is True
    assert retry_after == 0


def test_clients_have_separate_limits():
    limiter = SlidingWindowRateLimiter(
        maximum_requests=1,
        window_seconds=60,
    )

    limiter.check_request(
        "client-1",
        current_time=100.0,
    )

    first_client_allowed, _ = limiter.check_request(
        "client-1",
        current_time=101.0,
    )

    second_client_allowed, _ = limiter.check_request(
        "client-2",
        current_time=101.0,
    )

    assert first_client_allowed is False
    assert second_client_allowed is True


def test_invalid_maximum_requests_is_rejected():
    with pytest.raises(
        ValueError,
        match="maximum_requests",
    ):
        SlidingWindowRateLimiter(
            maximum_requests=0,
            window_seconds=60,
        )


def test_invalid_window_is_rejected():
    with pytest.raises(
        ValueError,
        match="window_seconds",
    ):
        SlidingWindowRateLimiter(
            maximum_requests=10,
            window_seconds=0,
        )

def create_rate_limited_test_client():
    test_app = FastAPI()

    test_app.add_middleware(
        RateLimitMiddleware,
        maximum_requests=2,
        window_seconds=60,
    )

    @test_app.post("/analyze")
    def test_analyze_endpoint():
        return {
            "status": "accepted",
        }

    @test_app.get("/health")
    def test_health_endpoint():
        return {
            "status": "healthy",
        }

    return TestClient(test_app)


def test_rate_limited_endpoint_returns_429():
    test_client = create_rate_limited_test_client()

    first_response = test_client.post("/analyze")
    second_response = test_client.post("/analyze")
    third_response = test_client.post("/analyze")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 429

    assert third_response.json() == {
        "error": "rate_limit_exceeded",
        "message": (
            "Too many analysis requests. "
            "Please try again later."
        ),
    }

    assert int(
        third_response.headers["Retry-After"]
    ) > 0


def test_unprotected_endpoint_is_not_rate_limited():
    test_client = create_rate_limited_test_client()

    for _ in range(5):
        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
        }