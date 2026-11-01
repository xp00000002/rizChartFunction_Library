"""高级批量复制工具。

所有函数只调用 base / chart / query 暴露的公开函数，不直接修改谱面 dict。
"""

from __future__ import annotations

import copy
import math

from .base import refresh
from .chart import (
    addBpmShift,
    addCameraPosition,
    addCameraScale,
    addCanvas,
    addCanvasPosition,
    addCanvasSpeed,
    addLine,
    addLineColor,
    addLinePoint,
    addNote,
    addRingPoint,
    addRiztime,
    deleteBpmShift,
    deleteCameraPosition,
    deleteCameraScale,
    deleteCanvas,
    deleteCanvasPosition,
    deleteCanvasSpeed,
    deleteLine,
    deleteLineColor,
    deleteLinePoint,
    deleteNote,
    deleteRingPoint,
    deleteRiztime,
    setBpmShift,
    setCameraPosition,
    setCameraScale,
    setCanvasPosition,
    setCanvasSpeed,
    setLineColor,
    setLinePoint,
    setNote,
    setRingPoint,
)
from .query import (
    getBpmAt,
    getBpmShift,
    getBpmShiftCount,
    getCamera,
    getCameraPosition,
    getCameraScale,
    getCanvas,
    getCanvasCount,
    getCanvasPosition,
    getCanvasSpeed,
    getLine,
    getLineColor,
    getLineCount,
    getLinePoint,
    getNote,
    getRingPoint,
    getRiztime,
    getRiztimeCount,
)

__all__ = [
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
]


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _plain_indices(value: object) -> list[int] | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return [value]
    if isinstance(value, list) and all(
        isinstance(item, int) and not isinstance(item, bool)
        for item in value
    ):
        return list(value)
    return None


def _nested_indices(value: object) -> list[tuple[int, int]] | None:
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        return [(int(value[0]), int(value[1]))]
    if isinstance(value, list):
        result = []
        for item in value:
            if (
                not isinstance(item, (list, tuple))
                or len(item) != 2
                or any(
                    not isinstance(part, int) or isinstance(part, bool)
                    for part in item
                )
            ):
                return None
            result.append((int(item[0]), int(item[1])))
        return result
    return None


def _resolve_index(index: object, length: int) -> int | None:
    if not isinstance(index, int) or isinstance(index, bool):
        return None
    value = length + index if index < 0 else index
    if not 0 <= value < length:
        return None
    return value


def _resolve_insert(index: object, length: int) -> int | None:
    if index is None:
        return None
    if not isinstance(index, int) or isinstance(index, bool):
        return None
    value = length + index if index < 0 else index
    if not 0 <= value <= length:
        return None
    return value


def _shift_time(
    chart: dict,
    time: object,
    offsettime: float,
    isRealOffsetTime: bool,
) -> float | None:
    if not _is_finite_number(time):
        return None
    if not isRealOffsetTime or offsettime == 0.0:
        shifted = float(time) + float(offsettime)
    else:
        bpm = getBpmAt(chart, float(time))
        if bpm is None or bpm <= 0:
            return None
        shifted = float(time) + float(offsettime) * bpm / 60.0
    if not _is_finite_number(shifted) or shifted < 0:
        return None
    return float(shifted)


def _add_position(value: object, offsetposition: float) -> float | None:
    if not _is_finite_number(value):
        return None
    shifted = float(value) + float(offsetposition)
    return shifted if _is_finite_number(shifted) else None


def _shift_key_point(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float | None = None,
) -> dict | None:
    out = copy.deepcopy(spec)
    shifted_time = _shift_time(
        chart,
        out.get("time"),
        offsettime,
        isRealOffsetTime,
    )
    if shifted_time is None:
        return None
    out["time"] = shifted_time
    if offsetposition is not None:
        shifted_value = _add_position(out.get("value"), offsetposition)
        if shifted_value is None:
            return None
        out["value"] = shifted_value
    return out


def _shift_color_spec(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
) -> dict | None:
    out = copy.deepcopy(spec)
    shifted_time = _shift_time(
        chart,
        out.get("time"),
        offsettime,
        isRealOffsetTime,
    )
    if shifted_time is None:
        return None
    out["time"] = shifted_time
    return out


