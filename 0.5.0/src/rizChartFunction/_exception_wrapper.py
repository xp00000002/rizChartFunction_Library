"""公开函数的 isReturnException 统一包装层。"""

from __future__ import annotations

import functools
import inspect
import math
from contextvars import ContextVar
from pathlib import Path

from ._config import get_default_return_exception
from ._failure import FailureContext, capture_failure
from ._i18n import (
    register_doc_namespace,
    translate_expected,
    translate_failure,
    translate_message,
)
from ._internal import _parse_color
from .exceptions import (
    RizChartArgumentError,
    RizChartBatchError,
    RizChartBpmError,
    RizChartCanvasError,
    RizChartColorError,
    RizChartColorMismatchError,
    RizChartDivisionByZeroError,
    RizChartDrawingError,
    RizChartEaseError,
    RizChartError,
    RizChartExportError,
    RizChartFloorPositionError,
    RizChartFontError,
    RizChartGeometryError,
    RizChartIndexError,
    RizChartLoadError,
    RizChartRangeError,
    RizChartStructureError,
    RizChartTextLayoutError,
    RizChartThemeError,
    RizChartTimeError,
    RizChartTransactionError,
    RizChartTypeError,
    RizChartValidationError,
    RizChartValueError,
)

_NO_FAILURE = {"new", "rgb", "rgba", "getRingRadius"}
_WRAPPER_DEPTH: ContextVar[int] = ContextVar(
    "rizchart_exception_wrapper_depth",
    default=0,
)
_BATCH_NAMES = {
    "addLineByDict",
    "addLinePointByDict",
    "addRingPointByDict",
    "addNoteByDict",
    "addLineColorByDict",
    "addRiztimeByDict",
    "addBpmByDict",
    "addCanvasByDict",
    "addCanvasPositionByDict",
    "addCanvasSpeedByDict",
    "addCameraPositionByDict",
    "addCameraScaleByDict",
    "copyLine",
    "copyLinePoint",
    "copyRingPoint",
    "copyNote",
    "copyLineColor",
    "copyBpmShift",
    "copyRiztime",
    "copyCanvas",
    "copyCanvasPosition",
    "copyCanvasSpeed",
    "copyCamera",
    "copyCameraPosition",
    "copyCameraScale",
    "setBpmShiftEase",
    "setLinePointPositionEase",
    "setLinePointColorEase",
    "setRingColorEase",
    "setLineColorEase",
    "setCanvasPositionEase",
    "setCanvasSpeedEase",
    "setCameraPositionEase",
    "setCameraScaleEase",
}
_SPECIAL_DEFAULT = {
    "load": RizChartLoadError,
    "export": RizChartExportError,
    "check": RizChartValidationError,
    "refresh": RizChartStructureError,
    "mixColor": RizChartColorError,
    "splitColor": RizChartColorError,
    "setNormalTheme": RizChartThemeError,
    "setRiztime": RizChartThemeError,
    "addRiztime": RizChartThemeError,
    "deleteRiztime": RizChartThemeError,
    "setBaseBpm": RizChartBpmError,
    "addBpmShift": RizChartBpmError,
    "setBpmShift": RizChartBpmError,
    "deleteBpmShift": RizChartBpmError,
    "getBpmAt": RizChartBpmError,
    "getSecondsAt": RizChartBpmError,
    "getTickAt": RizChartBpmError,
    "getTheme": RizChartThemeError,
    "getThemeColor": RizChartThemeError,
    "getChallengeTime": RizChartThemeError,
    "getRiztime": RizChartThemeError,
    "getThemeByColor": RizChartThemeError,
    "getFloorPosition": RizChartFloorPositionError,
    "getCanvasSpeedAt": RizChartCanvasError,
    "getCanvasPositionAt": RizChartCanvasError,
    "getBaseColor": RizChartColorError,
    "getCoverColor": RizChartColorError,
    "getRingColor": RizChartColorError,
    "getMixColor": RizChartColorError,
    "getXYRatio": RizChartValueError,
    "getXYRatioByChart": RizChartValueError,
    "getXBorder": RizChartValueError,
    "getXBorderByChart": RizChartStructureError,
    "getYBorder": RizChartValueError,
    "getYBorderByChart": RizChartStructureError,
    "getGameScale": RizChartValueError,
    "getLineWidth": RizChartValueError,
    "getShadeOpacity": RizChartValueError,
    "addIsolatedNote": RizChartStructureError,
    "transColor": RizChartColorError,
    "setLinePointColorByList": RizChartColorError,
    "getClosedRegion": RizChartGeometryError,
    "drawPolygon": RizChartGeometryError,
    "drawEllipse": RizChartGeometryError,
    "xMirrorLine": RizChartGeometryError,
    "drawText": RizChartDrawingError,
    "drawThinText": RizChartDrawingError,
}
_TIME_KEYS = {
    "time",
    "starttime",
    "endtime",
    "currenttime",
    "querytime",
    "tick",
    "seconds",
    "start",
    "end",
    "transtime",
}
_COLOR_KEYS = {
    "color",
    "startcolor",
    "endcolor",
    "bordercolor",
    "backgroundcolor",
    "holecolor",
    "color1",
    "color2",
    "color3",
}
_COLOR_LIST_KEYS = {"origioncolorlist", "targetcolorlist"}
_EASE_KEYS = {"easetype"}


