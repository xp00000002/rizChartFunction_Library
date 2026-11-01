"""Rizline 谱面基础操作。

目前提供以下函数：

* ``new()``   -- 新建一份空谱面，返回 dict。
* ``load()``  -- 读取谱面文件，清洗并规范化后返回 dict。
* ``export()``-- 校验通过后把谱面写回 JSON 文件。
* ``check()`` -- 以只读方式检查谱面，返回问题路径或 ``None``。
* ``refresh()``-- 按时间重排节点/Note 并重算 ``floorPosition``。

标准格式参考 Rizline 中文维基的「关卡文件格式」页面，并以官方谱面
（E:\\RizChartTool\\input\\20260109 等）中实际使用的键名为准。需要注意
官方文件使用的是 ``bpmShifts``（小写 p），而不是维基页面上的
``bPMShifts``；本模块以 ``bpmShifts`` 为标准，同时兼容读取旧键名。
"""

from __future__ import annotations

import json
import math

from ._internal import (
    _apply_floor_plan,
    _bpm_seconds,
    _canvas_ref,
    _find_canvas,
    _is_finite_number,
    _is_int,
    _is_number,
    _make_floor_plan,
    _seconds_at,
)
from .chart import (
    _canvas_floor_position_at,
    _canvas_speed_points,
    _line_note_position,
)

__all__ = ["new", "load", "export", "check", "refresh"]


_MISSING = object()


class _ListOf:
    """描述“列表，且每个元素都符合 item 描述”的类型。"""

    __slots__ = ("item",)

    def __init__(self, item: object) -> None:
        self.item = item


_INT = "int"
_NUMBER = "number"

_COLOR = {
    "r": _INT,
    "g": _INT,
    "b": _INT,
    "a": _INT,
}

_KEY_POINT = {
    "time": _NUMBER,
    "value": _NUMBER,
    "easeType": _INT,
    "floorPosition": _NUMBER,
}

_COLOR_CHANGE = {
    "startColor": _COLOR,
    "endColor": _COLOR,
    "time": _NUMBER,
}

_LINE_POINT = {
    "time": _NUMBER,
    "xPosition": _NUMBER,
    "color": _COLOR,
    "easeType": _INT,
    "canvasIndex": _INT,
    "floorPosition": _NUMBER,
}

_NOTE = {
    "type": _INT,
    "time": _NUMBER,
    "floorPosition": _NUMBER,
}

_LINE = {
    "linePoints": _ListOf(_LINE_POINT),
    "notes": _ListOf("note"),
    "judgeRingColor": _ListOf(_COLOR_CHANGE),
    "lineColor": _ListOf(_COLOR_CHANGE),
}

_CANVAS_MOVE = {
    "index": _INT,
    "xPositionKeyPoints": _ListOf(_KEY_POINT),
    "speedKeyPoints": _ListOf(_KEY_POINT),
}

_CAMERA_MOVE = {
    "scaleKeyPoints": _ListOf(_KEY_POINT),
    "xPositionKeyPoints": _ListOf(_KEY_POINT),
}

_ROOT = {
    "fileVersion": _INT,
    "chartDelayMs": _INT,
    "themes": _ListOf({"colorsList": _ListOf(_COLOR)}),
    "challengeTimes": _ListOf(
        {
            "checkPoint": _NUMBER,
            "start": _NUMBER,
            "end": _NUMBER,
            "transTime": _NUMBER,
        }
    ),
    "bPM": _NUMBER,
    "bpmShifts": _ListOf(_KEY_POINT),
    "lines": _ListOf(_LINE),
    "canvasMoves": _ListOf(_CANVAS_MOVE),
    "cameraMove": _CAMERA_MOVE,
}


def _sanitize_note(value: object) -> object:
    """清洗单个音符。

    ``otherInformations`` 需要结合音符类型判断：

    * Tap / Drag：空列表，或正好 3 个数字；
    * Hold：正好 3 个数字（尾部的 time、画布索引、floorPosition）。

    官方谱面中部分 Tap / Drag 会省略该键，也存在带有 3 个数字的
    Tap，因此这里保留这些写法，不会主动补键。
    """
    if not isinstance(value, dict):
        return _MISSING

    result: dict[str, object] = {}
    for key, item in value.items():
        if key == "otherInformations":
            continue
        spec = _NOTE.get(key)
        if spec is None:
            continue
        sanitized = _sanitize(item, spec)
        if sanitized is not _MISSING:
            result[key] = sanitized

    if "otherInformations" not in value:
        return result

    extra = value["otherInformations"]
    note_type = result.get("type", value.get("type"))
    if not isinstance(extra, list) or not all(_is_number(item) for item in extra):
        return result
    if len(extra) == 3 or (len(extra) == 0 and note_type in (0, 1)):
        result["otherInformations"] = list(extra)

    return result


def _sanitize(value: object, spec: object) -> object:
    if spec == _INT:
        return value if _is_int(value) else _MISSING
    if spec == _NUMBER:
        return value if _is_number(value) else _MISSING
    if spec == "note":
        return _sanitize_note(value)
    if isinstance(spec, _ListOf):
        if not isinstance(value, list):
            return _MISSING
        result = []
        for item in value:
            sanitized = _sanitize(item, spec.item)
            if sanitized is not _MISSING:
                result.append(sanitized)
        return result
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            return _MISSING
        result = {}
        for key, item in value.items():
            child_spec = spec.get(key)
            if child_spec is None:
                continue
            sanitized = _sanitize(item, child_spec)
            if sanitized is not _MISSING:
                result[key] = sanitized
        return result

    raise TypeError(f"未知的格式描述: {spec!r}")


def _default_color() -> dict:
    return {"r": 255, "g": 255, "b": 255, "a": 255}


def _default_theme() -> dict:
    return {"colorsList": [_default_color() for _ in range(3)]}


def _default_themes() -> list:
    return [_default_theme(), _default_theme()]


def _default_challenge_times() -> list:
    return [
        {
            "checkPoint": 0.0,
            "start": 0.0,
            "end": 0.0,
            "transTime": 0.5,
        }
    ]


def _fix_theme_counts(chart: dict) -> None:
    """调整 themes 与 challengeTimes 的数量关系。

    标准关系为 ``len(themes) == len(challengeTimes) + 1``。只有 1 个
    theme 时补一个默认 theme；数量不满足关系时从末尾删除较多的那一方。
    """
    themes = chart.get("themes")
    challenge_times = chart.get("challengeTimes")
    if not isinstance(themes, list) or not isinstance(challenge_times, list):
        return

    if not themes:
        themes.extend(_default_themes())
    elif len(themes) == 1:
        themes.append(_default_theme())

    if not challenge_times:
        challenge_times.extend(_default_challenge_times())

    while len(themes) > len(challenge_times) + 1:
        themes.pop()
    while len(themes) < len(challenge_times) + 1:
        challenge_times.pop()


