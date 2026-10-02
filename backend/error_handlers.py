from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import (
    HTTPException as StarletteHTTPException,
)


def register_error_handlers(app: FastAPI) -> None:
    """Register consistent and privacy-safe API errors."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ):
        safe_details = []

        for validation_error in error.errors():
            location = ".".join(
                str(part)
                for part in validation_error["loc"]
            )

            safe_details.append(
                {
                    "location": location,
                    "message": validation_error["msg"],
                    "type": validation_error["type"],
                }
            )

        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": (
                    "The request failed validation."
                ),
                "details": safe_details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        error: StarletteHTTPException,
    ):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": "http_error",
                "message": str(error.detail),
            },
            headers=error.headers,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        error: Exception,
    ):
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": (
                    "An unexpected server error occurred."
                ),
            },
        )