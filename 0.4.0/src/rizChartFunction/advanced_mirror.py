"""按指定 X 对称轴镜像引导线。"""

from __future__ import annotations

import bisect
import copy
import math

from ._exception_wrapper import install_exception_api
from ._internal import (
    _canvas_x_at,
    _is_finite_number,
    _is_int,
)
from .base import check

__all__ = ["xMirrorLine"]

_MIRROR_TYPES = {
    "Line",
    "changePartCanvas",
    "changeCanvas",
    "addCanvas",
}


def _empty_result() -> dict:
    return {
        "line": [],
        "canvas": [],
        "canvaspositionpoint": [],
    }


def _line_indices(chart: dict, indexlist: object) -> list[int] | None:
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None
    if isinstance(indexlist, int) and not isinstance(indexlist, bool):
        raw = [indexlist]
    elif isinstance(indexlist, list) and all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in indexlist
    ):
        raw = list(indexlist)
    else:
        return None

    count = len(lines)
    result = []
    for value in raw:
        index = count + value if value < 0 else value
        if not 0 <= index < count:
            return None
        result.append(index)
    return result


def _canvas_at(chart: dict, index: object) -> dict | None:
    if not _is_int(index) or index < 0:
        return None
    canvases = chart.get("canvasMoves")
    if not isinstance(canvases, list) or index >= len(canvases):
        return None
    canvas = canvases[index]
    if (
        not isinstance(canvas, dict)
        or not _is_int(canvas.get("index"))
        or canvas["index"] != index
    ):
        return None
    return canvas


def _line_runs(line: dict) -> list[tuple[int, float, float]] | None:
    points = line.get("linePoints")
    if not isinstance(points, list) or len(points) < 2:
        return None

    runs = []
    canvas_index = None
    start_time = None
    previous_time = None
    last_time = None
    for point in points:
        if not isinstance(point, dict):
            return None
        index = point.get("canvasIndex")
        point_time = point.get("time")
        if (
            not _is_int(index)
            or index < 0
            or not _is_finite_number(point_time)
            or point_time < 0
        ):
            return None
        point_time = float(point_time)
        if previous_time is not None and point_time < previous_time:
            return None

        if canvas_index is None:
            canvas_index = index
            start_time = point_time
        elif index != canvas_index:
            runs.append((canvas_index, start_time, last_time))
            canvas_index = index
            start_time = point_time

        previous_time = point_time
        last_time = point_time

    if canvas_index is not None:
        runs.append((canvas_index, start_time, last_time))
    return runs


def _canvas_times(canvas: dict) -> list[float] | None:
    key_points = canvas.get("xPositionKeyPoints")
    if not isinstance(key_points, list) or not key_points:
        return None
    times = []
    previous = None
    for point in key_points:
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        point_value = point.get("value")
        ease_type = point.get("easeType")
        if (
            not _is_finite_number(point_time)
            or point_time < 0
            or not _is_finite_number(point_value)
            or not _is_int(ease_type)
            or not 0 <= ease_type <= 18
        ):
            return None
        point_time = float(point_time)
        if previous is not None and point_time < previous:
            return None
        times.append(point_time)
        previous = point_time
    return times


def _plan_part_ranges(
    chart: dict,
    lines: list[dict],
) -> list[tuple[dict, list[dict], list[tuple[int, int, bool]]]] | None:
    plans: dict[int, dict] = {}
    for line in lines:
        runs = _line_runs(line)
        if runs is None:
            return None
        for canvas_index, start_time, end_time in runs:
            canvas = _canvas_at(chart, canvas_index)
            if canvas is None:
                return None
            times = _canvas_times(canvas)
            if times is None:
                return None

            start_index = bisect.bisect_right(times, start_time) - 1
            if start_index < 0:
                return None
            end_index = bisect.bisect_left(times, end_time)
            normal_end = end_index < len(times)
            if not normal_end:
                end_index = len(times) - 1
            if end_index < start_index:
                return None

            plan = plans.setdefault(
                canvas_index,
                {
                    "canvas": canvas,
                    "points": canvas["xPositionKeyPoints"],
                    "affected": set(),
                    "normal_ends": set(),
                },
            )
            plan["affected"].update(
                range(start_index, end_index + 1)
            )
            if normal_end:
                plan["normal_ends"].add(end_index)

    result = []
    for canvas_index in sorted(plans):
        plan = plans[canvas_index]
        affected = sorted(plan["affected"])
        groups = []
        position = 0
        while position < len(affected):
            start = affected[position]
            end = start
            position += 1
            while (
                position < len(affected)
                and affected[position] == end + 1
            ):
                end = affected[position]
                position += 1
            groups.append(
                (
                    start,
                    end,
                    end in plan["normal_ends"],
                )
            )
        result.append((plan["canvas"], plan["points"], groups))
    return result


def _preceding_time(time: float) -> float:
    if time <= 0.0:
        return 0.0
    return math.nextafter(time, 0.0)