def install_exception_api(namespace: dict) -> None:
    """把公开函数替换为支持 ``isReturnException`` 的包装函数。"""
    for name in namespace.get("__all__", ()):
        function = namespace.get(name)
        if not inspect.isfunction(function):
            continue
        if name in _NO_FAILURE:
            continue
        if getattr(function, "__rizchart_exception_wrapped__", False):
            continue
        namespace[name] = _wrap(function)
    register_doc_namespace(namespace)


def _wrap(function):
    signature = inspect.signature(function)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        explicit = kwargs.pop("isReturnException", None)
        depth = _WRAPPER_DEPTH.get()
        if explicit is None:
            # The global switch applies to top-level user calls only. Nested
            # public calls from batch/copy/ease implementations keep the
            # historical non-raising default so the outer function can handle
            # failures and roll back normally.
            explicit = (
                get_default_return_exception()
                if depth == 0
                else False
            )
        if not isinstance(explicit, bool):
            raise RizChartTypeError(
                translate_message(
                    "argument.isReturnException",
                    actual=repr(explicit),
                ),
                function=function.__name__,
                context={"isReturnException": repr(explicit)},
            )

        token = _WRAPPER_DEPTH.set(depth + 1)
        try:
            if explicit and "isFailAddAllowed" in signature.parameters:
                try:
                    bound = signature.bind_partial(*args, **kwargs)
                except TypeError:
                    bound = None
                if bound is not None and "isFailAddAllowed" in bound.arguments:
                    bound.arguments["isFailAddAllowed"] = False
                    args = bound.args
                    kwargs = bound.kwargs

            failure_context = None
            if explicit:
                manager = capture_failure(function.__name__)
                failure_context = manager.__enter__()
                try:
                    result = function(*args, **kwargs)
                finally:
                    manager.__exit__(None, None, None)
            else:
                result = function(*args, **kwargs)
            if not explicit:
                return result

            kind = _failure_kind(function.__name__, result)
            if kind is None:
                return result

            try:
                bound = signature.bind_partial(*args, **kwargs)
                arguments = dict(bound.arguments)
            except TypeError:
                arguments = {}

            error = _make_error(
                function.__name__,
                kind,
                result,
                arguments,
                failure_context,
            )
            if error is None:
                return result
            raise error
        finally:
            _WRAPPER_DEPTH.reset(token)

    parameters = list(signature.parameters.values())
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    parameter = inspect.Parameter(
        "isReturnException",
        keyword_only,
        default=None,
        annotation=bool | None,
    )
    var_keyword_at = None
    for index, current in enumerate(parameters):
        if current.kind == inspect.Parameter.VAR_KEYWORD:
            var_keyword_at = index
            break
    if var_keyword_at is None:
        parameters.append(parameter)
    else:
        parameters.insert(var_keyword_at, parameter)
    wrapper.__signature__ = signature.replace(parameters=parameters)
    wrapper.__rizchart_exception_wrapped__ = True
    return wrapper


