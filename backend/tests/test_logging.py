"""Tests for backend structured logging."""

import json
import logging
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.logging import JsonLogFormatter, resolve_log_level
from app.main import app


def test_json_formatter_emits_allowlisted_structured_fields() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="retines.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(
        {
            "event": "http_request",
            "http_method": "GET",
            "http_path": "/api/v1/patients",
            "status_code": 200,
            "duration_ms": 12.3,
            "email": "patient@example.com",
        },
    )

    payload = cast(dict[str, Any], json.loads(formatter.format(record)))

    assert payload["event"] == "http_request"
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/api/v1/patients"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.3
    assert "email" not in payload
    assert "patient@example.com" not in json.dumps(payload)


def test_json_formatter_redacts_common_secret_patterns() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="retines.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=(
            "login failed password=s3cr3t token=abc123 "
            "DATABASE_URL=postgresql://user:dbpass@localhost/db "
            "Authorization: Bearer header.payload"
        ),
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    payload = cast(dict[str, Any], json.loads(formatted))

    assert payload["message"] == (
        "login failed password=[REDACTED] token=[REDACTED] "
        "DATABASE_URL=[REDACTED] Authorization: [REDACTED]"
    )
    assert "s3cr3t" not in formatted
    assert "abc123" not in formatted
    assert "dbpass" not in formatted
    assert "header.payload" not in formatted


@pytest.mark.parametrize(
    ("log_level", "expected"),
    [
        ("DEBUG", logging.DEBUG),
        ("info", logging.INFO),
        ("WARNING", logging.WARNING),
        ("invalid", logging.INFO),
    ],
)
def test_resolve_log_level_keeps_existing_fallback_behavior(
    log_level: str,
    expected: int,
) -> None:
    assert resolve_log_level(log_level) == expected


@pytest.mark.asyncio
async def test_request_logging_uses_safe_structured_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="retines")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health?search=Jeanne&token=s3cr3t")

    records = [
        record for record in caplog.records if record.__dict__.get("event") == "http_request"
    ]

    assert response.status_code == 200
    assert records

    request_record = records[-1]
    request_values = request_record.__dict__
    assert request_record.getMessage() == "http_request"
    assert request_values["http_method"] == "GET"
    assert request_values["http_path"] == "/api/v1/health"
    assert request_values["status_code"] == 200
    assert "Jeanne" not in request_record.getMessage()
    assert "s3cr3t" not in request_record.getMessage()