_FLOOR_TOLERANCE = 1e-2
_NOTE_KEYS = set(_NOTE) | {"otherInformations"}


def _new_issues() -> dict:
    return {
        "unexpectedParts": [],
        "missingParts": [],
        "errorValues": [],
    }


def _add_issue(issues: dict, kind: str, path: list) -> None:
    target = issues[kind]
    if path not in target:
        target.append(path)


def _walk_note(value: object, path: list, issues: dict) -> None:
    if not isinstance(value, dict):
        _add_issue(issues, "errorValues", path)
        return

    for key in value:
        if key not in _NOTE_KEYS:
            _add_issue(issues, "unexpectedParts", path + [key])

    note_type = value.get("type")
    for key in ("type", "time", "floorPosition"):
        if key not in value:
            _add_issue(issues, "missingParts", path + [key])
        else:
            _walk_schema(
                value[key],
                _NOTE[key],
                path + [key],
                issues,
            )

    if "otherInformations" not in value:
        if note_type == 2:
            _add_issue(
                issues,
                "missingParts",
                path + ["otherInformations"],
            )
        return

    extra = value["otherInformations"]
    extra_path = path + ["otherInformations"]
    if not isinstance(extra, list):
        _add_issue(issues, "errorValues", extra_path)
        return

    for index, item in enumerate(extra):
        if not _is_number(item):
            _add_issue(issues, "errorValues", extra_path + [index])

    length = len(extra)
    if note_type == 2:
        for index in range(length, 3):
            _add_issue(issues, "missingParts", extra_path + [index])
        for index in range(3, length):
            _add_issue(
                issues,
                "unexpectedParts",
                extra_path + [index],
            )
    elif note_type in (0, 1):
        if 3 < length:
            for index in range(3, length):
                _add_issue(
                    issues,
                    "unexpectedParts",
                    extra_path + [index],
                )
        elif 0 < length < 3:
            for index in range(length, 3):
                _add_issue(
                    issues,
                    "missingParts",
                    extra_path + [index],
                )


def _walk_schema(
    value: object,
    spec: object,
    path: list,
    issues: dict,
) -> None:
    if spec == _INT:
        if not _is_int(value):
            _add_issue(issues, "errorValues", path)
        return
    if spec == _NUMBER:
        if not _is_number(value):
            _add_issue(issues, "errorValues", path)
        return
    if spec == "note":
        _walk_note(value, path, issues)
        return
    if isinstance(spec, _ListOf):
        if not isinstance(value, list):
            _add_issue(issues, "errorValues", path)
            return
        for index, item in enumerate(value):
            _walk_schema(
                item,
                spec.item,
                path + [index],
                issues,
            )
        return
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            _add_issue(issues, "errorValues", path)
            return
        for key in value:
            if key not in spec:
                _add_issue(
                    issues,
                    "unexpectedParts",
                    path + [key],
                )
        for key, child_spec in spec.items():
            if key not in value:
                _add_issue(issues, "missingParts", path + [key])
            else:
                _walk_schema(
                    value[key],
                    child_spec,
                    path + [key],
                    issues,
                )
        return

    raise TypeError(f"未知的格式描述: {spec!r}")


def _require_min(
    items: object,
    path: list,
    minimum: int,
    issues: dict,
) -> None:
    if not isinstance(items, list):
        return
    for index in range(len(items), minimum):
        _add_issue(issues, "missingParts", path + [index])


def _require_exact(
    items: object,
    path: list,
    count: int,
    issues: dict,
) -> None:
    if not isinstance(items, list):
        return
    for index in range(len(items), count):
        _add_issue(issues, "missingParts", path + [index])
    for index in range(count, len(items)):
        _add_issue(issues, "unexpectedParts", path + [index])


def _check_lengths(chart: dict, issues: dict) -> None:
    themes = chart.get("themes")
    _require_min(themes, ["themes"], 2, issues)
    _require_min(
        chart.get("challengeTimes"),
        ["challengeTimes"],
        1,
        issues,
    )
    _require_min(
        chart.get("bpmShifts"),
        ["bpmShifts"],
        1,
        issues,
    )
    _require_min(
        chart.get("canvasMoves"),
        ["canvasMoves"],
        1,
        issues,
    )

    if isinstance(themes, list):
        for index, theme in enumerate(themes):
            if isinstance(theme, dict):
                _require_exact(
                    theme.get("colorsList"),
                    ["themes", index, "colorsList"],
                    3,
                    issues,
                )

    canvases = chart.get("canvasMoves")
    if isinstance(canvases, list):
        for index, canvas in enumerate(canvases):
            if not isinstance(canvas, dict):
                continue
            _require_min(
                canvas.get("xPositionKeyPoints"),
                ["canvasMoves", index, "xPositionKeyPoints"],
                1,
                issues,
            )
            _require_min(
                canvas.get("speedKeyPoints"),
                ["canvasMoves", index, "speedKeyPoints"],
                1,
                issues,
            )

    camera = chart.get("cameraMove")
    if isinstance(camera, dict):
        _require_min(
            camera.get("scaleKeyPoints"),
            ["cameraMove", "scaleKeyPoints"],
            1,
            issues,
        )
        _require_min(
            camera.get("xPositionKeyPoints"),
            ["cameraMove", "xPositionKeyPoints"],
            1,
            issues,
        )

    lines = chart.get("lines")
    if isinstance(lines, list):
        for index, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            _require_min(
                line.get("linePoints"),
                ["lines", index, "linePoints"],
                2,
                issues,
            )
            _require_min(
                line.get("judgeRingColor"),
                ["lines", index, "judgeRingColor"],
                1,
                issues,
            )

    ctimes = chart.get("challengeTimes")
    if (
        isinstance(themes, list)
        and isinstance(ctimes, list)
        and len(themes) >= 2
        and len(ctimes) >= 1
    ):
        expected = len(ctimes) + 1
        if len(themes) > expected:
            for index in range(expected, len(themes)):
                _add_issue(
                    issues,
                    "unexpectedParts",
                    ["themes", index],
                )
        elif len(themes) < expected:
            for index in range(len(themes) - 1, len(ctimes)):
                _add_issue(
                    issues,
                    "unexpectedParts",
                    ["challengeTimes", index],
                )


