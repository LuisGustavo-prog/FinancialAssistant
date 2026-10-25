import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.messages import error_message
from app.errors import AppError

logger = logging.getLogger("app")

STATUS_BY_CODE = {
    "value_decreased": 409,
    "month_closed": 422,
    "future_date": 422,
    "payment_exceeds_reported_value": 422,
    "leftover_income_locked": 409,
    "leftover_not_pending": 409,
    "no_open_month": 409,
    "name_already_exists": 409,
    "default_category_locked": 409,
    "category_inactive": 422,
    "not_found": 404,
}

def error_response(status_code: int, code: str, params: dict | None = None) -> JSONResponse:
    params = params or {}
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": error_message(code, params), "params": params},
    )

async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(STATUS_BY_CODE.get(exc.code, 400), exc.code, exc.params)

async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = []
    for error in exc.errors():
        location = [str(part) for part in error["loc"]]
        name = ".".join(location[1:]) if len(location) > 1 else location[0]
        message = error["msg"].removeprefix("Value error, ")
        fields.append({"field": name, "message": message})
    return error_response(422, "validation_error", {"fields": fields})

async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return error_response(404, "not_found")
    if exc.status_code == 405:
        return error_response(405, "method_not_allowed")
    return error_response(exc.status_code, "internal_error")

async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path, exc_info=exc)
    response = error_response(500, "internal_error")
    origin = request.headers.get("origin")
    if origin and origin in getattr(request.app.state, "allowed_origins", ()):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response

def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
