"""Safe structured logging configuration for the backend."""

import json
import logging
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

LOG_FORMAT_JSON = "json"
LOG_FORMAT_TEXT = "text"
REDACTED = "[REDACTED]"

SAFE_EXTRA_FIELDS = frozenset(
    {
        "app_domain",
        "app_env",
        "app_version",
        "duration_ms",
        "event",
        "http_method",
        "http_path",
        "status_code",
    },
)

SENSITIVE_NAME_PARTS = (
    "authorization",
    "apikey",
    "connectionstring",
    "databaseurl",
    "dsn",
    "hashedpassword",
    "jwt",
    "password",
    "redisurl",
    "secret",
    "sessionid",
    "token",
)

_LOG_LEVELS: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "FATAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

_BEARER_TOKEN_PATTERN = re.compile(
    r"\bBearer\s+[A-Za-z0-9._~+/\-=]+",
    flags=re.IGNORECASE,
)
_AUTHORIZATION_PATTERN = re.compile(
    r"\b(?P<key>authorization)\b"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?:Bearer\s+)?[A-Za-z0-9._~+/\-=]+",
    flags=re.IGNORECASE,
)
_SENSITIVE_KEY_VALUE_PATTERN = re.compile(
    r"\b(?P<key>[A-Za-z0-9_-]*(?:password|passwd|pwd|secret|token|jwt|authorization|"
    r"api[_-]?key|session[_-]?id|hashed_password|database[_-]?url|redis[_-]?url|"
    r"connection[_-]?string|dsn)[A-Za-z0-9_-]*)\b"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^,\s&;]+)",
    flags=re.IGNORECASE,
)


def configure_logging(*, log_level: str, log_format: str) -> None:
    """Configure process logging with safe defaults."""

    level = resolve_log_level(log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_formatter_for(log_format))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for logger_name in ("retines", "uvicorn", "uvicorn.error"):
        configured_logger = logging.getLogger(logger_name)
        configured_logger.handlers.clear()
        configured_logger.setLevel(level)
        configured_logger.propagate = True

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.setLevel(logging.WARNING)
    access_logger.propagate = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a project logger under the retines namespace."""

    if name is None or name == "":
        return logging.getLogger("retines")
    if name == "retines" or name.startswith("retines."):
        return logging.getLogger(name)
    return logging.getLogger(f"retines.{name}")


def resolve_log_level(log_level: str) -> int:
    """Resolve LOG_LEVEL values with the previous INFO fallback behavior."""

    return _LOG_LEVELS.get(log_level.upper(), logging.INFO)


def redact_sensitive_data(value: object) -> object:
    """Redact common secret patterns from log output."""

    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _is_sensitive_name(str(key)) else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray | str):
        return [redact_sensitive_data(item) for item in value]
    return value


class JsonLogFormatter(logging.Formatter):
    """Format log records as compact JSON with allowlisted structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": _utc_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": str(redact_sensitive_data(record.getMessage())),
        }

        for field_name in sorted(SAFE_EXTRA_FIELDS):
            if field_name not in record.__dict__:
                continue
            field_value = record.__dict__[field_name]
            if field_value is None:
                continue
            payload[field_name] = _json_safe_value(redact_sensitive_data(field_value))

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class RedactingTextFormatter(logging.Formatter):
    """Apply the same redaction policy to text logs used in local development."""

    def format(self, record: logging.LogRecord) -> str:
        return str(redact_sensitive_data(super().format(record)))


def _formatter_for(log_format: str) -> logging.Formatter:
    if log_format.lower() == LOG_FORMAT_TEXT:
        return RedactingTextFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
    return JsonLogFormatter()


def _utc_timestamp(created: float) -> str:
    return datetime.fromtimestamp(created, tz=UTC).isoformat().replace("+00:00", "Z")


def _redact_text(value: str) -> str:
    value = _AUTHORIZATION_PATTERN.sub(
        lambda match: f"{match.group('key')}{match.group('separator')}{REDACTED}",
        value,
    )
    value = _BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED]", value)
    return _SENSITIVE_KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group('key')}{match.group('separator')}{REDACTED}",
        value,
    )


def _is_sensitive_name(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return any(part in normalized for part in SENSITIVE_NAME_PARTS)


def _json_safe_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray | str):
        return [_json_safe_value(item) for item in value]
    return str(value)