def _iter_time_slots(chart: dict):
    shifts = chart.get("bpmShifts")
    if isinstance(shifts, list):
        for index, node in enumerate(shifts):
            if isinstance(node, dict) and "time" in node:
                yield node, "time", ["bpmShifts", index, "time"]

    ctimes = chart.get("challengeTimes")
    if isinstance(ctimes, list):
        for index, item in enumerate(ctimes):
            if not isinstance(item, dict):
                continue
            for key in ("checkPoint", "start", "end", "transTime"):
                if key in item:
                    yield (
                        item,
                        key,
                        ["challengeTimes", index, key],
                    )

    canvases = chart.get("canvasMoves")
    if isinstance(canvases, list):
        for ci, canvas in enumerate(canvases):
            if not isinstance(canvas, dict):
                continue
            for key in ("xPositionKeyPoints", "speedKeyPoints"):
                points = canvas.get(key)
                if not isinstance(points, list):
                    continue
                for ki, point in enumerate(points):
                    if isinstance(point, dict) and "time" in point:
                        yield (
                            point,
                            "time",
                            ["canvasMoves", ci, key, ki, "time"],
                        )

    camera = chart.get("cameraMove")
    if isinstance(camera, dict):
        for key in ("scaleKeyPoints", "xPositionKeyPoints"):
            points = camera.get(key)
            if not isinstance(points, list):
                continue
            for ki, point in enumerate(points):
                if isinstance(point, dict) and "time" in point:
                    yield (
                        point,
                        "time",
                        ["cameraMove", key, ki, "time"],
                    )

    lines = chart.get("lines")
    if isinstance(lines, list):
        for li, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            points = line.get("linePoints")
            if isinstance(points, list):
                for pi, point in enumerate(points):
                    if isinstance(point, dict) and "time" in point:
                        yield (
                            point,
                            "time",
                            ["lines", li, "linePoints", pi, "time"],
                        )
            for key in ("judgeRingColor", "lineColor"):
                items = line.get(key)
                if not isinstance(items, list):
                    continue
                for ci, item in enumerate(items):
                    if isinstance(item, dict) and "time" in item:
                        yield (
                            item,
                            "time",
                            ["lines", li, key, ci, "time"],
                        )
            notes = line.get("notes")
            if isinstance(notes, list):
                for ni, note in enumerate(notes):
                    if not isinstance(note, dict):
                        continue
                    if "time" in note:
                        yield (
                            note,
                            "time",
                            ["lines", li, "notes", ni, "time"],
                        )
                    if note.get("type") != 2:
                        continue
                    extra = note.get("otherInformations")
                    if isinstance(extra, list) and len(extra) >= 1:
                        yield (
                            extra,
                            0,
                            [
                                "lines",
                                li,
                                "notes",
                                ni,
                                "otherInformations",
                                0,
                            ],
                        )


def _iter_ease_slots(chart: dict):
    shifts = chart.get("bpmShifts")
    if isinstance(shifts, list):
        for index, node in enumerate(shifts):
            if isinstance(node, dict) and "easeType" in node:
                yield (
                    node,
                    "easeType",
                    ["bpmShifts", index, "easeType"],
                )

    canvases = chart.get("canvasMoves")
    if isinstance(canvases, list):
        for ci, canvas in enumerate(canvases):
            if not isinstance(canvas, dict):
                continue
            for key in ("xPositionKeyPoints", "speedKeyPoints"):
                points = canvas.get(key)
                if not isinstance(points, list):
                    continue
                for ki, point in enumerate(points):
                    if isinstance(point, dict) and "easeType" in point:
                        yield (
                            point,
                            "easeType",
                            [
                                "canvasMoves",
                                ci,
                                key,
                                ki,
                                "easeType",
                            ],
                        )

    camera = chart.get("cameraMove")
    if isinstance(camera, dict):
        for key in ("scaleKeyPoints", "xPositionKeyPoints"):
            points = camera.get(key)
            if not isinstance(points, list):
                continue
            for ki, point in enumerate(points):
                if isinstance(point, dict) and "easeType" in point:
                    yield (
                        point,
                        "easeType",
                        ["cameraMove", key, ki, "easeType"],
                    )

    lines = chart.get("lines")
    if isinstance(lines, list):
        for li, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            points = line.get("linePoints")
            if not isinstance(points, list):
                continue
            for pi, point in enumerate(points):
                if isinstance(point, dict) and "easeType" in point:
                    yield (
                        point,
                        "easeType",
                        ["lines", li, "linePoints", pi, "easeType"],
                    )


def _iter_color_slots(chart: dict):
    themes = chart.get("themes")
    if isinstance(themes, list):
        for ti, theme in enumerate(themes):
            if not isinstance(theme, dict):
                continue
            colors = theme.get("colorsList")
            if not isinstance(colors, list):
                continue
            for ci, color in enumerate(colors):
                if isinstance(color, dict):
                    yield color, ["themes", ti, "colorsList", ci]

    lines = chart.get("lines")
    if isinstance(lines, list):
        for li, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            points = line.get("linePoints")
            if isinstance(points, list):
                for pi, point in enumerate(points):
                    if not isinstance(point, dict):
                        continue
                    color = point.get("color")
                    if isinstance(color, dict):
                        yield (
                            color,
                            ["lines", li, "linePoints", pi, "color"],
                        )
            for key in ("judgeRingColor", "lineColor"):
                items = line.get(key)
                if not isinstance(items, list):
                    continue
                for ci, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue
                    for side in ("startColor", "endColor"):
                        color = item.get(side)
                        if isinstance(color, dict):
                            yield (
                                color,
                                ["lines", li, key, ci, side],
                            )


