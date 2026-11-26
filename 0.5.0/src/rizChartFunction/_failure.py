"""Internal failure records used by ``isReturnException`` messages."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

_UNSET = object()

__all__ = [
    "FailureContext",
    "FailureRecord",
    "capture_failure",
    "fail",
    "last_failure",
]


@dataclass
class FailureRecord:
    """One detailed failure reason recorded inside the current call."""

    message: str
    code: str | None = None
    parameter: str | None = None
    actual: object = _UNSET
    expected: str | None = None
    path: object = None
    index: int | None = None
    length: int | None = None
    cause: BaseException | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def fields(self) -> dict[str, Any]:
        result = dict(self.details)
        if self.code is not None:
            result["reason_code"] = self.code
        if self.parameter is not None:
            result["parameter"] = self.parameter
        if self.actual is not _UNSET:
            result["actual"] = self.actual
            result["value"] = self.actual
        if self.expected is not None:
            result["expected"] = self.expected
            result["allowed"] = self.expected
        if self.path is not None:
            result["path"] = self.path
        if self.index is not None:
            result["index"] = self.index
        if self.length is not None:
            result["length"] = self.length
        if self.cause is not None:
            result["cause"] = self.cause
        return result


@dataclass
class FailureContext:
    """Failure records collected during one top-level exception call."""

    function: str
    records: list[FailureRecord] = field(default_factory=list)

    def add(self, record: FailureRecord) -> None:
        self.records.append(record)

    @property
    def last(self) -> FailureRecord | None:
        return self.records[-1] if self.records else None


_CURRENT: ContextVar[FailureContext | None] = ContextVar(
    "rizchart_failure_context",
    default=None,
)


def fail(
    value: Any,
    message: str,
    *,
    code: str | None = None,
    parameter: str | None = None,
    actual: object = _UNSET,
    expected: str | None = None,
    path: object = None,
    index: int | None = None,
    length: int | None = None,
    cause: BaseException | None = None,
    **details: Any,
) -> Any:
    """Record a failure reason when exception reporting is active.

    The original failure value is returned unchanged. Outside an active
    ``isReturnException=True`` call this is a cheap no-op, so default return
    behavior remains untouched.
    """
    context = _CURRENT.get()
    if context is not None:
        context.add(
            FailureRecord(
                message=message,
                code=code,
                parameter=parameter,
                actual=actual,
                expected=expected,
                path=path,
                index=index,
                length=length,
                cause=cause,
                details=details,
            )
        )
    return value


@contextmanager
def capture_failure(function: str) -> Iterator[FailureContext]:
    """Capture detailed failures for one public function call."""
    context = FailureContext(function)
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)


def last_failure() -> FailureRecord | None:
    """Return the most recent failure in the active context, if any."""
    context = _CURRENT.get()
    return None if context is None else context.last