def _shift_line_point(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    out = copy.deepcopy(spec)
    shifted_time = _shift_time(
        chart,
        out.get("time"),
        offsettime,
        isRealOffsetTime,
    )
    shifted_x = _add_position(out.get("xPosition"), offsetposition)
    if shifted_time is None or shifted_x is None:
        return None
    out["time"] = shifted_time
    out["xPosition"] = shifted_x
    return out


def _shift_note(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
) -> dict | None:
    out = copy.deepcopy(spec)
    head = _shift_time(chart, out.get("time"), offsettime, isRealOffsetTime)
    if head is None:
        return None
    out["time"] = head
    if out.get("type") == 2:
        tail = _shift_time(
            chart,
            out.get("endtime"),
            offsettime,
            isRealOffsetTime,
        )
        if tail is None or tail <= head:
            return None
        out["endtime"] = tail
    return out


def _shift_line_spec(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    out = copy.deepcopy(spec)
    new_points = []
    for point in out.get("linePoints", []):
        shifted = _shift_line_point(
            chart,
            point,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        if shifted is None:
            return None
        new_points.append(shifted)
    new_rings = []
    for ring in out.get("judgeRingColor", []):
        shifted = _shift_color_spec(
            chart,
            ring,
            offsettime,
            isRealOffsetTime,
        )
        if shifted is None:
            return None
        new_rings.append(shifted)
    new_colors = []
    for color in out.get("lineColor", []):
        shifted = _shift_color_spec(
            chart,
            color,
            offsettime,
            isRealOffsetTime,
        )
        if shifted is None:
            return None
        new_colors.append(shifted)
    new_notes = []
    for note in out.get("notes", []):
        shifted = _shift_note(
            chart,
            note,
            offsettime,
            isRealOffsetTime,
        )
        if shifted is None:
            return None
        new_notes.append(shifted)
    out["linePoints"] = new_points
    out["judgeRingColor"] = new_rings
    out["lineColor"] = new_colors
    out["notes"] = new_notes
    return out


def _shift_canvas_spec(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float | None = None,
) -> dict | None:
    out = copy.deepcopy(spec)
    new_positions = []
    for point in out.get("xPositionKeyPoints", []):
        shifted = _shift_key_point(
            chart,
            point,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        if shifted is None:
            return None
        new_positions.append(shifted)
    new_speeds = []
    for point in out.get("speedKeyPoints", []):
        shifted = _shift_key_point(
            chart,
            point,
            offsettime,
            isRealOffsetTime,
            None,
        )
        if shifted is None:
            return None
        new_speeds.append(shifted)
    out["xPositionKeyPoints"] = new_positions
    out["speedKeyPoints"] = new_speeds
    return out


def _shift_camera_spec(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    out = copy.deepcopy(spec)
    new_positions = []
    for point in out.get("xPositionKeyPoints", []):
        shifted = _shift_key_point(
            chart,
            point,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        if shifted is None:
            return None
        new_positions.append(shifted)
    new_scales = []
    for point in out.get("scaleKeyPoints", []):
        shifted = _shift_key_point(
            chart,
            point,
            offsettime,
            isRealOffsetTime,
            None,
        )
        if shifted is None:
            return None
        new_scales.append(shifted)
    out["xPositionKeyPoints"] = new_positions
    out["scaleKeyPoints"] = new_scales
    return out


def _shift_riztime(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
) -> dict | None:
    out = copy.deepcopy(spec)
    start = _shift_time(chart, out.get("start"), offsettime, isRealOffsetTime)
    end = _shift_time(chart, out.get("end"), offsettime, isRealOffsetTime)
    if start is None or end is None or end < start:
        return None
    out["start"] = start
    out["end"] = end
    return out


def _sorted_by_time(specs: list[dict]) -> list[dict]:
    return sorted(specs, key=lambda spec: spec.get("time", 0.0))


def _unique_positions(values: list[int]) -> list[int]:
    return sorted({int(value) for value in values})


def _run_copy(
    target: dict,
    items: list[tuple[list[int], object]],
    destructive: bool,
    isFailAddAllowed: bool,
    setup=None,
    post=None,
) -> list[int]:
    """在副本上预演，确认无误后再执行实际修改。"""
    def run(chart: dict, stop_on_first: bool) -> tuple[bool, list[int]]:
        if setup is not None and not setup(chart):
            return False, []
        failures = []
        for positions, action in items:
            if action(chart):
                continue
            failures.extend(positions)
            if stop_on_first:
                break
        return not failures, failures

    if not isFailAddAllowed:
        trial = copy.deepcopy(target)
        ok, failures = run(trial, True)
        if not ok:
            return [failures[0]] if failures else [-1]
        ok, failures = run(target, False)
        if not ok:
            return [failures[0]] if failures else [-1]
        if post is not None and not post(target):
            return [-1]
        return []

    if destructive:
        trial = copy.deepcopy(target)
        ok, failures = run(trial, False)
        if failures:
            return _unique_positions(failures)
        ok, failures = run(target, False)
        if failures:
            return _unique_positions(failures)
        if post is not None and not post(target):
            return [-1]
        return []

    if setup is not None and not setup(target):
        return [-1]
    failures = []
    successes = 0
    for positions, action in items:
        trial = copy.deepcopy(target)
        if not action(trial):
            failures.extend(positions)
            continue
        if action(target):
            successes += 1
        else:
            failures.extend(positions)
    if post is not None and successes and not post(target):
        return [-1]
    return _unique_positions(failures)


def _delete_all_lines(chart: dict) -> bool:
    while True:
        count = getLineCount(chart)
        if count is None:
            return False
        if count == 0:
            return True
        if deleteLine(chart, 0) is None:
            return False


def _recreate_line(chart: dict, index: int, line_spec: dict) -> bool:
    old_spec = getLine(chart, index)
    if old_spec is None:
        return False
    if deleteLine(chart, index) is None:
        return False
    created = addLine(
        chart,
        line_spec.get("linePoints", []),
        line_spec.get("judgeRingColor", []),
        index=index,
        notes=line_spec.get("notes"),
        linecolors=line_spec.get("lineColor"),
    )
    if created is not None:
        return True
    addLine(
        chart,
        old_spec.get("linePoints", []),
        old_spec.get("judgeRingColor", []),
        index=index,
        notes=old_spec.get("notes"),
        linecolors=old_spec.get("lineColor"),
    )
    return False


def _line_target_index(chart: dict, targetindex: object) -> int | None:
    count = getLineCount(chart)
    if count is None or count <= 0:
        return None
    index = count - 1 if targetindex is None else targetindex
    return _resolve_index(index, count)


def _canvas_target_index(chart: dict, targetindex: object) -> int | None:
    count = getCanvasCount(chart)
    if count is None or count <= 0:
        return None
    index = count - 1 if targetindex is None else targetindex
    return _resolve_index(index, count)


def _plan_canvas_mapping(
    source: dict,
    target: dict,
    used: list[int],
    canvasmode: str,
    offsettime: float,
    isRealOffsetTime: bool,
) -> tuple[dict[int, int], list[tuple[int, dict]]] | None:
    if canvasmode not in ("insert", "increase", "add"):
        return None
    unique = sorted(set(used))
    for value in unique:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return None
    mapping = {}
    copies = []
    if canvasmode == "insert":
        for value in unique:
            mapping[value] = value
    elif canvasmode == "increase":
        for position, value in enumerate(unique):
            mapping[value] = position
    else:
        count = getCanvasCount(target)
        if count is None:
            return None
        for position, value in enumerate(unique):
            spec = getCanvas(source, value)
            if not isinstance(spec, dict):
                return None
            shifted = _shift_canvas_spec(
                target,
                spec,
                offsettime,
                isRealOffsetTime,
                None,
            )
            if shifted is None:
                return None
            target_index = count + position
            mapping[value] = target_index
            copies.append((target_index, shifted))
    return mapping, copies


def _canvas_setup(
    mapping: dict[int, int],
    copies: list[tuple[int, dict]],
    canvasmode: str,
):
    def setup(chart: dict) -> bool:
        if canvasmode == "add":
            for target_index, spec in copies:
                created = addCanvas(chart)
                if created != target_index:
                    return False
                if not _write_canvas_contents(chart, created, spec):
                    return False
            return True
        needed = max(mapping.values(), default=-1) + 1
        count = getCanvasCount(chart)
        if count is None:
            return False
        while count < needed:
            if addCanvas(chart) is None:
                return False
            count += 1
        return True
    return setup


def _map_line_spec(spec: dict, mapping: dict[int, int]) -> dict | None:
    out = copy.deepcopy(spec)
    for point in out.get("linePoints", []):
        canvas_index = point.get("canvasIndex")
        if canvas_index not in mapping:
            return None
        point["canvasIndex"] = mapping[canvas_index]
    return out


def _map_line_point(spec: dict, mapping: dict[int, int]) -> dict | None:
    out = copy.deepcopy(spec)
    canvas_index = out.get("canvasIndex")
    if canvas_index not in mapping:
        return None
    out["canvasIndex"] = mapping[canvas_index]
    return out


def _clear_canvas_positions(chart: dict, canvasindex: int) -> bool:
    points = getCanvasPosition(chart, canvasindex, 0, -1)
    if points is None:
        return False
    count = len(points)
    for index in range(count - 1, 0, -1):
        if deleteCanvasPosition(chart, canvasindex, index) is None:
            return False
    if count > 0 and deleteCanvasPosition(chart, canvasindex, 0) is None:
        return False
    return True


def _write_canvas_positions(
    chart: dict,
    canvasindex: int,
    points: list[dict],
    skip_time_zero: bool,
) -> bool:
    current = getCanvasPosition(chart, canvasindex, 0, -1)
    if current is None:
        return False
    skip = None
    if skip_time_zero and current:
        for index, point in enumerate(points):
            if point.get("time") == 0.0:
                skip = index
                break
    for index, point in enumerate(points):
        if index == skip:
            continue
        if addCanvasPosition(
            chart,
            canvasindex,
            point.get("time"),
            position=point.get("value"),
            easetype=point.get("easeType", 0),
        ) is None:
            return False
    if skip is not None:
        point = points[skip]
        if setCanvasPosition(
            chart,
            canvasindex,
            0,
            time=0.0,
            position=point.get("value"),
            easetype=point.get("easeType", 0),
        ) is None:
            return False
    return True


def _clear_canvas_speeds(chart: dict, canvasindex: int) -> bool:
    points = getCanvasSpeed(chart, canvasindex, 0, -1)
    if points is None:
        return False
    count = len(points)
    for index in range(count - 1, 0, -1):
        if deleteCanvasSpeed(chart, canvasindex, index) is None:
            return False
    if count > 0 and deleteCanvasSpeed(chart, canvasindex, 0) is None:
        return False
    return True


def _write_canvas_speeds(
    chart: dict,
    canvasindex: int,
    points: list[dict],
    skip_time_zero: bool,
) -> bool:
    current = getCanvasSpeed(chart, canvasindex, 0, -1)
    if current is None:
        return False
    skip = None
    if skip_time_zero and current:
        for index, point in enumerate(points):
            if point.get("time") == 0.0:
                skip = index
                break
    for index, point in enumerate(points):
        if index == skip:
            continue
        if addCanvasSpeed(
            chart,
            canvasindex,
            point.get("time"),
            speed=point.get("value"),
            isChangeZeroSpeed=False,
        ) is None:
            return False
    if skip is not None:
        point = points[skip]
        if setCanvasSpeed(
            chart,
            canvasindex,
            0,
            time=0.0,
            speed=point.get("value"),
            isChangeZeroSpeed=False,
        ) is None:
            return False
    return True


def _write_canvas_contents(chart: dict, canvasindex: int, spec: dict) -> bool:
    if not _clear_canvas_positions(chart, canvasindex):
        return False
    if not _write_canvas_positions(
        chart,
        canvasindex,
        _sorted_by_time(spec.get("xPositionKeyPoints", [])),
        True,
    ):
        return False
    if not _clear_canvas_speeds(chart, canvasindex):
        return False
    if not _write_canvas_speeds(
        chart,
        canvasindex,
        _sorted_by_time(spec.get("speedKeyPoints", [])),
        True,
    ):
        return False
    return True


def _clear_camera_positions(chart: dict) -> bool:
    points = getCameraPosition(chart, 0, -1)
    if points is None:
        return False
    count = len(points)
    for index in range(count - 1, 0, -1):
        if deleteCameraPosition(chart, index) is None:
            return False
    if count > 0 and deleteCameraPosition(chart, 0) is None:
        return False
    return True


def _write_camera_positions(
    chart: dict,
    points: list[dict],
    skip_time_zero: bool,
) -> bool:
    current = getCameraPosition(chart, 0, -1)
    if current is None:
        return False
    skip = None
    if skip_time_zero and current:
        for index, point in enumerate(points):
            if point.get("time") == 0.0:
                skip = index
                break
    for index, point in enumerate(points):
        if index == skip:
            continue
        if addCameraPosition(
            chart,
            point.get("time"),
            position=point.get("value"),
            easetype=point.get("easeType", 0),
        ) is None:
            return False
    if skip is not None:
        point = points[skip]
        if setCameraPosition(
            chart,
            0,
            time=0.0,
            position=point.get("value"),
            easetype=point.get("easeType", 0),
        ) is None:
            return False
    return True


def _clear_camera_scales(chart: dict) -> bool:
    points = getCameraScale(chart, 0, -1)
    if points is None:
        return False
    count = len(points)
    for index in range(count - 1, 0, -1):
        if deleteCameraScale(chart, index) is None:
            return False
    if count > 0 and deleteCameraScale(chart, 0) is None:
        return False
    return True


def _write_camera_scales(
    chart: dict,
    points: list[dict],
    skip_time_zero: bool,
) -> bool:
    current = getCameraScale(chart, 0, -1)
    if current is None:
        return False
    skip = None
    if skip_time_zero and current:
        for index, point in enumerate(points):
            if point.get("time") == 0.0:
                skip = index
                break
    for index, point in enumerate(points):
        if index == skip:
            continue
        if addCameraScale(
            chart,
            point.get("time"),
            scale=point.get("value"),
            easetype=point.get("easeType", 0),
        ) is None:
            return False
    if skip is not None:
        point = points[skip]
        if setCameraScale(
            chart,
            0,
            time=0.0,
            scale=point.get("value"),
            easetype=point.get("easeType", 0),
        ) is None:
            return False
    return True


def _add_bpm_spec(chart: dict, spec: dict) -> bool:
    return (
        addBpmShift(
            chart,
            spec.get("value"),
            spec.get("time"),
            isDelayCalculate=True,
            isMultiply=True,
        )
        is not None
    )


def _clear_bpm_shifts(chart: dict) -> bool:
    count = getBpmShiftCount(chart)
    if count is None:
        return False
    for index in range(count - 1, 0, -1):
        if deleteBpmShift(chart, index) is None:
            return False
    if count > 0 and deleteBpmShift(chart, 0) is None:
        return False
    return True


def _write_bpm_shifts(
    chart: dict,
    specs: list[dict],
    skip_time_zero: bool,
) -> bool:
    specs = _sorted_by_time(specs)
    current = getBpmShift(chart, 0, -1)
    if current is None:
        return False
    skip = None
    if skip_time_zero and current:
        for index, spec in enumerate(specs):
            if spec.get("time") == 0.0:
                skip = index
                break
    for index, spec in enumerate(specs):
        if index == skip:
            continue
        if not _add_bpm_spec(chart, spec):
            return False
    if skip is not None:
        spec = specs[skip]
        if setBpmShift(
            chart,
            0,
            value=spec.get("value"),
            isDelayCalculate=True,
            isMultiply=True,
        ) is None:
            return False
    return True


def _replace_bpm_shifts(chart: dict, specs: list[dict]) -> bool:
    if not _clear_bpm_shifts(chart):
        return False
    return _write_bpm_shifts(chart, specs, True)


def _delete_bpm_between(chart: dict, start: float, end: float) -> bool:
    specs = getBpmShift(chart, 0, -1)
    if specs is None:
        return False
    indices = [
        index
        for index, spec in enumerate(specs)
        if _is_finite_number(spec.get("time"))
        and start < spec["time"] < end
    ]
    for index in reversed(indices):
        if deleteBpmShift(chart, index) is None:
            return False
    return True


def _add_riztime_spec(chart: dict, spec: dict) -> bool:
    colors = spec.get("colorsList")
    if not isinstance(colors, list) or len(colors) != 3:
        return False
    return (
        addRiztime(
            chart,
            colors[0],
            colors[1],
            colors[2],
            start=spec.get("start", 0.0),
            end=spec.get("end", 0.0),
            transtime=spec.get("transTime", 0.5),
            checkpoint=spec.get("checkPoint", 0.0),
        )
        is not None
    )


def _clear_riztimes(chart: dict) -> bool:
    count = getRiztimeCount(chart)
    if count is None:
        return False
    for _ in range(count):
        if deleteRiztime(chart, 1) is None:
            return False
    return True


def _add_riztime_specs(chart: dict, specs: list[dict]) -> bool:
    for spec in sorted(specs, key=lambda value: value.get("start", 0.0)):
        if not _add_riztime_spec(chart, spec):
            return False
    return True


def _delete_riztime_part(chart: dict, start: float, end: float) -> bool:
    specs = getRiztime(chart, 0, -1)
    if specs is None:
        return False
    indices = [
        index
        for index, spec in enumerate(specs)
        if _is_finite_number(spec.get("start"))
        and _is_finite_number(spec.get("end"))
        and spec["start"] > start
        and spec["end"] < end
    ]
    for index in reversed(indices):
        if deleteRiztime(chart, index + 1) is None:
            return False
    return True


def _refresh_all(chart: dict) -> bool:
    return refresh(chart, mode="all", type="all") is not None


def _line_copy_action(
    spec: dict,
    copymode: str,
    start: int | None,
    initial_count: int,
    source_index: int,
    part_offset: int,
    fixed_index: bool,
):
    def action(chart: dict) -> bool:
        if copymode == "replace":
            index = None
        elif copymode == "part":
            target_position = source_index + part_offset
            count = getLineCount(chart)
            if count is None or target_position < 0:
                return False
            if target_position < count:
                if deleteLine(chart, target_position) is None:
                    return False
                index = target_position
            else:
                index = None
        else:
            if start is None:
                index = None
            else:
                count = getLineCount(chart)
                if count is None:
                    return False
                index = start + (count - initial_count)
        return (
            addLine(
                chart,
                spec.get("linePoints", []),
                spec.get("judgeRingColor", []),
                index=index,
                notes=spec.get("notes"),
                linecolors=spec.get("lineColor"),
            )
            is not None
        )
    return action


def copyLine(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    offsetposition: float = 0.0,
    canvasmode: str = "insert",
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一条或多条引导线。"""
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    if canvasmode not in ("insert", "increase", "add"):
        return [-1]
    indices = _plain_indices(indexlist)
    if indices is None:
        return [-1]
    if not indices:
        return []
    if copymode == "part" and (
        not isinstance(targetindex, int)
        or isinstance(targetindex, bool)
    ):
        return [-1]
    start = None
    initial_count = 0
    if copymode == "insert":
        initial_count = getLineCount(target)
        if initial_count is None:
            return [-1]
        if targetindex is not None:
            start = _resolve_insert(targetindex, initial_count)
            if start is None:
                return [-1]
    elif copymode == "part":
        initial_count = getLineCount(target)
        if initial_count is None:
            return [-1]

    entries = []
    used_canvases = []
    for position, source_index in enumerate(indices):
        spec = getLine(sourcechart, source_index)
        if not isinstance(spec, dict):
            entries.append((position, source_index, None))
            continue
        shifted = _shift_line_spec(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        if shifted is None:
            entries.append((position, source_index, None))
            continue
        valid = True
        for point in shifted.get("linePoints", []):
            canvas_index = point.get("canvasIndex")
            if (
                not isinstance(canvas_index, int)
                or isinstance(canvas_index, bool)
                or canvas_index < 0
            ):
                valid = False
                break
            used_canvases.append(canvas_index)
        if not valid:
            entries.append((position, source_index, None))
            continue
        entries.append((position, source_index, shifted))

    if not any(spec is not None for _, _, spec in entries):
        invalid = [
            position
            for position, _, spec in entries
            if spec is None
        ]
        if isFailAddAllowed:
            return _unique_positions(invalid)
        return [invalid[0]]

    plan = _plan_canvas_mapping(
        sourcechart,
        target,
        used_canvases,
        canvasmode,
        offsettime,
        isRealOffsetTime,
    )
    if plan is None:
        return [-1]
    mapping, canvas_copies = plan

    mapped_entries = []
    for position, source_index, spec in entries:
        if spec is None:
            mapped_entries.append((position, source_index, None))
            continue
        mapped = _map_line_spec(spec, mapping)
        mapped_entries.append((position, source_index, mapped))

    def setup(chart: dict) -> bool:
        if copymode == "replace" and not _delete_all_lines(chart):
            return False
        return _canvas_setup(mapping, canvas_copies, canvasmode)(chart)

    items = []
    for position, source_index, spec in mapped_entries:
        if spec is None:
            items.append(([position], lambda chart: False))
            continue
        items.append(
            (
                [position],
                _line_copy_action(
                    spec,
                    copymode,
                    start,
                    initial_count,
                    source_index,
                    targetindex if isinstance(targetindex, int) else 0,
                    False,
                ),
            )
        )
    return _run_copy(
        target,
        items,
        destructive=copymode != "insert",
        isFailAddAllowed=isFailAddAllowed,
        setup=setup,
    )


def _line_child_part_points(
    line_spec: dict,
    key: str,
    source_specs: list[dict],
) -> list[dict]:
    if not source_specs:
        return list(line_spec.get(key, []))
    times = [spec.get("time") for spec in source_specs]
    start = min(times)
    end = max(times)
    kept = [
        spec
        for spec in line_spec.get(key, [])
        if not (
            _is_finite_number(spec.get("time"))
            and start < spec["time"] < end
        )
    ]
    combined = kept + source_specs
    return _sorted_by_time(combined)


def _line_child_copy(
    sourcechart: dict,
    indexlist: object,
    targetchart: dict | None,
    targetindex: int | None,
    copymode: str,
    offsettime: float,
    offsetposition: float,
    isRealOffsetTime: bool,
    isFailAddAllowed: bool,
    child: str,
    getter,
    shifter,
    adder,
) -> list[int]:
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    pairs = _nested_indices(indexlist)
    if pairs is None:
        return [-1]
    if not pairs:
        return []
    target_line = _line_target_index(target, targetindex)
    if target_line is None:
        return [-1]

    entries = []
    for position, (line_index, child_index) in enumerate(pairs):
        spec = getter(sourcechart, line_index, child_index)
        if not isinstance(spec, dict):
            entries.append((position, None))
            continue
        shifted = shifter(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        entries.append((position, shifted))

    if copymode == "insert":
        items = []
        valid_specs = [spec for _, spec in entries if spec is not None]
        for position, spec in entries:
            if spec is None:
                items.append(([position], lambda chart: False))
                continue
            items.append(
                (
                    [position],
                    lambda chart, value=spec: adder(
                        chart,
                        target_line,
                        value,
                    ),
                )
            )
        return _run_copy(
            target,
            items,
            destructive=False,
            isFailAddAllowed=isFailAddAllowed,
        )

    valid_specs = [spec for _, spec in entries if spec is not None]
    positions = [position for position, _ in entries]
    invalid_positions = [position for position, spec in entries if spec is None]
    if invalid_positions:
        if isFailAddAllowed:
            return _unique_positions(invalid_positions)
        return [invalid_positions[0]]
    if not valid_specs:
        return [positions[0]] if positions else [-1]

    def action(chart: dict) -> bool:
        line_spec = getLine(chart, target_line)
        if not isinstance(line_spec, dict):
            return False
        new_spec = copy.deepcopy(line_spec)
        if copymode == "replace":
            new_spec[child] = _sorted_by_time(valid_specs)
        else:
            new_spec[child] = _line_child_part_points(
                line_spec,
                child,
                valid_specs,
            )
        return _recreate_line(chart, target_line, new_spec)

    return _run_copy(
        target,
        [(positions, action)],
        destructive=True,
        isFailAddAllowed=isFailAddAllowed,
    )


def _line_point_adder(chart: dict, lineindex: int, spec: dict) -> bool:
    return (
        addLinePoint(
            chart,
            spec.get("time"),
            spec.get("xPosition"),
            spec.get("canvasIndex"),
            spec.get("easeType", 0),
            spec.get("color"),
            lineindex=lineindex,
        )
        is not None
    )


def _line_point_shifter(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    return _shift_line_point(
        chart,
        spec,
        offsettime,
        isRealOffsetTime,
        offsetposition,
    )


def copyLinePoint(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    offsetposition: float = 0.0,
    canvasmode: str = "insert",
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一条或多条线节点。"""
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    if canvasmode not in ("insert", "increase", "add"):
        return [-1]
    pairs = _nested_indices(indexlist)
    if pairs is None:
        return [-1]
    if not pairs:
        return []
    target_line = _line_target_index(target, targetindex)
    if target_line is None:
        return [-1]

    entries = []
    used_canvases = []
    for position, (line_index, point_index) in enumerate(pairs):
        spec = getLinePoint(sourcechart, line_index, point_index)
        if not isinstance(spec, dict):
            entries.append((position, None))
            continue
        shifted = _line_point_shifter(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        if shifted is None:
            entries.append((position, None))
            continue
        canvas_index = shifted.get("canvasIndex")
        if (
            not isinstance(canvas_index, int)
            or isinstance(canvas_index, bool)
            or canvas_index < 0
        ):
            entries.append((position, None))
            continue
        used_canvases.append(canvas_index)
        entries.append((position, shifted))

    if not any(spec is not None for _, spec in entries):
        invalid = [position for position, spec in entries if spec is None]
        if isFailAddAllowed:
            return _unique_positions(invalid)
        return [invalid[0]]

    plan = _plan_canvas_mapping(
        sourcechart,
        target,
        used_canvases,
        canvasmode,
        offsettime,
        isRealOffsetTime,
    )
    if plan is None:
        return [-1]
    mapping, canvas_copies = plan
    mapped = []
    for position, spec in entries:
        if spec is None:
            mapped.append((position, None))
        else:
            mapped.append((position, _map_line_point(spec, mapping)))

    setup = _canvas_setup(mapping, canvas_copies, canvasmode)

    if copymode == "insert":
        items = []
        valid = [spec for _, spec in mapped if spec is not None]
        for position, spec in mapped:
            if spec is None:
                items.append(([position], lambda chart: False))
                continue
            items.append(
                (
                    [position],
                    lambda chart, value=spec: _line_point_adder(
                        chart,
                        target_line,
                        value,
                    ),
                )
            )
        return _run_copy(
            target,
            items,
            destructive=False,
            isFailAddAllowed=isFailAddAllowed,
            setup=setup,
        )

    positions = [position for position, _ in mapped]
    valid = [spec for _, spec in mapped if spec is not None]
    invalid_positions = [position for position, spec in mapped if spec is None]
    if invalid_positions:
        if isFailAddAllowed:
            return _unique_positions(invalid_positions)
        return [invalid_positions[0]]
    if not valid:
        return [positions[0]] if positions else [-1]

    def action(chart: dict) -> bool:
        line_spec = getLine(chart, target_line)
        if not isinstance(line_spec, dict):
            return False
        if len(valid) < 2 and copymode == "replace":
            return False
        new_spec = copy.deepcopy(line_spec)
        if copymode == "replace":
            points = _sorted_by_time(valid)
        else:
            times = [spec.get("time") for spec in valid]
            start = min(times)
            end = max(times)
            kept = [
                spec
                for spec in line_spec.get("linePoints", [])
                if not (
                    _is_finite_number(spec.get("time"))
                    and start < spec["time"] < end
                )
            ]
            points = _sorted_by_time(kept + valid)
        if len(points) < 2:
            return False
        new_spec["linePoints"] = points
        return _recreate_line(chart, target_line, new_spec)

    return _run_copy(
        target,
        [(positions, action)],
        destructive=True,
        isFailAddAllowed=isFailAddAllowed,
        setup=setup,
    )


def _ring_adder(chart: dict, lineindex: int, spec: dict) -> bool:
    return (
        addRingPoint(
            chart,
            lineindex,
            spec.get("time"),
            spec.get("startColor"),
            spec.get("endColor"),
        )
        is not None
    )


def _color_adder(chart: dict, lineindex: int, spec: dict) -> bool:
    return (
        addLineColor(
            chart,
            lineindex,
            spec.get("time"),
            spec.get("startColor"),
            spec.get("endColor"),
        )
        is not None
    )


def _note_adder(chart: dict, lineindex: int, spec: dict) -> bool:
    return (
        addNote(
            chart,
            lineindex,
            spec.get("time"),
            spec.get("type"),
            spec.get("endtime", 0.0),
        )
        is not None
    )


def _ring_shifter(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    return _shift_color_spec(chart, spec, offsettime, isRealOffsetTime)


def _note_shifter(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    return _shift_note(chart, spec, offsettime, isRealOffsetTime)


def _line_color_shifter(
    chart: dict,
    spec: dict,
    offsettime: float,
    isRealOffsetTime: bool,
    offsetposition: float,
) -> dict | None:
    return _shift_color_spec(chart, spec, offsettime, isRealOffsetTime)


def copyRingPoint(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个判定环颜色节点。"""
    return _line_child_copy(
        sourcechart,
        indexlist,
        targetchart,
        targetindex,
        copymode,
        offsettime,
        0.0,
        isRealOffsetTime,
        isFailAddAllowed,
        "judgeRingColor",
        getRingPoint,
        _ring_shifter,
        _ring_adder,
    )


def copyNote(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个 Note。"""
    return _line_child_copy(
        sourcechart,
        indexlist,
        targetchart,
        targetindex,
        copymode,
        offsettime,
        0.0,
        isRealOffsetTime,
        isFailAddAllowed,
        "notes",
        getNote,
        _note_shifter,
        _note_adder,
    )


def copyLineColor(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个线色覆盖节点。"""
    return _line_child_copy(
        sourcechart,
        indexlist,
        targetchart,
        targetindex,
        copymode,
        offsettime,
        0.0,
        isRealOffsetTime,
        isFailAddAllowed,
        "lineColor",
        getLineColor,
        _line_color_shifter,
        _color_adder,
    )


def copyBpmShift(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个 BPM 变化节点。"""
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    indices = _plain_indices(indexlist)
    if indices is None:
        return [-1]
    if not indices:
        return []

    entries = []
    for position, source_index in enumerate(indices):
        spec = getBpmShift(sourcechart, source_index)
        if not isinstance(spec, dict):
            entries.append((position, None))
            continue
        shifted = _shift_key_point(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            None,
        )
        entries.append((position, shifted))

    if copymode == "insert":
        items = []
        for position, spec in entries:
            if spec is None:
                items.append(([position], lambda chart: False))
                continue
            items.append(
                (
                    [position],
                    lambda chart, value=spec: _add_bpm_spec(chart, value),
                )
            )
        return _run_copy(
            target,
            items,
            destructive=False,
            isFailAddAllowed=isFailAddAllowed,
            post=_refresh_all,
        )

    positions = [position for position, _ in entries]
    valid = [spec for _, spec in entries if spec is not None]
    invalid_positions = [position for position, spec in entries if spec is None]
    if invalid_positions:
        if isFailAddAllowed:
            return _unique_positions(invalid_positions)
        return [invalid_positions[0]]
    if not valid:
        return [positions[0]] if positions else [-1]

    if copymode == "replace":
        def action(chart: dict) -> bool:
            return _replace_bpm_shifts(chart, valid)
    else:
        times = [spec.get("time") for spec in valid]
        start = min(times)
        end = max(times)

        def action(chart: dict) -> bool:
            if not _delete_bpm_between(chart, start, end):
                return False
            return _write_bpm_shifts(chart, valid, False)

    return _run_copy(
        target,
        [(positions, action)],
        destructive=True,
        isFailAddAllowed=isFailAddAllowed,
        post=_refresh_all,
    )


def copyRiztime(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个 Riztime；indexlist 使用从 1 开始的索引。"""
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    indices = _plain_indices(indexlist)
    if indices is None:
        return [-1]
    if not indices:
        return []

    entries = []
    for position, source_index in enumerate(indices):
        if source_index == 0:
            entries.append((position, None))
            continue
        query_index = source_index - 1 if source_index > 0 else source_index
        spec = getRiztime(sourcechart, query_index)
        if not isinstance(spec, dict):
            entries.append((position, None))
            continue
        shifted = _shift_riztime(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
        )
        entries.append((position, shifted))

    if copymode == "insert":
        items = []
        for position, spec in entries:
            if spec is None:
                items.append(([position], lambda chart: False))
                continue
            items.append(
                (
                    [position],
                    lambda chart, value=spec: _add_riztime_spec(chart, value),
                )
            )
        return _run_copy(
            target,
            items,
            destructive=False,
            isFailAddAllowed=isFailAddAllowed,
        )

    positions = [position for position, _ in entries]
    valid = [spec for _, spec in entries if spec is not None]
    invalid_positions = [position for position, spec in entries if spec is None]
    if invalid_positions:
        if isFailAddAllowed:
            return _unique_positions(invalid_positions)
        return [invalid_positions[0]]
    if not valid:
        return [positions[0]] if positions else [-1]

    if copymode == "replace":
        def action(chart: dict) -> bool:
            if not _clear_riztimes(chart):
                return False
            return _add_riztime_specs(chart, valid)
    else:
        start = min(spec.get("start") for spec in valid)
        end = max(spec.get("end") for spec in valid)

        def action(chart: dict) -> bool:
            if not _delete_riztime_part(chart, start, end):
                return False
            return _add_riztime_specs(chart, valid)

    return _run_copy(
        target,
        [(positions, action)],
        destructive=True,
        isFailAddAllowed=isFailAddAllowed,
    )


def _canvas_copy_action(
    spec: dict,
    copymode: str,
    start: int | None,
    initial_count: int,
    source_index: int,
    part_offset: int,
):
    def action(chart: dict) -> bool:
        if copymode == "insert":
            if start is None:
                target_index = None
            else:
                count = getCanvasCount(chart)
                if count is None:
                    return False
                target_index = start + (count - initial_count)
            created = addCanvas(chart, target_index)
        else:
            target_position = source_index + part_offset
            count = getCanvasCount(chart)
            if count is None or target_position < 0:
                return False
            if target_position < count:
                created = target_position
            else:
                created = addCanvas(chart)
        if created is None:
            return False
        return _write_canvas_contents(chart, created, spec)
    return action


def copyCanvas(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    offsetposition: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个画布；不支持 copymode="replace"。"""
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "part"):
        return [-1]
    indices = _plain_indices(indexlist)
    if indices is None:
        return [-1]
    if not indices:
        return []
    if copymode == "part" and (
        not isinstance(targetindex, int)
        or isinstance(targetindex, bool)
    ):
        return [-1]
    initial_count = getCanvasCount(target)
    if initial_count is None:
        return [-1]
    start = None
    if copymode == "insert" and targetindex is not None:
        start = _resolve_insert(targetindex, initial_count)
        if start is None:
            return [-1]

    entries = []
    for position, source_index in enumerate(indices):
        spec = getCanvas(sourcechart, source_index)
        if not isinstance(spec, dict):
            entries.append((position, source_index, None))
            continue
        shifted = _shift_canvas_spec(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        entries.append((position, source_index, shifted))

    items = []
    for position, source_index, spec in entries:
        if spec is None:
            items.append(([position], lambda chart: False))
            continue
        items.append(
            (
                [position],
                _canvas_copy_action(
                    spec,
                    copymode,
                    start,
                    initial_count,
                    source_index,
                    targetindex if isinstance(targetindex, int) else 0,
                ),
            )
        )
    return _run_copy(
        target,
        items,
        destructive=copymode == "part",
        isFailAddAllowed=isFailAddAllowed,
    )


def _canvas_position_adder(chart: dict, parent: int, spec: dict) -> bool:
    return (
        addCanvasPosition(
            chart,
            parent,
            spec.get("time"),
            position=spec.get("value"),
            easetype=spec.get("easeType", 0),
        )
        is not None
    )


def _canvas_speed_adder(chart: dict, parent: int, spec: dict) -> bool:
    return (
        addCanvasSpeed(
            chart,
            parent,
            spec.get("time"),
            speed=spec.get("value"),
            isChangeZeroSpeed=False,
        )
        is not None
    )


def _delete_canvas_positions_between(
    chart: dict,
    canvasindex: int,
    start: float,
    end: float,
) -> bool:
    points = getCanvasPosition(chart, canvasindex, 0, -1)
    if points is None:
        return False
    indices = [
        index
        for index, point in enumerate(points)
        if _is_finite_number(point.get("time"))
        and start < point["time"] < end
    ]
    for index in reversed(indices):
        if deleteCanvasPosition(chart, canvasindex, index) is None:
            return False
    return True


def _delete_canvas_speeds_between(
    chart: dict,
    canvasindex: int,
    start: float,
    end: float,
) -> bool:
    points = getCanvasSpeed(chart, canvasindex, 0, -1)
    if points is None:
        return False
    indices = [
        index
        for index, point in enumerate(points)
        if _is_finite_number(point.get("time"))
        and start < point["time"] < end
    ]
    for index in reversed(indices):
        if deleteCanvasSpeed(chart, canvasindex, index) is None:
            return False
    return True


def _canvas_child_copy(
    sourcechart: dict,
    indexlist: object,
    targetchart: dict | None,
    targetindex: int | None,
    copymode: str,
    offsettime: float,
    offsetposition: float,
    isRealOffsetTime: bool,
    isFailAddAllowed: bool,
    getter,
    shifter,
    adder,
    clear,
    write,
    delete_between,
) -> list[int]:
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    pairs = _nested_indices(indexlist)
    if pairs is None:
        return [-1]
    if not pairs:
        return []
    target_canvas = _canvas_target_index(target, targetindex)
    if target_canvas is None:
        return [-1]

    entries = []
    for position, (canvas_index, point_index) in enumerate(pairs):
        spec = getter(sourcechart, canvas_index, point_index)
        if not isinstance(spec, dict):
            entries.append((position, None))
            continue
        shifted = shifter(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        entries.append((position, shifted))

    if copymode == "insert":
        items = []
        for position, spec in entries:
            if spec is None:
                items.append(([position], lambda chart: False))
                continue
            items.append(
                (
                    [position],
                    lambda chart, value=spec: adder(
                        chart,
                        target_canvas,
                        value,
                    ),
                )
            )
        return _run_copy(
            target,
            items,
            destructive=False,
            isFailAddAllowed=isFailAddAllowed,
        )

    positions = [position for position, _ in entries]
    valid = [spec for _, spec in entries if spec is not None]
    invalid_positions = [position for position, spec in entries if spec is None]
    if invalid_positions:
        if isFailAddAllowed:
            return _unique_positions(invalid_positions)
        return [invalid_positions[0]]
    if not valid:
        return [positions[0]] if positions else [-1]
    valid = _sorted_by_time(valid)

    if copymode == "replace":
        def action(chart: dict) -> bool:
            if not clear(chart, target_canvas):
                return False
            return write(chart, target_canvas, valid, True)
    else:
        start = min(spec.get("time") for spec in valid)
        end = max(spec.get("time") for spec in valid)

        def action(chart: dict) -> bool:
            if not delete_between(chart, target_canvas, start, end):
                return False
            return write(chart, target_canvas, valid, False)

    return _run_copy(
        target,
        [(positions, action)],
        destructive=True,
        isFailAddAllowed=isFailAddAllowed,
    )


def copyCanvasPosition(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    offsetposition: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个画布横向移动关键点。"""
    return _canvas_child_copy(
        sourcechart,
        indexlist,
        targetchart,
        targetindex,
        copymode,
        offsettime,
        offsetposition,
        isRealOffsetTime,
        isFailAddAllowed,
        getCanvasPosition,
        _shift_key_point,
        _canvas_position_adder,
        _clear_canvas_positions,
        _write_canvas_positions,
        _delete_canvas_positions_between,
    )


def copyCanvasSpeed(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    targetindex: int | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个画布流速关键点。"""
    return _canvas_child_copy(
        sourcechart,
        indexlist,
        targetchart,
        targetindex,
        copymode,
        offsettime,
        0.0,
        isRealOffsetTime,
        isFailAddAllowed,
        getCanvasSpeed,
        _shift_key_point,
        _canvas_speed_adder,
        _clear_canvas_speeds,
        _write_canvas_speeds,
        _delete_canvas_speeds_between,
    )


def _camera_position_adder(chart: dict, spec: dict) -> bool:
    return (
        addCameraPosition(
            chart,
            spec.get("time"),
            position=spec.get("value"),
            easetype=spec.get("easeType", 0),
        )
        is not None
    )


def _camera_scale_adder(chart: dict, spec: dict) -> bool:
    return (
        addCameraScale(
            chart,
            spec.get("time"),
            scale=spec.get("value"),
            easetype=spec.get("easeType", 0),
        )
        is not None
    )


def _delete_camera_positions_between(
    chart: dict,
    start: float,
    end: float,
) -> bool:
    points = getCameraPosition(chart, 0, -1)
    if points is None:
        return False
    indices = [
        index
        for index, point in enumerate(points)
        if _is_finite_number(point.get("time"))
        and start < point["time"] < end
    ]
    for index in reversed(indices):
        if deleteCameraPosition(chart, index) is None:
            return False
    return True


def _delete_camera_scales_between(
    chart: dict,
    start: float,
    end: float,
) -> bool:
    points = getCameraScale(chart, 0, -1)
    if points is None:
        return False
    indices = [
        index
        for index, point in enumerate(points)
        if _is_finite_number(point.get("time"))
        and start < point["time"] < end
    ]
    for index in reversed(indices):
        if deleteCameraScale(chart, index) is None:
            return False
    return True


def _camera_array_copy(
    sourcechart: dict,
    indexlist: object,
    targetchart: dict | None,
    copymode: str,
    offsettime: float,
    offsetposition: float,
    isRealOffsetTime: bool,
    isFailAddAllowed: bool,
    getter,
    shifter,
    adder,
    clear,
    write,
    delete_between,
) -> list[int]:
    if not isinstance(sourcechart, dict):
        return [-1]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [-1]
    if copymode not in ("insert", "replace", "part"):
        return [-1]
    indices = _plain_indices(indexlist)
    if indices is None:
        return [-1]
    if not indices:
        return []

    entries = []
    for position, index in enumerate(indices):
        spec = getter(sourcechart, index)
        if not isinstance(spec, dict):
            entries.append((position, None))
            continue
        shifted = shifter(
            target,
            spec,
            offsettime,
            isRealOffsetTime,
            offsetposition,
        )
        entries.append((position, shifted))

    if copymode == "insert":
        items = []
        for position, spec in entries:
            if spec is None:
                items.append(([position], lambda chart: False))
                continue
            items.append(
                (
                    [position],
                    lambda chart, value=spec: adder(chart, value),
                )
            )
        return _run_copy(
            target,
            items,
            destructive=False,
            isFailAddAllowed=isFailAddAllowed,
        )

    positions = [position for position, _ in entries]
    valid = [spec for _, spec in entries if spec is not None]
    invalid_positions = [position for position, spec in entries if spec is None]
    if invalid_positions:
        if isFailAddAllowed:
            return _unique_positions(invalid_positions)
        return [invalid_positions[0]]
    if not valid:
        return [positions[0]] if positions else [-1]
    valid = _sorted_by_time(valid)

    if copymode == "replace":
        def action(chart: dict) -> bool:
            if not clear(chart):
                return False
            return write(chart, valid, True)
    else:
        start = min(spec.get("time") for spec in valid)
        end = max(spec.get("time") for spec in valid)

        def action(chart: dict) -> bool:
            if not delete_between(chart, start, end):
                return False
            return write(chart, valid, False)

    return _run_copy(
        target,
        [(positions, action)],
        destructive=True,
        isFailAddAllowed=isFailAddAllowed,
    )


def copyCameraPosition(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    offsetposition: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个摄像机横向移动关键点。"""
    return _camera_array_copy(
        sourcechart,
        indexlist,
        targetchart,
        copymode,
        offsettime,
        offsetposition,
        isRealOffsetTime,
        isFailAddAllowed,
        getCameraPosition,
        _shift_key_point,
        _camera_position_adder,
        _clear_camera_positions,
        _write_camera_positions,
        _delete_camera_positions_between,
    )


def copyCameraScale(
    sourcechart: dict,
    indexlist: int | list,
    targetchart: dict | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制一个或多个摄像机缩放关键点。"""
    return _camera_array_copy(
        sourcechart,
        indexlist,
        targetchart,
        copymode,
        offsettime,
        0.0,
        isRealOffsetTime,
        isFailAddAllowed,
        getCameraScale,
        _shift_key_point,
        _camera_scale_adder,
        _clear_camera_scales,
        _write_camera_scales,
        _delete_camera_scales_between,
    )


def copyCamera(
    sourcechart: dict,
    targetchart: dict | None = None,
    copymode: str = "insert",
    offsettime: float = 0.0,
    offsetposition: float = 0.0,
    isRealOffsetTime: bool = False,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """复制整个摄像机；不支持 copymode="part"。"""
    if not isinstance(sourcechart, dict):
        return [0]
    target = sourcechart if targetchart is None else targetchart
    if not isinstance(target, dict):
        return [0]
    if copymode not in ("insert", "replace"):
        return [0]
    spec = getCamera(sourcechart)
    if not isinstance(spec, dict):
        return [0]
    shifted = _shift_camera_spec(
        target,
        spec,
        offsettime,
        isRealOffsetTime,
        offsetposition,
    )
    if shifted is None:
        return [0]

    def action(chart: dict) -> bool:
        if copymode == "insert":
            for point in _sorted_by_time(shifted.get("xPositionKeyPoints", [])):
                if not _camera_position_adder(chart, point):
                    return False
            for point in _sorted_by_time(shifted.get("scaleKeyPoints", [])):
                if not _camera_scale_adder(chart, point):
                    return False
            return True
        if not _clear_camera_positions(chart):
            return False
        if not _write_camera_positions(
            chart,
            _sorted_by_time(shifted.get("xPositionKeyPoints", [])),
            True,
        ):
            return False
        if not _clear_camera_scales(chart):
            return False
        if not _write_camera_scales(
            chart,
            _sorted_by_time(shifted.get("scaleKeyPoints", [])),
            True,
        ):
            return False
        return True

    return _run_copy(
        target,
        [([0], action)],
        destructive=copymode == "replace",
        isFailAddAllowed=False,
    )