def _check_values(chart: dict, issues: dict) -> None:
    bpm = chart.get("bPM")
    if _is_number(bpm) and bpm <= 0:
        _add_issue(issues, "errorValues", ["bPM"])

    shifts = chart.get("bpmShifts")
    if isinstance(shifts, list):
        for index, node in enumerate(shifts):
            if not isinstance(node, dict):
                continue
            value = node.get("value")
            if _is_number(value) and value <= 0:
                _add_issue(
                    issues,
                    "errorValues",
                    ["bpmShifts", index, "value"],
                )

    for container, key, path in _iter_time_slots(chart):
        if isinstance(container, dict):
            value = container.get(key)
        else:
            value = container[key]
        if _is_number(value) and value < 0:
            _add_issue(issues, "errorValues", path)

    for container, key, path in _iter_ease_slots(chart):
        value = container.get(key)
        if _is_int(value) and not 0 <= value <= 18:
            _add_issue(issues, "errorValues", path)

    for color, path in _iter_color_slots(chart):
        for channel in ("r", "g", "b", "a"):
            value = color.get(channel)
            if _is_int(value) and not 0 <= value <= 255:
                _add_issue(
                    issues,
                    "errorValues",
                    path + [channel],
                )

    canvases = chart.get("canvasMoves")
    canvas_indices = set()
    seen_indices = set()
    if isinstance(canvases, list):
        for index, canvas in enumerate(canvases):
            if not isinstance(canvas, dict):
                continue
            canvas_index = canvas.get("index")
            if not _is_int(canvas_index):
                continue
            canvas_indices.add(canvas_index)
            if canvas_index < 0:
                _add_issue(
                    issues,
                    "errorValues",
                    ["canvasMoves", index, "index"],
                )
            if canvas_index in seen_indices:
                _add_issue(
                    issues,
                    "errorValues",
                    ["canvasMoves", index, "index"],
                )
            else:
                seen_indices.add(canvas_index)

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return
    for li, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        points = line.get("linePoints")
        notes = line.get("notes")
        if not isinstance(points, list) or not isinstance(notes, list):
            continue
        for pi, point in enumerate(points):
            if not isinstance(point, dict):
                continue
            canvas_index = point.get("canvasIndex")
            if (
                _is_int(canvas_index)
                and canvas_index not in canvas_indices
            ):
                _add_issue(
                    issues,
                    "errorValues",
                    [
                        "lines",
                        li,
                        "linePoints",
                        pi,
                        "canvasIndex",
                    ],
                )

        first = None
        last = None
        if points and isinstance(points[0], dict):
            first = points[0].get("time")
        if points and isinstance(points[-1], dict):
            last = points[-1].get("time")
        span_ok = _is_number(first) and _is_number(last)

        for ni, note in enumerate(notes):
            if not isinstance(note, dict):
                continue
            note_type = note.get("type")
            if _is_int(note_type) and note_type not in (0, 1, 2):
                _add_issue(
                    issues,
                    "errorValues",
                    ["lines", li, "notes", ni, "type"],
                )
            note_time = note.get("time")
            if (
                span_ok
                and _is_number(note_time)
                and (note_time < first or note_time > last)
            ):
                _add_issue(
                    issues,
                    "errorValues",
                    ["lines", li, "notes", ni, "time"],
                )
            extra = note.get("otherInformations")
            if not isinstance(extra, list) or len(extra) != 3:
                continue
            canvas_ref = _canvas_ref(extra[1])
            if canvas_ref not in canvas_indices:
                _add_issue(
                    issues,
                    "errorValues",
                    [
                        "lines",
                        li,
                        "notes",
                        ni,
                        "otherInformations",
                        1,
                    ],
                )
            if note_type != 2:
                continue
            tail_time = extra[0]
            if (
                span_ok
                and _is_number(tail_time)
                and (tail_time < first or tail_time > last)
            ):
                _add_issue(
                    issues,
                    "errorValues",
                    [
                        "lines",
                        li,
                        "notes",
                        ni,
                        "otherInformations",
                        0,
                    ],
                )


def _check_floor_positions(chart: dict, issues: dict) -> None:
    plan = _make_floor_plan(chart)
    if plan is None:
        return

    paths = {}
    for index, node in enumerate(chart.get("bpmShifts", [])):
        if isinstance(node, dict):
            paths[id(node)] = [
                "bpmShifts",
                index,
                "floorPosition",
            ]
    for ci, canvas in enumerate(chart.get("canvasMoves", [])):
        if not isinstance(canvas, dict):
            continue
        points = canvas.get("speedKeyPoints")
        if not isinstance(points, list):
            continue
        for ki, point in enumerate(points):
            if isinstance(point, dict):
                paths[id(point)] = [
                    "canvasMoves",
                    ci,
                    "speedKeyPoints",
                    ki,
                    "floorPosition",
                ]
    for li, line in enumerate(chart.get("lines", [])):
        if not isinstance(line, dict):
            continue
        points = line.get("linePoints")
        if isinstance(points, list):
            for pi, point in enumerate(points):
                if isinstance(point, dict):
                    paths[id(point)] = [
                        "lines",
                        li,
                        "linePoints",
                        pi,
                        "floorPosition",
                    ]
        notes = line.get("notes")
        if isinstance(notes, list):
            for ni, note in enumerate(notes):
                if not isinstance(note, dict):
                    continue
                paths[id(note)] = [
                    "lines",
                    li,
                    "notes",
                    ni,
                    "floorPosition",
                ]
                extra = note.get("otherInformations")
                if isinstance(extra, list) and len(extra) == 3:
                    paths[id(extra)] = [
                        "lines",
                        li,
                        "notes",
                        ni,
                        "otherInformations",
                    ]

    def check_value(obj: dict, expected: float) -> None:
        path = paths.get(id(obj))
        if path is None:
            return
        value = obj.get("floorPosition")
        if not _is_number(value):
            return
        if not abs(value - expected) <= _FLOOR_TOLERANCE:
            _add_issue(issues, "errorValues", path)

    for node, expected in plan["bpmShifts"]:
        check_value(node, expected)
    for point, expected in plan["canvasSpeedKeyPoints"]:
        check_value(point, expected)
    for point, expected in plan["linePoints"]:
        check_value(point, expected)
    for note, expected in plan["notes"]:
        check_value(note, expected)

    for extra, canvas_index, expected in plan["holds"]:
        path = paths.get(id(extra))
        if path is None:
            continue
        if _canvas_ref(extra[1]) != canvas_index:
            _add_issue(issues, "errorValues", path + [1])
        stored = extra[2]
        if not _is_number(stored):
            continue
        if not abs(stored - expected) <= _FLOOR_TOLERANCE:
            _add_issue(issues, "errorValues", path + [2])


def check(chart: object) -> dict | None:
    """检查谱面是否符合标准格式，不修改谱面。

    返回 ``unexpectedParts`` / ``missingParts`` / ``errorValues``
    三组路径；没有问题时返回 ``None``。路径数组只定位到最顶层的
    非法项，不再递归其内部。
    """
    if not isinstance(chart, dict):
        return {
            "unexpectedParts": [],
            "missingParts": [],
            "errorValues": [[]],
        }

    issues = _new_issues()
    _walk_schema(chart, _ROOT, [], issues)
    _check_lengths(chart, issues)
    _check_values(chart, issues)
    _check_floor_positions(chart, issues)

    if any(issues.values()):
        return issues
    return None


def _sorted_time_items(values: object) -> tuple[list, bool] | None:
    """返回按 ``time`` 稳定排序的副本，以及顺序是否发生变化。"""
    if not isinstance(values, list):
        return None
    for item in values:
        if not isinstance(item, dict):
            return None
        if not _is_finite_number(item.get("time")):
            return None

    ordered = sorted(values, key=lambda item: item["time"])
    changed = any(
        left is not right
        for left, right in zip(values, ordered)
    )
    return ordered, changed


class _RefreshFailure(Exception):
    """内部使用：表示 refresh 无法完成。"""


def _refresh_range(
    length: int,
    start: int,
    end: int,
) -> range | None:
    """把闭区间索引转换为范围；出界部分忽略，空交集返回空范围。"""
    if not _is_int(start) or not _is_int(end):
        return None
    if length <= 0:
        return range(0)

    if start < 0:
        start += length
    if end < 0:
        end += length
    if start < 0:
        start = 0
    if end >= length:
        end = length - 1
    if start >= length or end < 0 or start > end:
        return range(0)
    return range(start, end + 1)