def _failure_kind(name: str, result: object) -> str | None:
    if name == "check":
        return "validation" if isinstance(result, dict) else None
    if name == "splitColor":
        if result is False:
            return "color_mismatch"
        if result is None:
            return "value"
        return None
    if name == "export":
        return "false" if result is False else None
    if name in ("getXYRatio", "getXYRatioByChart", "getYBorder", "getYBorderByChart"):
        if isinstance(result, float) and math.isnan(result):
            return "division"
        return "value" if result is None else None
    if name in _BATCH_NAMES:
        if isinstance(result, list) and result:
            return "batch"
        return "value" if result is None else None
    return "value" if result is None else None


def _make_error(
    name: str,
    kind: str,
    result: object,
    arguments: dict,
    failure_context: FailureContext | None = None,
) -> RizChartError | None:
    context = {
        key: _summarize(value)
        for key, value in arguments.items()
        if key not in {"chart"}
    }
    context["result"] = _summarize(result)

    failure = (
        failure_context.last
        if failure_context is not None
        else None
    )
    if failure is not None:
        return _make_detailed_error(
            name,
            kind,
            result,
            context,
            arguments,
            failure,
        )

    if kind == "validation":
        return RizChartValidationError(
            translate_message("validation.failed"),
            function=name,
            context=context,
            issues=result,
        )
    if kind == "division":
        return RizChartDivisionByZeroError(
            translate_message("math.division_by_zero"),
            function=name,
            context=context,
            numerator=context.get("value"),
            denominator=0.0,
            expression="value * 5.625 * bpm / (60 * canvasspeed * K)",
        )
    if kind == "color_mismatch":
        return RizChartColorMismatchError(
            translate_message("color.mismatch"),
            function=name,
            context=context,
            mixcolor=context.get("mixcolor"),
            basecolor=context.get("basecolor"),
            covercolor=context.get("covercolor"),
        )
    if kind == "false":
        if name == "export":
            return RizChartExportError(
                translate_message("export.failed"),
                function=name,
                context=context,
                filename=arguments.get("filename"),
                reason="chart validation, path or JSON serialization failed",
            )
        return _default_error(name, context)
    if kind == "batch":
        failed_indices = [] if result == [-1] else list(result)
        cause = _specific_error(name, arguments, context)
        if cause is None:
            cause = _default_error(name, context)
        return RizChartBatchError(
            translate_message(
                "batch.failed",
                failed_indices=failed_indices,
            ),
            function=name,
            context=context,
            failed_indices=failed_indices,
            errors=[cause],
            rolled_back=True,
            cause=cause,
        )

    # Prefer an obvious argument/domain failure before the function default.
    specific = _specific_error(name, arguments, context)
    if specific is not None:
        return specific
    return _default_error(name, context)


