"""rizChartFunction 的公开异常类。"""

from __future__ import annotations

__all__ = [
    "RizChartError",
    "RizChartArgumentError",
    "RizChartTypeError",
    "RizChartValueError",
    "RizChartIndexError",
    "RizChartRangeError",
    "RizChartStructureError",
    "RizChartReferenceError",
    "RizChartTimeError",
    "RizChartBpmError",
    "RizChartCanvasError",
    "RizChartEaseError",
    "RizChartColorError",
    "RizChartColorMismatchError",
    "RizChartThemeError",
    "RizChartFloorPositionError",
    "RizChartMathError",
    "RizChartDivisionByZeroError",
    "RizChartBatchError",
    "RizChartIOError",
    "RizChartLoadError",
    "RizChartExportError",
    "RizChartValidationError",
    "RizChartTransactionError",
    "RizChartDrawingError",
    "RizChartGeometryError",
    "RizChartFontError",
    "RizChartTextLayoutError",
    "RizChartNoEffectError",
]


class RizChartError(Exception):
    """所有 rizChartFunction 异常的基类。"""

    code = "RCF"

    def __init__(
        self,
        message: str,
        *,
        function: str | None = None,
        context: dict | None = None,
        cause: BaseException | None = None,
        **details,
    ) -> None:
        super().__init__(message)
        self.function = function
        self.context = dict(context or {})
        self.cause = cause
        for name, value in details.items():
            setattr(self, name, value)

    def __str__(self) -> str:
        message = super().__str__()
        if self.function:
            return f"{self.function}: {message}"
        return message


class RizChartArgumentError(RizChartError):
    code = "RCF-ARG"


class RizChartTypeError(RizChartArgumentError):
    code = "RCF-TYPE"


class RizChartValueError(RizChartArgumentError):
    code = "RCF-VALUE"


class RizChartIndexError(RizChartArgumentError):
    code = "RCF-INDEX"


class RizChartRangeError(RizChartArgumentError):
    code = "RCF-RANGE"


class RizChartStructureError(RizChartError):
    code = "RCF-STRUCTURE"


class RizChartReferenceError(RizChartError):
    code = "RCF-REFERENCE"


class RizChartTimeError(RizChartError):
    code = "RCF-TIME"


class RizChartBpmError(RizChartError):
    code = "RCF-BPM"


class RizChartCanvasError(RizChartError):
    code = "RCF-CANVAS"


class RizChartEaseError(RizChartError):
    code = "RCF-EASE"


class RizChartColorError(RizChartError):
    code = "RCF-COLOR"


class RizChartColorMismatchError(RizChartColorError):
    code = "RCF-COLOR-MISMATCH"


class RizChartThemeError(RizChartError):
    code = "RCF-THEME"


class RizChartFloorPositionError(RizChartError):
    code = "RCF-FLOOR"


class RizChartMathError(RizChartError):
    code = "RCF-MATH"


class RizChartDivisionByZeroError(RizChartMathError):
    code = "RCF-DIV-ZERO"


class RizChartBatchError(RizChartError):
    code = "RCF-BATCH"


class RizChartIOError(RizChartError):
    code = "RCF-IO"


class RizChartLoadError(RizChartIOError):
    code = "RCF-LOAD"


class RizChartExportError(RizChartIOError):
    code = "RCF-EXPORT"


class RizChartValidationError(RizChartError):
    code = "RCF-VALIDATION"


class RizChartTransactionError(RizChartError):
    code = "RCF-TRANSACTION"


class RizChartDrawingError(RizChartError):
    code = "RCF-DRAWING"


class RizChartGeometryError(RizChartDrawingError):
    code = "RCF-GEOMETRY"


class RizChartFontError(RizChartDrawingError):
    code = "RCF-FONT"


class RizChartTextLayoutError(RizChartDrawingError):
    code = "RCF-TEXT-LAYOUT"


class RizChartNoEffectError(RizChartError):
    code = "RCF-NO-EFFECT"