def _is_nan(value: object) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _refresh_add_sort(
    targets: list[dict],
    container: dict,
    key: str,
    start: int = 0,
    stop: int | None = None,
) -> list:
    values = container.get(key)
    if not isinstance(values, list):
        raise _RefreshFailure
    if stop is None:
        stop = len(values)
    selected = values[start:stop]
    result = _sorted_time_items(selected)
    if result is None:
        raise _RefreshFailure
    ordered, changed = result
    targets.append(
        {
            "container": container,
            "key": key,
            "start": start,
            "stop": stop,
            "original": list(selected),
            "ordered": ordered,
            "changed": changed,
        }
    )
    return values


def _apply_refresh_order(targets: list[dict]) -> None:
    for target in targets:
        if target["changed"]:
            target["container"][target["key"]][
                target["start"]:target["stop"]
            ] = target["ordered"]


def _restore_refresh_order(targets: list[dict]) -> None:
    for target in targets:
        if target["changed"]:
            target["container"][target["key"]][
                target["start"]:target["stop"]
            ] = target["original"]


def _refresh_add_floor(
    pending: list[tuple],
    node: dict,
    expected: float,
    only_nan: bool,
) -> None:
    if not _is_finite_number(expected):
        raise _RefreshFailure
    if only_nan and not _is_nan(node.get("floorPosition")):
        return
    pending.append(("floor", node, expected))


def _refresh_add_hold(
    pending: list[tuple],
    extra: object,
    canvas_index: int,
    expected: float,
    only_nan: bool,
) -> None:
    if (
        not isinstance(extra, list)
        or len(extra) != 3
        or not _is_int(canvas_index)
        or not _is_finite_number(expected)
    ):
        raise _RefreshFailure
    if only_nan and not _is_nan(extra[2]):
        return
    pending.append(("hold", extra, canvas_index, expected))


def _floor_value_matches(value: object, expected: float) -> bool:
    return (
        _is_finite_number(value)
        and math.isfinite(expected)
        and value == expected
    )


def _refresh_pending_changed(pending: list[tuple]) -> bool:
    for item in pending:
        if item[0] == "floor":
            _, node, expected = item
            if not _floor_value_matches(node.get("floorPosition"), expected):
                return True
        else:
            _, extra, canvas_index, expected = item
            if _canvas_ref(extra[1]) != canvas_index:
                return True
            if not _floor_value_matches(extra[2], expected):
                return True
    return False


def _refresh_apply_pending(pending: list[tuple]) -> None:
    for item in pending:
        if item[0] == "floor":
            _, node, expected = item
            node["floorPosition"] = expected
        else:
            _, extra, canvas_index, expected = item
            extra[1] = canvas_index
            extra[2] = expected


def _refresh_camera(camera: object) -> dict:
    if not isinstance(camera, dict):
        raise _RefreshFailure
    return camera


def _refresh_list(container: dict, key: str) -> list:
    values = container.get(key)
    if not isinstance(values, list):
        raise _RefreshFailure
    return values


