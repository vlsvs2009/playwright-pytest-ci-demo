"""JSON Schemas for API contract checks (Draft 2020-12)."""

from typing import Any

from jsonschema import Draft202012Validator

ISO_DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"

ORDER = {
    "type": "object",
    "required": ["id", "customer", "service", "price", "status", "created_at"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "customer": {"type": "string", "minLength": 2, "maxLength": 80},
        "service": {"type": "string", "minLength": 2, "maxLength": 120},
        "price": {"type": "number", "exclusiveMinimum": 0},
        "status": {"enum": ["new", "in_progress", "done"]},
        "created_at": {"type": "string", "pattern": ISO_DATETIME},
    },
}

ORDER_LIST = {
    "type": "object",
    "required": ["items", "count"],
    "additionalProperties": False,
    "properties": {
        "items": {"type": "array", "items": ORDER},
        "count": {"type": "integer", "minimum": 0},
    },
}

TOKEN = {
    "type": "object",
    "required": ["access_token", "token_type"],
    "additionalProperties": False,
    "properties": {
        "access_token": {"type": "string", "minLength": 20},
        "token_type": {"const": "bearer"},
    },
}

ERROR = {
    "type": "object",
    "required": ["detail"],
    "properties": {"detail": {"type": "string", "minLength": 1}},
}

VALIDATION_ERROR = {
    "type": "object",
    "required": ["detail"],
    "properties": {
        "detail": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["loc", "msg", "type"],
                "properties": {
                    "loc": {"type": "array", "items": {"type": ["string", "integer"]}},
                    "msg": {"type": "string"},
                    "type": {"type": "string"},
                },
            },
        }
    },
}


def assert_schema(instance: Any, schema: dict) -> None:
    """Assert `instance` matches `schema`, listing every violation in the failure message."""
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(f"  at {list(e.path) or '<root>'}: {e.message}" for e in errors)
        raise AssertionError(f"Response does not match schema:\n{details}")
