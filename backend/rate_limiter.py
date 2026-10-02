import time
from collections import defaultdict, deque
from threading import Lock

from fastapi.responses import JSONResponse


RATE_LIMITED_PATHS = {
    "/analyze",
    "/ml/analyze",
}


class SlidingWindowRateLimiter:
    """Track requests using an in-memory sliding time window."""

    def __init__(
        self,
        maximum_requests: int = 10,
        window_seconds: int = 60,
    ):
        if maximum_requests < 1:
            raise ValueError(
                "maximum_requests must be at least 1."
            )

        if window_seconds < 1:
            raise ValueError(
                "window_seconds must be at least 1."
            )

        self.maximum_requests = maximum_requests
        self.window_seconds = window_seconds
        self.request_times = defaultdict(deque)
        self.lock = Lock()

    def check_request(
        self,
        client_identifier: str,
        current_time: float | None = None,
    ) -> tuple[bool, int]:
        """
        Check whether a request is allowed.

        Return whether it is allowed and the retry delay.
        """
        now = (
            current_time
            if current_time is not None
            else time.monotonic()
        )

        window_start = now - self.window_seconds

        with self.lock:
            timestamps = self.request_times[
                client_identifier
            ]

            while (
                timestamps
                and timestamps[0] <= window_start
            ):
                timestamps.popleft()

            if len(timestamps) >= self.maximum_requests:
                retry_after = max(
                    1,
                    int(
                        self.window_seconds
                        - (now - timestamps[0])
                    )
                    + 1,
                )

                return False, retry_after

            timestamps.append(now)

            return True, 0


class RateLimitMiddleware:
    """Limit requests to expensive PromptShield endpoints."""

    def __init__(
        self,
        app,
        maximum_requests: int = 10,
        window_seconds: int = 60,
    ):
        self.app = app

        self.rate_limiter = SlidingWindowRateLimiter(
            maximum_requests=maximum_requests,
            window_seconds=window_seconds,
        )

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] not in RATE_LIMITED_PATHS
        ):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")

        if client:
            client_identifier = client[0]
        else:
            client_identifier = "unknown"

        allowed, retry_after = (
            self.rate_limiter.check_request(
                client_identifier
            )
        )

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": (
                        "Too many analysis requests. "
                        "Please try again later."
                    ),
                },
                headers={
                    "Retry-After": str(retry_after),
                },
            )

            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)