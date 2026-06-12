import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_startup",
        extra={
            "event": "application_startup",
            "app_env": settings.APP_ENV,
            "app_version": settings.APP_VERSION,
            "app_domain": settings.APP_DOMAIN,
        },
    )
    yield
    logger.info("application_shutdown", extra={"event": "application_shutdown"})


app = FastAPI(
    title="Rétines & Pupilles API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "http_request",
        extra={
            "event": "http_request",
            "http_method": request.method,
            "http_path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(elapsed_ms, 1),
        },
    )
    return response


app.include_router(api_router)
