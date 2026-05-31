"""Dynamic form validation unit tests."""

import uuid

import pytest

from app.applications.models import ApplicationField
from app.applications.validation import validate_responses
from app.common.enums import FieldType
from app.core.exceptions import ValidationError


def _field(key, ftype, **kwargs) -> ApplicationField:
    return ApplicationField(
        id=uuid.uuid4(),
        form_id=uuid.uuid4(),
        key=key,
        label=key.title(),
        field_type=ftype,
        is_required=kwargs.get("is_required", False),
        default_value=kwargs.get("default_value"),
        validation=kwargs.get("validation"),
        options=kwargs.get("options"),
        display_order=0,
    )


def test_required_field_missing_raises():
    fields = [_field("reason", FieldType.TEXT, is_required=True)]
    with pytest.raises(ValidationError):
        validate_responses(fields, {})


def test_number_range_enforced():
    fields = [_field("copies", FieldType.NUMBER, validation={"min": 1, "max": 5})]
    with pytest.raises(ValidationError):
        validate_responses(fields, {"copies": 10})
    ok = validate_responses(fields, {"copies": 3})
    assert ok["copies"] == "3"


def test_dropdown_option_validated():
    fields = [_field("delivery", FieldType.DROPDOWN, options=["Email", "Postal"])]
    with pytest.raises(ValidationError):
        validate_responses(fields, {"delivery": "Carrier Pigeon"})
    ok = validate_responses(fields, {"delivery": "Email"})
    assert ok["delivery"] == "Email"


def test_email_validation():
    fields = [_field("contact", FieldType.EMAIL)]
    with pytest.raises(ValidationError):
        validate_responses(fields, {"contact": "not-an-email"})
    ok = validate_responses(fields, {"contact": "a@b.com"})
    assert ok["contact"] == "a@b.com"


def test_unknown_field_rejected():
    fields = [_field("reason", FieldType.TEXT)]
    with pytest.raises(ValidationError):
        validate_responses(fields, {"unexpected": "x"})


def test_default_value_applied_when_absent():
    fields = [_field("note", FieldType.TEXT, default_value="n/a")]
    result = validate_responses(fields, {})
    assert result["note"] == "n/a"
