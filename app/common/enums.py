"""Shared enums used across modules."""

import enum


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class RoleName(str, enum.Enum):
    STUDENT = "student"
    HOD = "hod"
    HOD_ASSISTANT = "hod_assistant"
    EXAMINATION_OFFICER = "examination_officer"
    REGISTRAR_OFFICER = "registrar_officer"
    IT_OFFICER = "it_officer"
    TRANSPORT_OFFICER = "transport_officer"
    TREASURER_OFFICER = "treasurer_officer"
    SUPER_ADMIN = "super_admin"


class FieldType(str, enum.Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    DROPDOWN = "dropdown"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    EMAIL = "email"
    PHONE = "phone"


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RETURNED = "returned"
    REJECTED = "rejected"
    APPROVED = "approved"
    FORWARDED = "forwarded"
    COMPLETED = "completed"
    CLOSED = "closed"


class WorkflowActionType(str, enum.Enum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    FORWARD = "forward"
    RETURN_FOR_CORRECTION = "return_for_correction"
    ADD_REMARKS = "add_remarks"
    CLOSE = "close"
    REOPEN = "reopen"


class NotificationType(str, enum.Enum):
    APPLICATION_SUBMITTED = "application_submitted"
    APPLICATION_APPROVED = "application_approved"
    APPLICATION_REJECTED = "application_rejected"
    APPLICATION_RETURNED = "application_returned"
    APPLICATION_FORWARDED = "application_forwarded"
    NEW_REMARK = "new_remark"
    ATTENDANCE_MARKED = "attendance_marked"
    ACCOUNT_APPROVED = "account_approved"
    SYSTEM = "system"
