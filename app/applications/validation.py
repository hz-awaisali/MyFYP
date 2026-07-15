"""Server-side validation of submitted responses against dynamic field definitions."""

import re
from datetime import date
from typing import Any

from app.applications.models import ApplicationField
from app.common.enums import FieldType
from app.core.exceptions import ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


def evaluate_visibility(rule: dict | None, responses: dict[str, Any]) -> bool:
    """Evaluate if a field should be visible based on prior answers in ``responses``."""
    if not rule:
        return True
    field_key = rule.get("field")
    operator = rule.get("operator", "equals")
    rule_value = rule.get("value")

    if not field_key:
        return True

    actual_value = responses.get(field_key)

    # If the controlling field wasn't provided or is empty, we assume the target field is hidden
    if actual_value is None or actual_value == "":
        return False

    if operator in ("equals", "eq"):
        return str(actual_value) == str(rule_value)
    elif operator in ("not_equals", "ne"):
        return str(actual_value) != str(rule_value)
    elif operator in ("contains",):
        return str(rule_value) in str(actual_value)
    elif operator in ("greater_than", "gt"):
        try:
            return float(actual_value) > float(rule_value)
        except (ValueError, TypeError):
            return False
    elif operator in ("less_than", "lt"):
        try:
            return float(actual_value) < float(rule_value)
        except (ValueError, TypeError):
            return False

    return True


def validate_responses(
    fields: list[ApplicationField], responses: dict[str, Any]
) -> dict[str, str | None]:
    """Validate ``responses`` (keyed by field key) against ``fields``.

    Returns a normalized mapping of field_key -> stringified value to persist.
    Raises ``ValidationError`` on the first problem.
    """
    errors: list[str] = []
    normalized: dict[str, str | None] = {}
    valid_keys = {f.key for f in fields}

    unknown = set(responses) - valid_keys
    if unknown:
        raise ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")

    # Sort fields to ensure sequential dependencies are evaluated in display order
    sorted_fields = sorted(fields, key=lambda f: f.display_order)

    for field in sorted_fields:
        visible = evaluate_visibility(field.visibility_rule, normalized)
        if not visible:
            normalized[field.key] = None
            continue

        raw = responses.get(field.key, None)
        provided = raw is not None and raw != ""

        if field.is_required and not provided:
            errors.append(f"'{field.label}' is required")
            continue
        if not provided:
            normalized[field.key] = field.default_value
            continue

        try:
            normalized[field.key] = _validate_one(field, raw)
        except ValueError as exc:
            errors.append(f"'{field.label}': {exc}")

    if errors:
        raise ValidationError("; ".join(errors))
    return normalized


def _validate_one(field: ApplicationField, value: Any) -> str:
    ft = field.field_type
    rules = field.validation or {}

    if ft == FieldType.NUMBER:
        try:
            num = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("must be a number") from exc
        if "min" in rules and num < rules["min"]:
            raise ValueError(f"must be >= {rules['min']}")
        if "max" in rules and num > rules["max"]:
            raise ValueError(f"must be <= {rules['max']}")
        return str(value)

    if ft == FieldType.DATE:
        try:
            date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError("must be an ISO date (YYYY-MM-DD)") from exc
        return str(value)

    if ft == FieldType.EMAIL:
        if not _EMAIL_RE.match(str(value)):
            raise ValueError("must be a valid email")
        return str(value)

    if ft == FieldType.PHONE:
        if not _PHONE_RE.match(str(value)):
            raise ValueError("must be a valid phone number")
        return str(value)

    if ft in (FieldType.DROPDOWN, FieldType.RADIO):
        options = field.options or []
        if str(value) not in [str(o) for o in options]:
            raise ValueError(f"must be one of {options}")
        return str(value)

    if ft == FieldType.CHECKBOX:
        options = field.options or []
        selected = value if isinstance(value, list) else [value]
        allowed = {str(o) for o in options}
        for item in selected:
            if str(item) not in allowed:
                raise ValueError(f"contains an invalid option: {item}")
        return ",".join(str(s) for s in selected)

    # TEXT, TEXTAREA, FILE (file references handled via attachments)
    text = str(value)
    if "min_length" in rules and len(text) < rules["min_length"]:
        raise ValueError(f"must be at least {rules['min_length']} characters")
    if "max_length" in rules and len(text) > rules["max_length"]:
        raise ValueError(f"must be at most {rules['max_length']} characters")
    if "pattern" in rules and not re.match(rules["pattern"], text):
        raise ValueError("has an invalid format")
    return text
