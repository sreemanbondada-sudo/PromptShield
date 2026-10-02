import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from request_logging import (
    PrivacySafeRequestLoggingMiddleware,
)


def create_logging_test_client(
    raise_server_exceptions: bool = True,
):
    test_app = FastAPI()

    test_app.add_middleware(
        PrivacySafeRequestLoggingMiddleware
    )

    @test_app.post("/analyze")
    def analyze_endpoint():
        return {
            "status": "accepted",
        }

    @test_app.get("/failure")
    def failure_endpoint():
        raise RuntimeError(
            "PRIVATE-INTERNAL-ERROR-DATA"
        )

    return TestClient(
        test_app,
        raise_server_exceptions=(
            raise_server_exceptions
        ),
    )


def test_request_metadata_is_logged(
    caplog,
):
    test_client = create_logging_test_client()

    with caplog.at_level(
        logging.INFO,
        logger="promptshield.requests",
    ):
        response = test_client.post(
            "/analyze",
            json={
                "prompt": "PRIVATE-PROMPT-CONTENT",
            },
        )

    assert response.status_code == 200

    request_id = response.headers[
        "X-Request-ID"
    ]

    assert re.fullmatch(
        r"[0-9a-f]{32}",
        request_id,
    )

    log_output = caplog.text

    assert "request_completed" in log_output
    assert "method=POST" in log_output
    assert "path=/analyze" in log_output
    assert "status_code=200" in log_output
    assert request_id in log_output

    assert "PRIVATE-PROMPT-CONTENT" not in log_output


def test_internal_error_details_are_not_logged(
    caplog,
):
    test_client = create_logging_test_client(
        raise_server_exceptions=False,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="promptshield.requests",
    ):
        response = test_client.get("/failure")

    assert response.status_code == 500

    log_output = caplog.text

    assert "request_failed" in log_output
    assert "error_type=RuntimeError" in log_output
    assert (
        "PRIVATE-INTERNAL-ERROR-DATA"
        not in log_output
    )