def refresh(
    chart: dict,
    mode: str = "all",
    type: str = "all",
    startindex: int = 0,
    endindex: int = -1,
    startlineindex: int = 0,
    endlineindex: int = -1,
    isOnlyRefreshNaN: bool = False,
) -> bool | None:
    """按模式、类型和索引范围刷新谱面。

    ``mode``：``"all"`` 重排并重算高度；``"floorPosition"`` 只重算高度；
    ``"order"`` 只排序。``type`` 选择刷新对象。星号类型（``"all"``、
    ``"camera"``）忽略起止索引；井号类型（``linePoints`` / ``notes`` /
    ``judgeRingColor`` / ``lineColor``）使用行索引范围与节点索引范围。
    """
    modes = {"all", "floorPosition", "order"}
    types = {
        "all",
        "bpmShifts",
        "lines",
        "linePoints",
        "notes",
        "judgeRingColor",
        "lineColor",
        "canvas",
        "canvasPosition",
        "canvasSpeed",
        "camera",
        "cameraPosition",
        "cameraScale",
    }
    if (
        not isinstance(chart, dict)
        or not isinstance(mode, str)
        or not isinstance(type, str)
    ):
        return None
    if mode not in modes or type not in types:
        return None

    only_nan = False
    if mode != "order":
        if not isinstance(isOnlyRefreshNaN, bool):
            return None
        only_nan = isOnlyRefreshNaN

    targets: list[dict] = []
    pending: list[tuple] = []
    bpm_nodes: list[dict] = []
    speed_groups: list[tuple[dict, list]] = []
    line_nodes: list[tuple[dict, dict]] = []
    note_nodes: list[tuple[dict, dict]] = []
    zero_nodes: list[dict] = []
    selected = False

    def add_sort(
        container: dict,
        key: str,
        indices: range | None = None,
    ) -> list:
        if indices is None:
            return _refresh_add_sort(targets, container, key)
        return _refresh_add_sort(
            targets,
            container,
            key,
            indices.start,
            indices.stop,
        )

    def get_list(container: dict, key: str) -> list:
        return _refresh_list(container, key)

    try:
        # ------------------------------------------------------------
        # 选择对象，并在 order/all 模式下绑定排序目标
        # ------------------------------------------------------------
        if type == "all":
            selected = True
            get_list(chart, "bpmShifts")
            if mode in ("all", "order"):
                add_sort(chart, "bpmShifts")

            canvases = get_list(chart, "canvasMoves")
            for canvas in canvases:
                if not isinstance(canvas, dict):
                    raise _RefreshFailure
                x_points = get_list(canvas, "xPositionKeyPoints")
                speed_points = get_list(canvas, "speedKeyPoints")
                if mode in ("all", "order"):
                    add_sort(canvas, "xPositionKeyPoints")
                    add_sort(canvas, "speedKeyPoints")
                zero_nodes.extend(x_points)

            camera = _refresh_camera(chart.get("cameraMove"))
            for key in ("scaleKeyPoints", "xPositionKeyPoints"):
                points = get_list(camera, key)
                if mode in ("all", "order"):
                    add_sort(camera, key)
                zero_nodes.extend(points)

            lines = get_list(chart, "lines")
            for line in lines:
                if not isinstance(line, dict):
                    raise _RefreshFailure
                for key in (
                    "linePoints",
                    "notes",
                    "judgeRingColor",
                    "lineColor",
                ):
                    get_list(line, key)
                    if mode in ("all", "order"):
                        add_sort(line, key)

        elif type == "camera":
            selected = True
            camera = _refresh_camera(chart.get("cameraMove"))
            for key in ("scaleKeyPoints", "xPositionKeyPoints"):
                points = get_list(camera, key)
                if mode in ("all", "order"):
                    add_sort(camera, key)
                zero_nodes.extend(points)

        elif type == "bpmShifts":
            shifts = get_list(chart, "bpmShifts")
            indices = _refresh_range(len(shifts), startindex, endindex)
            if indices is None:
                raise _RefreshFailure
            if not indices:
                return False
            selected = True
            bpm_nodes = [shifts[index] for index in indices]
            if mode in ("all", "order"):
                add_sort(chart, "bpmShifts", indices)

        elif type == "lines":
            lines = get_list(chart, "lines")
            indices = _refresh_range(len(lines), startindex, endindex)
            if indices is None:
                raise _RefreshFailure
            if not indices:
                return False
            selected = True
            for index in indices:
                line = lines[index]
                if not isinstance(line, dict):
                    raise _RefreshFailure
                for key in (
                    "linePoints",
                    "notes",
                    "judgeRingColor",
                    "lineColor",
                ):
                    values = get_list(line, key)
                    if mode in ("all", "order"):
                        add_sort(line, key)
                    if key == "linePoints":
                        line_nodes.extend((line, node) for node in values)
                    elif key == "notes":
                        note_nodes.extend((line, node) for node in values)

        elif type in ("linePoints", "notes", "judgeRingColor", "lineColor"):
            if not _is_int(startindex) or not _is_int(endindex):
                raise _RefreshFailure
            lines = get_list(chart, "lines")
            line_indices = _refresh_range(
                len(lines),
                startlineindex,
                endlineindex,
            )
            if line_indices is None:
                raise _RefreshFailure
            if not line_indices:
                return False

            for line_index in line_indices:
                line = lines[line_index]
                if not isinstance(line, dict):
                    raise _RefreshFailure
                values = get_list(line, type)
                node_indices = _refresh_range(
                    len(values),
                    startindex,
                    endindex,
                )
                if node_indices is None:
                    raise _RefreshFailure
                if not node_indices:
                    continue
                selected = True
                if mode in ("all", "order"):
                    add_sort(line, type, node_indices)
                if type == "linePoints":
                    line_nodes.extend(
                        (line, values[index]) for index in node_indices
                    )
                elif type == "notes":
                    note_nodes.extend(
                        (line, values[index]) for index in node_indices
                    )

        elif type == "canvas":
            canvases = get_list(chart, "canvasMoves")
            indices = _refresh_range(len(canvases), startindex, endindex)
            if indices is None:
                raise _RefreshFailure
            if not indices:
                return False
            selected = True
            for index in indices:
                canvas = canvases[index]
                if not isinstance(canvas, dict):
                    raise _RefreshFailure
                x_points = get_list(canvas, "xPositionKeyPoints")
                speed_points = get_list(canvas, "speedKeyPoints")
                if mode in ("all", "order"):
                    add_sort(canvas, "xPositionKeyPoints")
                    add_sort(canvas, "speedKeyPoints")
                zero_nodes.extend(x_points)
                speed_groups.append((canvas, speed_points))

        elif type == "canvasPosition":
            if not _is_int(startindex) or not _is_int(endindex):
                raise _RefreshFailure
            canvases = get_list(chart, "canvasMoves")
            for canvas in canvases:
                if not isinstance(canvas, dict):
                    raise _RefreshFailure
                x_points = get_list(canvas, "xPositionKeyPoints")
                indices = _refresh_range(
                    len(x_points),
                    startindex,
                    endindex,
                )
                if indices is None:
                    raise _RefreshFailure
                if not indices:
                    continue
                selected = True
                if mode in ("all", "order"):
                    add_sort(canvas, "xPositionKeyPoints", indices)
                zero_nodes.extend(x_points[index] for index in indices)

        elif type == "canvasSpeed":
            if not _is_int(startindex) or not _is_int(endindex):
                raise _RefreshFailure
            canvases = get_list(chart, "canvasMoves")
            for canvas in canvases:
                if not isinstance(canvas, dict):
                    raise _RefreshFailure
                speed_points = get_list(canvas, "speedKeyPoints")
                indices = _refresh_range(
                    len(speed_points),
                    startindex,
                    endindex,
                )
                if indices is None:
                    raise _RefreshFailure
                if not indices:
                    continue
                selected = True
                if mode in ("all", "order"):
                    add_sort(canvas, "speedKeyPoints", indices)
                speed_groups.append(
                    (
                        canvas,
                        [speed_points[index] for index in indices],
                    )
                )

        elif type in ("cameraPosition", "cameraScale"):
            if not _is_int(startindex) or not _is_int(endindex):
                raise _RefreshFailure
            camera = _refresh_camera(chart.get("cameraMove"))
            key = (
                "xPositionKeyPoints"
                if type == "cameraPosition"
                else "scaleKeyPoints"
            )
            points = get_list(camera, key)
            indices = _refresh_range(len(points), startindex, endindex)
            if indices is None:
                raise _RefreshFailure
            if not indices:
                return False
            selected = True
            if mode in ("all", "order"):
                add_sort(camera, key, indices)
            zero_nodes.extend(points[index] for index in indices)

        if not selected and not targets:
            return False

        # ------------------------------------------------------------
        # 应用排序（高度尚未写入）
        # ------------------------------------------------------------
        _apply_refresh_order(targets)

        if mode == "order":
            return any(target["changed"] for target in targets)

        # ------------------------------------------------------------
        # 计算 floorPosition（只收集待写入值，失败时不落盘）
        # ------------------------------------------------------------
        if type == "all":
            plan = _make_floor_plan(chart)
            if plan is None:
                raise _RefreshFailure
            for node, expected in plan["bpmShifts"]:
                _refresh_add_floor(pending, node, expected, only_nan)
            for node, expected in plan["canvasSpeedKeyPoints"]:
                _refresh_add_floor(pending, node, expected, only_nan)
            for node, expected in plan["linePoints"]:
                _refresh_add_floor(pending, node, expected, only_nan)
            for node, expected in plan["notes"]:
                _refresh_add_floor(pending, node, expected, only_nan)
            for extra, canvas_index, expected in plan["holds"]:
                _refresh_add_hold(
                    pending,
                    extra,
                    canvas_index,
                    expected,
                    only_nan,
                )
            for node in zero_nodes:
                _refresh_add_floor(pending, node, 0.0, only_nan)
        else:
            if bpm_nodes:
                selected_bpm = [
                    node
                    for node in bpm_nodes
                    if not only_nan
                    or _is_nan(node.get("floorPosition"))
                ]
                if selected_bpm:
                    timeline = _bpm_seconds(chart)
                    if timeline is None:
                        raise _RefreshFailure
                    seconds = timeline[3]
                    index_map = {
                        id(node): index
                        for index, node in enumerate(chart["bpmShifts"])
                    }
                    for node in selected_bpm:
                        index = index_map.get(id(node))
                        if index is None:
                            raise _RefreshFailure
                        _refresh_add_floor(
                            pending,
                            node,
                            seconds[index],
                            only_nan,
                        )

            if speed_groups:
                groups = []
                for canvas, nodes in speed_groups:
                    selected_nodes = [
                        node
                        for node in nodes
                        if not only_nan
                        or _is_nan(node.get("floorPosition"))
                    ]
                    if selected_nodes:
                        groups.append((canvas, selected_nodes))
                if groups:
                    timeline = _bpm_seconds(chart)
                    if timeline is None:
                        raise _RefreshFailure
                    base_bpm, times, values, seconds = timeline

                    def seconds_at(tick: float) -> float:
                        return _seconds_at(
                            tick,
                            base_bpm,
                            times,
                            values,
                            seconds,
                        )

                    for canvas, nodes in groups:
                        key_points = _canvas_speed_points(canvas)
                        if not key_points:
                            raise _RefreshFailure
                        floors = [0.0] * len(key_points)
                        for position in range(1, len(key_points)):
                            point_value = key_points[position - 1].get(
                                "value"
                            )
                            if not _is_finite_number(point_value):
                                raise _RefreshFailure
                            floors[position] = (
                                floors[position - 1]
                                + point_value
                                * (
                                    seconds_at(
                                        key_points[position]["time"]
                                    )
                                    - seconds_at(
                                        key_points[position - 1]["time"]
                                    )
                                )
                            )
                        index_map = {
                            id(node): index
                            for index, node in enumerate(key_points)
                        }
                        for node in nodes:
                            index = index_map.get(id(node))
                            if index is None:
                                raise _RefreshFailure
                            _refresh_add_floor(
                                pending,
                                node,
                                floors[index],
                                only_nan,
                            )

            if line_nodes:
                for line, node in line_nodes:
                    if only_nan and not _is_nan(
                        node.get("floorPosition")
                    ):
                        continue
                    point_time = node.get("time")
                    canvas_index = node.get("canvasIndex")
                    if (
                        not _is_finite_number(point_time)
                        or point_time < 0
                        or not _is_int(canvas_index)
                    ):
                        raise _RefreshFailure
                    canvas = _find_canvas(chart, canvas_index)
                    if canvas is None:
                        raise _RefreshFailure
                    expected = _canvas_floor_position_at(
                        chart,
                        canvas,
                        float(point_time),
                    )
                    if expected is None:
                        raise _RefreshFailure
                    _refresh_add_floor(
                        pending,
                        node,
                        expected,
                        only_nan,
                    )

            if note_nodes:
                for line, note in note_nodes:
                    note_type = note.get("type")
                    note_time = note.get("time")
                    if (
                        not _is_int(note_type)
                        or note_type not in (0, 1, 2)
                        or not _is_finite_number(note_time)
                        or note_time < 0
                    ):
                        raise _RefreshFailure

                    extra = note.get("otherInformations")
                    need_tail = note_type == 2 and (
                        not only_nan
                        or (
                            isinstance(extra, list)
                            and len(extra) == 3
                            and _is_nan(extra[2])
                        )
                    )
                    need_head = not only_nan or _is_nan(
                        note.get("floorPosition")
                    )
                    if not need_head and not need_tail:
                        continue

                    points = get_list(line, "linePoints")
                    if need_head:
                        head = _line_note_position(
                            chart,
                            points,
                            float(note_time),
                            True,
                        )
                        if head is None:
                            raise _RefreshFailure
                        _refresh_add_floor(
                            pending,
                            note,
                            head[1],
                            only_nan,
                        )
                    if note_type == 2 and need_tail:
                        if not isinstance(extra, list) or len(extra) != 3:
                            raise _RefreshFailure
                        tail_time = extra[0]
                        if not _is_finite_number(tail_time):
                            raise _RefreshFailure
                        tail = _line_note_position(
                            chart,
                            points,
                            float(tail_time),
                            False,
                        )
                        if tail is None:
                            raise _RefreshFailure
                        _refresh_add_hold(
                            pending,
                            extra,
                            tail[0],
                            tail[1],
                            only_nan,
                        )

            for node in zero_nodes:
                _refresh_add_floor(pending, node, 0.0, only_nan)

        order_changed = any(target["changed"] for target in targets)
        floor_changed = _refresh_pending_changed(pending)
        if not order_changed and not floor_changed:
            return False

        _refresh_apply_pending(pending)
        return True

    except (
        _RefreshFailure,
        KeyError,
        TypeError,
        ValueError,
        IndexError,
        AttributeError,
    ):
        _restore_refresh_order(targets)
        return None


