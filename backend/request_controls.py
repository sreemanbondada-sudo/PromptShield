from fastapi.responses import JSONResponse


MAXIMUM_REQUEST_BODY_BYTES = 16 * 1024

BODY_METHODS = {
    "POST",
    "PUT",
    "PATCH",
}


class RequestSizeLimitMiddleware:
    """Reject oversized request bodies before processing."""

    def __init__(
        self,
        app,
        maximum_body_bytes: int = (
            MAXIMUM_REQUEST_BODY_BYTES
        ),
    ):
        self.app = app
        self.maximum_body_bytes = maximum_body_bytes

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        if (
            scope["type"] != "http"
            or scope["method"] not in BODY_METHODS
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))

        content_length = headers.get(
            b"content-length"
        )

        if content_length is not None:
            try:
                declared_size = int(content_length)

            except ValueError:
                declared_size = 0

            if declared_size > self.maximum_body_bytes:
                await self._send_too_large(
                    scope,
                    receive,
                    send,
                )
                return

        received_messages = []
        total_size = 0
        more_body = True

        while more_body:
            message = await receive()
            received_messages.append(message)

            if message["type"] == "http.request":
                total_size += len(
                    message.get("body", b"")
                )

                more_body = message.get(
                    "more_body",
                    False,
                )

                if total_size > self.maximum_body_bytes:
                    await self._send_too_large(
                        scope,
                        receive,
                        send,
                    )
                    return

            else:
                more_body = False

        message_index = 0

        async def replay_receive():
            nonlocal message_index

            if message_index < len(received_messages):
                message = received_messages[
                    message_index
                ]

                message_index += 1
                return message

            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }

        await self.app(
            scope,
            replay_receive,
            send,
        )

    async def _send_too_large(
        self,
        scope,
        receive,
        send,
    ):
        response = JSONResponse(
            status_code=413,
            content={
                "error": "request_too_large",
                "message": (
                    "The request body exceeds the "
                    "maximum permitted size."
                ),
            },
        )

        await response(scope, receive, send)