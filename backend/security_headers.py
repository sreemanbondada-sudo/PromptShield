SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=()"
    ),
}


class SecurityHeadersMiddleware:
    """Add defensive HTTP headers to every response."""

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

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = list(
                    message.get("headers", [])
                )

                existing_header_names = {
                    name.lower()
                    for name, _ in headers
                }

                for name, value in SECURITY_HEADERS.items():
                    encoded_name = name.lower().encode(
                        "latin-1"
                    )

                    if encoded_name not in existing_header_names:
                        headers.append(
                            (
                                encoded_name,
                                value.encode("latin-1"),
                            )
                        )

                message["headers"] = headers

            await send(message)

        await self.app(
            scope,
            receive,
            send_with_security_headers,
        )