def _make_detailed_error(
    name: str,
    kind: str,
    result: object,
    context: dict,
    arguments: dict,
    failure,
) -> RizChartError:
    """Build an exception from a failure recorded inside the function."""
    fields = failure.fields()
    message = translate_failure(failure)

    if kind == "batch":
        failed_indices = [] if result == [-1] else list(result)
        base = _specific_error(name, arguments, context)
        if base is None:
            base = _default_error(name, context)
        cause_class = type(base)
        cause_fields = {
            key: value
            for key, value in fields.items()
            if key not in {"failed_indices", "errors", "rolled_back", "cause"}
        }
        if "expected" in cause_fields:
            cause_fields["expected"] = translate_expected(
                cause_fields["expected"]
            )
        if "allowed" in cause_fields:
            cause_fields["allowed"] = translate_expected(
                cause_fields["allowed"]
            )
        cause = cause_class(
            message,
            function=name,
            context=context,
            **cause_fields,
        )
        batch_fields = {
            key: value
            for key, value in fields.items()
            if key not in {"failed_indices", "errors", "rolled_back", "cause"}
        }
        if "expected" in batch_fields:
            batch_fields["expected"] = translate_expected(
                batch_fields["expected"]
            )
        if "allowed" in batch_fields:
            batch_fields["allowed"] = translate_expected(
                batch_fields["allowed"]
            )
        return RizChartBatchError(
            message,
            function=name,
            context=context,
            failed_indices=failed_indices,
            errors=[cause],
            rolled_back=True,
            cause=cause,
            **batch_fields,
        )

    base = _specific_error(name, arguments, context)
    if base is None:
        base = _default_error(name, context)
    error_class = _failure_error_class(failure, type(base))
    if kind == "validation":
        error_class = RizChartValidationError
    elif kind == "division":
        error_class = RizChartDivisionByZeroError
    elif kind == "color_mismatch":
        error_class = RizChartColorMismatchError
    elif kind == "false" and name == "export":
        error_class = RizChartExportError
    if name in {
        "xMirrorLine",
        "drawPolygon",
        "drawEllipse",
        "getClosedRegion",
    }:
        error_class = RizChartGeometryError
    elif name == "refresh":
        error_class = RizChartStructureError
    details = {
        key: value
        for key, value in vars(base).items()
        if key not in {"function", "context", "cause"}
    }
    details.update(fields)
    if "expected" in details:
        details["expected"] = translate_expected(details["expected"])
    if "allowed" in details:
        details["allowed"] = translate_expected(details["allowed"])
    return error_class(
        message,
        function=name,
        context=context,
        **details,
    )


def _failure_error_class(failure, fallback):
    code = failure.code or ""
    if code.startswith("index.") or code.endswith(".index_out_of_range"):
        return RizChartIndexError
    if code == "argument.type":
        return RizChartTypeError
    if code == "argument.value":
        return RizChartValueError
    if code.startswith("range."):
        return RizChartRangeError
    if code.startswith("canvas."):
        return RizChartCanvasError
    if code.startswith("color."):
        return RizChartColorError
    if code.startswith("bpm."):
        return RizChartBpmError
    if code.startswith("time.") or code.endswith(".time_invalid"):
        return RizChartTimeError
    if code.startswith("structure."):
        return RizChartStructureError
    if code.startswith("font."):
        return RizChartFontError
    if code.startswith("text."):
        return RizChartTextLayoutError
    if code.startswith("drawing."):
        return RizChartDrawingError
    return fallback