def _fix_bpm_shifts(chart: dict) -> None:
    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list):
        return
    for node in shifts:
        if not isinstance(node, dict):
            continue
        value = node.get("value")
        if _is_number(value) and value <= 0:
            node["value"] = 1.0
        time = node.get("time")
        if _is_number(time) and time < 0:
            node["time"] = 0.0
        ease = node.get("easeType")
        if _is_int(ease) and not 0 <= ease <= 18:
            node["easeType"] = 0 if ease < 0 else 18


def _fix_time_fields(chart: dict) -> None:
    for container, key, _ in _iter_time_slots(chart):
        if isinstance(container, dict):
            value = container.get(key)
            if _is_number(value) and value < 0:
                container[key] = 0.0
        else:
            value = container[key]
            if _is_number(value) and value < 0:
                container[key] = 0.0


def _fix_ease_fields(chart: dict) -> None:
    for container, key, _ in _iter_ease_slots(chart):
        value = container.get(key)
        if _is_int(value) and not 0 <= value <= 18:
            container[key] = 0 if value < 0 else 18


def _fix_colors(chart: dict) -> None:
    for color, _ in _iter_color_slots(chart):
        for channel in ("r", "g", "b", "a"):
            value = color.get(channel)
            if not _is_int(value):
                continue
            if value < 0:
                color[channel] = 0
            elif value > 255:
                color[channel] = 255


def _delete_invalid_notes(chart: dict) -> None:
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return
    for line in lines:
        if not isinstance(line, dict):
            continue
        notes = line.get("notes")
        if not isinstance(notes, list):
            continue
        line["notes"] = [
            note
            for note in notes
            if isinstance(note, dict)
            and note.get("type") in (0, 1, 2)
        ]


def _normalize_canvases(chart: dict) -> None:
    canvases = chart.get("canvasMoves")
    if not isinstance(canvases, list):
        return

    kept = []
    seen = set()
    for canvas in canvases:
        if not isinstance(canvas, dict):
            continue
        index = canvas.get("index")
        if not _is_int(index):
            continue
        if index in seen:
            continue
        seen.add(index)
        kept.append(canvas)

    non_negative = [c for c in kept if c["index"] >= 0]
    negative = [c for c in kept if c["index"] < 0]
    ordered = non_negative + negative

    mapping = {}
    for new_index, canvas in enumerate(ordered):
        old_index = canvas["index"]
        mapping[old_index] = new_index
        canvas["index"] = new_index
    chart["canvasMoves"] = ordered

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return
    for line in lines:
        if not isinstance(line, dict):
            continue
        points = line.get("linePoints")
        if isinstance(points, list):
            for point in points:
                if not isinstance(point, dict):
                    continue
                index = point.get("canvasIndex")
                if _is_int(index) and index in mapping:
                    point["canvasIndex"] = mapping[index]
        notes = line.get("notes")
        if not isinstance(notes, list):
            continue
        for note in notes:
            if not isinstance(note, dict):
                continue
            extra = note.get("otherInformations")
            if not isinstance(extra, list) or len(extra) != 3:
                continue
            index = _canvas_ref(extra[1])
            if index is not None and index in mapping:
                extra[1] = mapping[index]


