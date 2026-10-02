import logging
import time
import uuid


logger = logging.getLogger("promptshield.requests")


class PrivacySafeRequestLoggingMiddleware:
    """Log request metadata without logging private content."""

    def __init__(self, app):
        self.app = app

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        status_code = 500
        started_at = time.perf_counter()

        async def send_with_request_id(message):
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

                headers = list(
                    message.get("headers", [])
                )

                headers.append(
                    (
                        b"x-request-id",
                        request_id.encode("ascii"),
                    )
                )

                message["headers"] = headers

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )

        except Exception as error:
            duration_ms = (
                time.perf_counter() - started_at
            ) * 1000

            logger.error(
                (
                    "request_failed request_id=%s "
                    "method=%s path=%s "
                    "status_code=500 duration_ms=%.2f "
                    "error_type=%s"
                ),
                request_id,
                method,
                path,
                duration_ms,
                type(error).__name__,
            )

            raise

        duration_ms = (
            time.perf_counter() - started_at
        ) * 1000

        logger.info(
            (
                "request_completed request_id=%s "
                "method=%s path=%s "
                "status_code=%s duration_ms=%.2f"
            ),
            request_id,
            method,
            path,
            status_code,
            duration_ms,
        )