def _following_time(time: float) -> float | None:
    result = math.nextafter(time, math.inf)
    if not math.isfinite(result):
        return None
    return result


def _mirror_canvas_ranges(
    canvas: dict,
    key_points: list[dict],
    groups: list[tuple[int, int, bool]],
    axis: float,
) -> list[list[int]] | None:
    canvas_index = canvas.get("index")
    if not _is_int(canvas_index):
        return None

    start_groups = {}
    end_groups = {}
    interior = set()
    for start, end, normal_end in groups:
        start_groups[start] = (start, end, normal_end)
        if end > start:
            end_groups[end] = (start, end, normal_end)
            interior.update(range(start + 1, end))

    touched = set()
    new_points = []
    for index, point in enumerate(key_points):
        value = point.get("value")
        point_time = point.get("time")
        ease_type = point.get("easeType")
        if (
            not _is_finite_number(value)
            or not _is_finite_number(point_time)
            or not _is_int(ease_type)
            or not 0 <= ease_type <= 18
        ):
            return None

        if index in start_groups:
            start, end, normal_end = start_groups[index]
            original_time = float(point_time)
            mirrored_value = 2.0 * axis - float(value)
            prime = copy.deepcopy(point)
            prime["time"] = original_time
            prime["value"] = mirrored_value
            prime["easeType"] = ease_type

            before = _preceding_time(original_time)
            point["time"] = before
            point["easeType"] = 0
            if before == original_time:
                prime_time = _following_time(original_time)
                if prime_time is None:
                    return None
                prime["time"] = prime_time

            new_points.append(point)
            new_points.append(prime)
            touched.add(id(point))
            touched.add(id(prime))
            continue

        if index in end_groups:
            start, end, normal_end = end_groups[index]
            if not normal_end:
                point["value"] = 2.0 * axis - float(value)
                new_points.append(point)
                touched.add(id(point))
                continue

            original_time = float(point_time)
            mirrored_value = 2.0 * axis - float(value)
            prime = copy.deepcopy(point)
            prime["time"] = original_time
            prime["value"] = mirrored_value
            prime["easeType"] = 0

            after = _following_time(original_time)
            if after is None:
                return None
            point["time"] = after

            new_points.append(prime)
            new_points.append(point)
            touched.add(id(point))
            touched.add(id(prime))
            continue

        if index in interior:
            point["value"] = 2.0 * axis - float(value)
            new_points.append(point)
            touched.add(id(point))
            continue

        new_points.append(point)

    new_points.sort(key=lambda point: point["time"])
    key_points[:] = new_points

    result = []
    for index, point in enumerate(new_points):
        if id(point) in touched:
            result.append([canvas_index, index])
    return result


def _mirror_line_copies(
    chart: dict,
    source_lines: list[dict],
    axis: float,
    mirrortype: str,
    is_absolute_axis: bool,
    canvas_mapping: dict[int, int] | None = None,
) -> list[dict] | None:
    copies = []
    for source in source_lines:
        line = copy.deepcopy(source)
        points = line.get("linePoints")
        if not isinstance(points, list) or len(points) < 2:
            return None
        for point in points:
            if not isinstance(point, dict):
                return None
            x_position = point.get("xPosition")
            point_time = point.get("time")
            canvas_index = point.get("canvasIndex")
            if (
                not _is_finite_number(x_position)
                or not _is_finite_number(point_time)
                or not _is_int(canvas_index)
            ):
                return None

            if mirrortype == "Line":
                if is_absolute_axis:
                    canvas = _canvas_at(chart, canvas_index)
                    if canvas is None:
                        return None
                    center = _canvas_x_at(canvas, float(point_time))
                    if center is None:
                        return None
                    point["xPosition"] = (
                        2.0 * axis - 2.0 * center - float(x_position)
                    )
                else:
                    point["xPosition"] = 2.0 * axis - float(x_position)
            else:
                point["xPosition"] = -float(x_position)

            if canvas_mapping is not None:
                mapped = canvas_mapping.get(canvas_index)
                if mapped is None:
                    return None
                point["canvasIndex"] = mapped

        if canvas_mapping is not None:
            notes = line.get("notes")
            if not isinstance(notes, list):
                return None
            for note in notes:
                if not isinstance(note, dict):
                    return None
                extra = note.get("otherInformations")
                if isinstance(extra, list) and len(extra) == 3:
                    old_canvas = extra[1]
                    if _is_int(old_canvas):
                        mapped = canvas_mapping.get(old_canvas)
                        if mapped is not None:
                            extra[1] = mapped
        copies.append(line)
    return copies


def _append_line_copies(
    chart: dict,
    source_indices: list[int],
    copies: list[dict],
    delete_original: bool,
) -> list[int] | None:
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None
    source_ids = {id(lines[index]) for index in source_indices}

    copy_ids = set()
    for line in copies:
        lines.append(line)
        copy_ids.add(id(line))
    if delete_original:
        lines[:] = [
            line for line in lines
            if id(line) not in source_ids
        ]
    return [
        index
        for index, line in enumerate(lines)
        if id(line) in copy_ids
    ]