def _validate_lines(chart: dict) -> None:
    canvases = chart.get("canvasMoves")
    if not isinstance(canvases, list):
        return
    canvas_indices = {
        canvas["index"]
        for canvas in canvases
        if isinstance(canvas, dict) and _is_int(canvas.get("index"))
    }

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return

    kept = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        points = line.get("linePoints")
        notes = line.get("notes")
        if not isinstance(points, list) or len(points) < 2:
            continue
        if not isinstance(notes, list):
            continue
        if not all(
            isinstance(point, dict)
            and _is_number(point.get("time"))
            for point in points
        ):
            continue

        first = points[0]["time"]
        last = points[-1]["time"]

        rings = line.get("judgeRingColor")
        if not isinstance(rings, list):
            rings = []
            line["judgeRingColor"] = rings
        if not rings:
            rings.append(
                {
                    "startColor": {"r": 0, "g": 0, "b": 0, "a": 0},
                    "endColor": {"r": 0, "g": 0, "b": 0, "a": 0},
                    "time": first,
                }
            )

        bad = False

        for point in points:
            if point.get("canvasIndex") not in canvas_indices:
                bad = True
                break

        if bad:
            continue

        for note in notes:
            if not isinstance(note, dict):
                bad = True
                break
            note_type = note.get("type")
            note_time = note.get("time")
            if (
                not _is_int(note_type)
                or note_type not in (0, 1, 2)
                or not _is_number(note_time)
                or note_time < first
                or note_time > last
            ):
                bad = True
                break

            extra = note.get("otherInformations")
            if isinstance(extra, list) and len(extra) == 3:
                if _canvas_ref(extra[1]) not in canvas_indices:
                    bad = True
                    break

            if note_type == 2:
                if not isinstance(extra, list) or len(extra) != 3:
                    bad = True
                    break
                tail_time = extra[0]
                if (
                    not _is_number(tail_time)
                    or tail_time < first
                    or tail_time > last
                ):
                    bad = True
                    break

        if not bad:
            kept.append(line)

    chart["lines"] = kept


def _normalize_for_load(chart: dict) -> dict | None:
    bpm = chart.get("bPM")
    if not _is_number(bpm) or bpm <= 0:
        return None

    _fix_bpm_shifts(chart)
    _fix_time_fields(chart)
    _fix_ease_fields(chart)
    _fix_colors(chart)
    _delete_invalid_notes(chart)
    _normalize_canvases(chart)
    _validate_lines(chart)

    plan = _make_floor_plan(chart)
    if plan is not None:
        _apply_floor_plan(plan)

    return chart


def new(basebpm: float, delay: int = 0, version: int = 0) -> dict:
    """新建一份空谱面。

    参数
    ----
    basebpm:
        基准 BPM。
    delay:
        谱面延迟，单位 ms。
    version:
        文件版本，通常为 0。
    """
    return {
        "fileVersion": version,
        "chartDelayMs": delay,
        "themes": _default_themes(),
        "challengeTimes": _default_challenge_times(),
        "bPM": float(basebpm),
        "bpmShifts": [
            {
                "time": 0.0,
                "value": 1.0,
                "easeType": 0,
                "floorPosition": 0.0,
            }
        ],
        "lines": [],
        "canvasMoves": [
            {
                "index": 0,
                "xPositionKeyPoints": [
                    {
                        "time": 0.0,
                        "value": 0.0,
                        "easeType": 0,
                        "floorPosition": 0.0,
                    }
                ],
                "speedKeyPoints": [
                    {
                        "time": 0.0,
                        "value": 1.0,
                        "easeType": 0,
                        "floorPosition": 0.0,
                    }
                ],
            }
        ],
        "cameraMove": {
            "scaleKeyPoints": [
                {
                    "time": 0.0,
                    "value": 1.0,
                    "easeType": 0,
                    "floorPosition": 0.0,
                }
            ],
            "xPositionKeyPoints": [
                {
                    "time": 0.0,
                    "value": 0.0,
                    "easeType": 0,
                    "floorPosition": 0.0,
                }
            ],
        },
    }


def _prepare_chart(chart: object, basebpm: float | None) -> dict | None:
    """按标准格式清洗 chart，并补齐根结构。"""
    if not isinstance(chart, dict):
        return None

    source = chart
    if "bpmShifts" not in chart and "bPMShifts" in chart:
        source = dict(chart)
        source["bpmShifts"] = source.pop("bPMShifts")

    sanitized = _sanitize(source, _ROOT)
    if not isinstance(sanitized, dict):
        return None

    if basebpm is not None:
        sanitized["bPM"] = float(basebpm)
    elif "bPM" not in sanitized:
        return None

    template = new(
        sanitized["bPM"],
        sanitized.get("chartDelayMs", 0),
        sanitized.get("fileVersion", 0),
    )
    for key, default in template.items():
        sanitized.setdefault(key, default)

    _fix_theme_counts(sanitized)

    return {key: sanitized[key] for key in _ROOT}


def load(filename: str, basebpm: float | None = None) -> dict | None:
    """读取并清洗谱面文件。

    * 深度删除标准格式之外的键，以及类型不正确的键值对；
    * 仅对根结构缺失的键使用 ``new()`` 的默认结构补齐；
    * 若缺少 ``bPM`` 且未提供 ``basebpm``，返回 ``None``。

    读取失败（文件不存在、JSON 非法、根节点不是对象）同样返回 ``None``。
    """
    try:
        with open(filename, "r", encoding="utf-8-sig") as file:
            chart = json.load(file)
    except (OSError, ValueError):
        return None

    prepared = _prepare_chart(chart, basebpm)
    if prepared is None:
        return None
    return _normalize_for_load(prepared)


def export(chartlist: dict, filename: str) -> bool:
    """把谱面原样导出为 JSON 文件。

    导出前只做结构校验，不修改传入的字典：如果谱面需要补齐默认值、
    删除非法键或调整主题数量才能符合标准格式，则返回 ``False``。
    """
    if not isinstance(chartlist, dict):
        return False
    if check(chartlist) is not None:
        return False

    prepared = _prepare_chart(chartlist, None)
    if prepared is None or prepared != chartlist:
        return False

    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                chartlist,
                file,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
    except (OSError, TypeError, ValueError):
        return False

    return True