def _specific_error(
    name: str,
    arguments: dict,
    context: dict,
) -> RizChartError | None:
    chart = arguments.get("chart")
    if chart is not None and not isinstance(chart, dict):
        return RizChartTypeError(
            "chart 必须是 dict",
            function=name,
            context=context,
            parameter="chart",
            expected_type="dict",
            actual_type=type(chart).__name__,
            value=_summarize(chart),
        )

    if isinstance(chart, dict):
        index_specs = {
            "getLine": ("startindex", "lines", "line"),
            "getNoteCount": ("startindex", "lines", "line"),
            "getLinePoint": ("lineindex", "lines", "line"),
            "getRingPoint": ("lineindex", "lines", "line"),
            "getLineColor": ("lineindex", "lines", "line"),
            "getNote": ("lineindex", "lines", "line"),
            "getLineTimeRange": ("lineindex", "lines", "line"),
            "getNotePosition": ("lineindex", "lines", "line"),
            "getNoteCanvas": ("lineindex", "lines", "line"),
            "getCanvas": ("startindex", "canvasMoves", "canvas"),
            "getCanvasPosition": ("canvasindex", "canvasMoves", "canvas"),
            "getCanvasSpeed": ("canvasindex", "canvasMoves", "canvas"),
            "getCanvasPositionAt": ("index", "canvasMoves", "canvas"),
            "getBpmShift": ("startindex", "bpmShifts", "bpm shift"),
            "getTheme": ("startindex", "themes", "theme"),
            "getThemeColor": ("themeindex", "themes", "theme"),
            "getChallengeTime": ("startindex", "challengeTimes", "challenge time"),
            "getRiztime": ("startindex", "challengeTimes", "riztime"),
        }
        spec = index_specs.get(name)
        if spec is not None:
            key, field, kind = spec
            value = arguments.get(key)
            collection = chart.get(field)
            if (
                value is not None
                and isinstance(collection, list)
                and isinstance(value, int)
                and not isinstance(value, bool)
            ):
                count = len(collection)
                resolved = count + value if value < 0 else value
                if not 0 <= resolved < count:
                    return RizChartIndexError(
                        f"{kind} 索引不存在",
                        function=name,
                        context=context,
                        kind=kind,
                        index=value,
                        resolved_index=resolved,
                        length=count,
                    )

    bpm = arguments.get("bpm")
    if bpm is not None and _is_number(bpm) and float(bpm) <= 0.0:
        return RizChartBpmError(
            "BPM 必须大于 0",
            function=name,
            context=context,
            bpm=float(bpm),
            reason="non-positive bpm",
        )

    for key in ("gamespeed", "value", "camerascale", "gamescale", "Xwidth", "Ywidth"):
        value = arguments.get(key)
        if value is not None and _is_number(value) and float(value) <= 0.0:
            return RizChartValueError(
                f"{key} 必须大于 0",
                function=name,
                context=context,
                parameter=key,
                value=float(value),
                allowed="> 0",
            )

    start_time = arguments.get("starttime")
    end_time = arguments.get("endtime")
    if _is_number(start_time) and _is_number(end_time) and float(end_time) < float(start_time):
        return RizChartRangeError(
            "endtime 不能小于 starttime",
            function=name,
            context=context,
            start=float(start_time),
            end=float(end_time),
        )

    for key, value in arguments.items():
        lower = key.lower()
        if lower in _TIME_KEYS and value is not None and _is_number(value):
            if float(value) < 0.0:
                return RizChartTimeError(
                    f"{key} 不能为负数",
                    function=name,
                    context=context,
                    time=float(value),
                    is_real=bool(
                        arguments.get("isRealTime")
                        or arguments.get("isRealStartTime")
                        or arguments.get("isRealEndTime")
                    ),
                )
        if lower in _EASE_KEYS and value is not None and not _valid_ease(value):
            return RizChartEaseError(
                "easetype 非法",
                function=name,
                context=context,
                easetype=value,
                allowed="0..25 或 [x1,y1,x2,y2]",
            )
        if lower in _COLOR_KEYS and value is not None and not _valid_color(value):
            return RizChartColorError(
                f"{key} 颜色非法",
                function=name,
                context=context,
                color=_summarize(value),
                path=[key],
            )
        if lower in _COLOR_LIST_KEYS and value is not None and not _valid_color_list(value):
            return RizChartColorError(
                f"{key} 颜色列表非法",
                function=name,
                context=context,
                color=_summarize(value),
                path=[key],
            )

    if name == "getRingColor":
        query_time = arguments.get("time")
        if _is_number(query_time) and float(query_time) <= 0.0:
            return RizChartTimeError(
                "time 必须大于 0.0",
                function=name,
                context=context,
                time=float(query_time),
                domain="positive",
            )

    text = arguments.get("text")
    if isinstance(text, str) and ("\n" in text or "\r" in text):
        return RizChartTextLayoutError(
            "文本不能包含换行符",
            function=name,
            context=context,
            text=text,
            reason="newline",
        )

    fontpath = arguments.get("fontpath")
    if fontpath is not None and name in {"drawText", "drawThinText"}:
        if not isinstance(fontpath, (str, Path)):
            return RizChartFontError(
                "fontpath 类型非法",
                function=name,
                context=context,
                fontpath=repr(fontpath),
                reason="invalid fontpath type",
            )
        if not Path(fontpath).exists():
            return RizChartFontError(
                "字体文件不存在",
                function=name,
                context=context,
                fontpath=str(fontpath),
                reason="font file not found",
            )

    line_index = arguments.get("lineindex")
    if (
        line_index is not None
        and isinstance(chart, dict)
        and isinstance(chart.get("lines"), list)
        and isinstance(line_index, int)
        and not isinstance(line_index, bool)
    ):
        count = len(chart["lines"])
        resolved = count + line_index if line_index < 0 else line_index
        if not 0 <= resolved < count:
            return RizChartIndexError(
                "线索引不存在",
                function=name,
                context=context,
                kind="line",
                index=line_index,
                resolved_index=resolved,
                length=count,
            )

    canvas_index = arguments.get("canvasindex")
    if (
        canvas_index is not None
        and isinstance(chart, dict)
        and isinstance(chart.get("canvasMoves"), list)
        and isinstance(canvas_index, int)
        and not isinstance(canvas_index, bool)
    ):
        count = len(chart["canvasMoves"])
        resolved = count + canvas_index if canvas_index < 0 else canvas_index
        if not 0 <= resolved < count:
            return RizChartCanvasError(
                "画布索引不存在",
                function=name,
                context=context,
                canvasindex=canvas_index,
                reason="out of range",
            )

    return None


