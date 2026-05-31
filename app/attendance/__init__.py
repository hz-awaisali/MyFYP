"""Attendance module (Phase 2 - scaffolded).

Planned: GPS / BLE / Hybrid validation engine, attendance sessions, records,
events, location logs, beacon logs and validation results, plus attendance
analytics and reports.

The validation layer is designed around a pluggable decision engine:

    class AttendanceValidator(Protocol):
        def validate(self, context) -> ValidationResult: ...

with GpsValidator, BleValidator and HybridValidator implementations and
configurable rules sourced from ``system_settings``.

TODO(phase-2): implement models, services, repositories and routers here.
"""