def _mirror_canvas_all(canvas: dict, axis: float) -> bool:
    key_points = canvas.get("xPositionKeyPoints")
    if not isinstance(key_points, list) or not key_points:
        return False
    for point in key_points:
        if not isinstance(point, dict):
            return False
        value = point.get("value")
        if not _is_finite_number(value):
            return False
        point["value"] = 2.0 * axis - float(value)
    return True


def _apply_mirror(
    chart: dict,
    source_indices: list[int],
    axis: float,
    mirrortype: str,
    is_absolute_axis: bool,
    delete_original: bool,
) -> dict | None:
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None
    source_lines = [lines[index] for index in source_indices]
    if not all(isinstance(line, dict) for line in source_lines):
        return None

    canvasresult = []
    pointresult = []
    canvas_mapping = None

    if mirrortype == "changePartCanvas":
        plans = _plan_part_ranges(chart, source_lines)
        if plans is None:
            return None
        for canvas, key_points, groups in plans:
            touched = _mirror_canvas_ranges(
                canvas,
                key_points,
                groups,
                axis,
            )
            if touched is None:
                return None
            pointresult.extend(touched)
    elif mirrortype == "changeCanvas":
        canvas_indices = sorted(
            {
                point.get("canvasIndex")
                for line in source_lines
                for point in line.get("linePoints", [])
            }
        )
        for canvas_index in canvas_indices:
            canvas = _canvas_at(chart, canvas_index)
            if canvas is None:
                return None
            if not _mirror_canvas_all(canvas, axis):
                return None
            canvasresult.append(canvas_index)
    elif mirrortype == "addCanvas":
        old_indices = sorted(
            {
                point.get("canvasIndex")
                for line in source_lines
                for point in line.get("linePoints", [])
            }
        )
        canvases = chart.get("canvasMoves")
        if not isinstance(canvases, list):
            return None
        canvas_mapping = {}
        for old_index in old_indices:
            canvas = _canvas_at(chart, old_index)
            if canvas is None:
                return None
            new_index = len(canvases)
            new_canvas = copy.deepcopy(canvas)
            new_canvas["index"] = new_index
            if not _mirror_canvas_all(new_canvas, axis):
                return None
            canvases.append(new_canvas)
            canvas_mapping[old_index] = new_index
            canvasresult.append(new_index)

    copies = _mirror_line_copies(
        chart,
        source_lines,
        axis,
        mirrortype,
        is_absolute_axis,
        canvas_mapping,
    )
    if copies is None:
        return None
    line_result = _append_line_copies(
        chart,
        source_indices,
        copies,
        delete_original,
    )
    if line_result is None:
        return None

    pointresult.sort()
    return {
        "line": line_result,
        "canvas": canvasresult,
        "canvaspositionpoint": pointresult,
    }


def xMirrorLine(
    chart: dict,
    indexlist: int | list,
    axisposition: float,
    mirrortype: str = "Line",
    isAbsoluteAxisPosition: bool = True,
    isDeleteOriginLine: bool = True,
) -> dict | None:
    """以 x=axisposition 为对称轴镜像选中的引导线。

    ``mirrortype`` 支持 ``"Line"`` / ``"changePartCanvas"`` /
    ``"changeCanvas"`` / ``"addCanvas"``。新镜像线追加到 ``lines`` 末尾；
    ``isDeleteOriginLine=True`` 时删除原线，否则保留原线。``addCanvas``
    会复制受影响画布，并把 Hold 音符的画布引用重映射到新画布。

    成功的返回值包含最终线索引、画布索引与画布位置节点索引；失败时
    返回 ``None``。``isReturnException=True`` 时失败抛出异常。
    """
    if not isinstance(chart, dict):
        return None
    if mirrortype not in _MIRROR_TYPES:
        return None
    if not _is_finite_number(axisposition):
        return None
    if not isinstance(isAbsoluteAxisPosition, bool):
        return None
    if not isinstance(isDeleteOriginLine, bool):
        return None

    indices = _line_indices(chart, indexlist)
    if indices is None:
        return None
    if not indices:
        return _empty_result()

    if mirrortype == "changePartCanvas":
        delete_original = False
    else:
        delete_original = isDeleteOriginLine
    absolute_axis = (
        isAbsoluteAxisPosition
        if mirrortype == "Line"
        else True
    )

    fallback = copy.deepcopy(chart)
    try:
        result = _apply_mirror(
            chart,
            indices,
            float(axisposition),
            mirrortype,
            absolute_axis,
            delete_original,
        )
        if result is None or check(chart) is not None:
            raise ValueError("xMirrorLine failed")
        return result
    except Exception:
        chart.clear()
        chart.update(fallback)
        return None


install_exception_api(globals())