def _default_error(name: str, context: dict) -> RizChartError:
    error_class = _SPECIAL_DEFAULT.get(name, RizChartStructureError)
    return _build_default(name, error_class, context)


def _build_default(name: str, error_class: type, context: dict) -> RizChartError:
    details = {}
    if error_class is RizChartLoadError:
        details["filename"] = context.get("filename")
        details["reason"] = "file or JSON load failed"
    elif error_class is RizChartExportError:
        details["filename"] = context.get("filename")
        details["reason"] = "export failed"
    elif error_class is RizChartValidationError:
        details["issues"] = context.get("result")
    elif error_class is RizChartFontError:
        details["fontpath"] = context.get("fontpath")
    elif error_class is RizChartTextLayoutError:
        details["text"] = context.get("text")
    elif error_class is RizChartGeometryError:
        details["lineindexlist"] = context.get("lineindexlist")
    elif error_class is RizChartBatchError:
        details["failed_indices"] = []
        details["errors"] = []
        details["rolled_back"] = True
    message = translate_message("common.default_failure")
    return error_class(message, function=name, context=context, **details)


def _valid_color(value: object) -> bool:
    return isinstance(value, (str, list)) and _parse_color(value) is not None


def _valid_color_list(value: object) -> bool:
    if isinstance(value, str):
        return _parse_color(value) is not None
    if not isinstance(value, list) or not value:
        return False
    if _parse_color(value) is not None:
        return True
    return all(isinstance(item, (str, list)) and _parse_color(item) is not None for item in value)


def _valid_ease(value: object) -> bool:
    if isinstance(value, int) and not isinstance(value, bool):
        return 0 <= value <= 25
    if isinstance(value, list) and len(value) == 4:
        return all(_is_number(item) for item in value)
    return False


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _summarize(value: object) -> object:
    if isinstance(value, dict):
        return {"type": "dict", "size": len(value)}
    if isinstance(value, (list, tuple)):
        return {"type": type(value).__name__, "size": len(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
