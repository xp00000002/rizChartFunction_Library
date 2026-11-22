"""内部共享工具。

本模块只依赖标准库，供 base.py / chart.py / query.py 共同使用。
不要把公开 API 或依赖其他模块的逻辑放到这里，避免循环导入。
"""

from __future__ import annotations

import bisect
import math
import re

_HEX_COLOR = re.compile(r"#?([0-9a-fA-F]{6})([0-9a-fA-F]{2})?")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    return _is_number(value) and math.isfinite(value)


def _canvas_ref(value: object) -> int | None:
    if _is_int(value):
        return value
    if (
        isinstance(value, float)
        and math.isfinite(value)
        and value.is_integer()
    ):
        return int(value)
    return None


def _parse_color(value: object) -> dict | None:
    if isinstance(value, str):
        match = _HEX_COLOR.fullmatch(value)
        if match is None:
            return None
        rgb_hex = match.group(1)
        alpha_hex = match.group(2)
        return {
            "r": int(rgb_hex[0:2], 16),
            "g": int(rgb_hex[2:4], 16),
            "b": int(rgb_hex[4:6], 16),
            "a": int(alpha_hex, 16) if alpha_hex is not None else 255,
        }

    if isinstance(value, list):
        if len(value) not in (3, 4):
            return None
        if not all(_is_int(channel) and 0 <= channel <= 255 for channel in value):
            return None
        return {
            "r": value[0],
            "g": value[1],
            "b": value[2],
            "a": value[3] if len(value) == 4 else 255,
        }

    if isinstance(value, dict):
        channels = ("r", "g", "b", "a")
        if not all(
            _is_int(value.get(channel)) and 0 <= value[channel] <= 255
            for channel in channels
        ):
            return None
        return {
            "r": value["r"],
            "g": value["g"],
            "b": value["b"],
            "a": value["a"],
        }

    return None


def _round_color_channel(value: float) -> int:
    return int(math.floor(value + 0.5))


def _ease(ease_type: object, t: float) -> float | None:
    """计算缓动函数值；``ease_type`` 非法时返回 ``None``。"""
    if not _is_int(ease_type) or not 0 <= ease_type <= 18:
        return None

    if t <= 0.0:
        u = 0.0
    elif t >= 1.0:
        u = 1.0
    else:
        u = float(t)

    if ease_type == 0:
        return u
    if ease_type == 1:
        return u * u
    if ease_type == 2:
        return 1.0 - (1.0 - u) ** 2
    if ease_type == 3:
        return (
            2.0 * u * u
            if u < 0.5
            else 1.0 - 2.0 * (1.0 - u) ** 2
        )
    if ease_type == 4:
        return u ** 3
    if ease_type == 5:
        return 1.0 - (1.0 - u) ** 3
    if ease_type == 6:
        return (
            4.0 * u ** 3
            if u < 0.5
            else 1.0 - 4.0 * (1.0 - u) ** 3
        )
    if ease_type == 7:
        return u ** 4
    if ease_type == 8:
        return 1.0 - (1.0 - u) ** 4
    if ease_type == 9:
        return (
            8.0 * u ** 4
            if u < 0.5
            else 1.0 - 8.0 * (1.0 - u) ** 4
        )
    if ease_type == 10:
        return u ** 5
    if ease_type == 11:
        return 1.0 - (1.0 - u) ** 5
    if ease_type == 12:
        return (
            16.0 * u ** 5
            if u < 0.5
            else 1.0 - 16.0 * (1.0 - u) ** 5
        )
    if ease_type == 13:
        return 0.0
    if ease_type == 14:
        return 1.0
    if ease_type == 15:
        return 1.0 - math.sqrt(1.0 - u * u)
    if ease_type == 16:
        return math.sqrt(1.0 - (1.0 - u) ** 2)
    if ease_type == 17:
        return math.sin(math.pi * u / 2.0)
    return 1.0 - math.cos(math.pi * u / 2.0)


def _canvas_x_at(canvas: dict, tick: float) -> float | None:
    """计算画布在指定 tick 的中线 x 坐标。"""
    key_points = canvas.get("xPositionKeyPoints")
    if not isinstance(key_points, list) or not key_points:
        return None

    times = []
    values = []
    for key_point in key_points:
        if not isinstance(key_point, dict):
            return None
        key_time = key_point.get("time")
        key_value = key_point.get("value")
        if (
            not _is_finite_number(key_time)
            or key_time < 0
            or not _is_finite_number(key_value)
        ):
            return None
        if times and key_time < times[-1]:
            return None
        times.append(key_time)
        values.append(key_value)

    if tick < times[0]:
        return None
    if tick >= times[-1]:
        return float(values[-1])

    position = bisect.bisect_right(times, tick) - 1
    if times[position] == tick:
        return float(values[position])

    start = times[position]
    end = times[position + 1]
    ratio = (tick - start) / (end - start)
    eased = _ease(key_points[position].get("easeType"), ratio)
    if eased is None:
        return None
    return float(
        values[position] + (values[position + 1] - values[position]) * eased
    )


def _seconds_to_tick(
    seconds: float,
    base_bpm: float,
    times: list,
    values: list,
    floor_positions: list,
) -> float | None:
    for position in range(len(times)):
        start_floor_position = floor_positions[position]
        if position + 1 < len(times):
            if seconds < floor_positions[position + 1]:
                return (
                    times[position]
                    + (seconds - start_floor_position)
                    * base_bpm
                    * values[position]
                    / 60.0
                )
        else:
            return (
                times[position]
                + (seconds - start_floor_position)
                * base_bpm
                * values[position]
                / 60.0
            )
    return None


def _bpm_seconds(
    chart: dict,
) -> tuple[float, list, list, list] | None:
    """按谱面的 BPM 时间轴计算每个节点的绝对秒数。

    谱面必须在 ``time=0.0`` 处有一个 BPM 节点；否则无法确定 tick 0
    的起始状态，返回 ``None``。节点时间按非递减校验；相同时间允许，
    该 tick 及之后以最右侧节点为准。
    """
    base_bpm = chart.get("bPM")
    if not _is_finite_number(base_bpm) or base_bpm <= 0:
        return None

    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list) or not shifts:
        return None

    times = []
    values = []
    for node in shifts:
        if not isinstance(node, dict):
            return None
        node_time = node.get("time")
        node_value = node.get("value")
        if (
            not _is_finite_number(node_time)
            or not _is_finite_number(node_value)
            or node_time < 0
            or node_value <= 0
        ):
            return None
        if times and node_time < times[-1]:
            return None
        times.append(node_time)
        values.append(node_value)

    if times[0] != 0:
        return None

    seconds = [0.0] * len(times)
    for position in range(1, len(times)):
        seconds[position] = (
            seconds[position - 1]
            + (times[position] - times[position - 1])
            * 60.0
            / (base_bpm * values[position - 1])
        )

    return float(base_bpm), times, values, seconds


def _seconds_at(
    tick: float,
    base_bpm: float,
    times: list,
    values: list,
    seconds: list,
) -> float:
    """BPM 时间轴上 tick 对应的绝对秒数。"""
    position = bisect.bisect_right(times, tick) - 1
    return (
        seconds[position]
        + (tick - times[position]) * 60.0 / (base_bpm * values[position])
    )


def _find_canvas(chart: object, index: object) -> dict | None:
    """按索引查找画布；负数从末尾计算，要求画布索引连续。"""
    if not isinstance(chart, dict) or not _is_int(index):
        return None

    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return None

    position = index + len(canvas_moves) if index < 0 else index
    if not 0 <= position < len(canvas_moves):
        return None

    canvas = canvas_moves[position]
    if (
        not isinstance(canvas, dict)
        or not _is_int(canvas.get("index"))
        or canvas["index"] != position
    ):
        return None
    return canvas


def _make_floor_plan(chart: dict) -> dict | None:
    """计算整份谱面所有 floorPosition 的新值，但不修改谱面。

    ``bpmShifts`` 的 ``floorPosition`` 是绝对秒数；``canvasMoves`` 的
    流速节点与引导线/音符的 ``floorPosition`` 则是对秒积分的画布高度。
    计算失败（结构非法、引用了不存在的画布等）时返回 ``None``。
    """
    timeline = _bpm_seconds(chart)
    if timeline is None:
        return None
    base_bpm, times, values, seconds = timeline
    shifts = chart["bpmShifts"]

    def seconds_at(tick: float) -> float:
        return _seconds_at(tick, base_bpm, times, values, seconds)

    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return None

    canvas_speeds: dict[int, tuple[list, list, list]] = {}
    canvas_plan = []
    for canvas in canvas_moves:
        if not isinstance(canvas, dict):
            return None
        canvas_index = canvas.get("index")
        if not _is_int(canvas_index) or canvas_index in canvas_speeds:
            return None

        key_points = canvas.get("speedKeyPoints")
        if not isinstance(key_points, list) or not key_points:
            return None

        key_times = []
        key_values = []
        for key_point in key_points:
            if not isinstance(key_point, dict):
                return None
            key_time = key_point.get("time")
            key_value = key_point.get("value")
            if (
                not _is_finite_number(key_time)
                or not _is_finite_number(key_value)
                or key_time < 0
            ):
                return None
            if key_times and key_time < key_times[-1]:
                return None
            key_times.append(key_time)
            key_values.append(key_value)

        key_floor_positions = [0.0] * len(key_times)
        for position in range(1, len(key_times)):
            key_floor_positions[position] = (
                key_floor_positions[position - 1]
                + key_values[position - 1]
                * (
                    seconds_at(key_times[position])
                    - seconds_at(key_times[position - 1])
                )
            )

        for key_point, floor_position in zip(
            key_points, key_floor_positions
        ):
            canvas_plan.append((key_point, floor_position))
        canvas_speeds[canvas_index] = (
            key_times,
            key_values,
            key_floor_positions,
        )

    def canvas_floor_position(canvas_index: int, tick: float) -> float:
        key_times, key_values, key_floor_positions = (
            canvas_speeds[canvas_index]
        )
        position = bisect.bisect_right(key_times, tick) - 1
        if position < 0:
            return key_values[0] * (
                seconds_at(tick) - seconds_at(key_times[0])
            )
        return (
            key_floor_positions[position]
            + key_values[position]
            * (seconds_at(tick) - seconds_at(key_times[position]))
        )

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    point_plan = []
    note_plan = []
    hold_plan = []
    for line in lines:
        if not isinstance(line, dict):
            return None

        line_points = line.get("linePoints")
        notes = line.get("notes")
        if not isinstance(line_points, list) or not isinstance(notes, list):
            return None

        point_times = []
        for point in line_points:
            if not isinstance(point, dict):
                return None
            point_time = point.get("time")
            canvas_index = point.get("canvasIndex")
            if (
                not _is_finite_number(point_time)
                or point_time < 0
                or not _is_int(canvas_index)
                or canvas_index not in canvas_speeds
            ):
                return None
            if point_times and point_time < point_times[-1]:
                return None
            point_times.append(point_time)
            point_plan.append(
                (point, canvas_floor_position(canvas_index, point_time))
            )

        if notes and not point_times:
            return None

        for note in notes:
            if not isinstance(note, dict):
                return None
            note_time = note.get("time")
            if not _is_finite_number(note_time) or note_time < 0:
                return None

            # 头部：正好在节点时间上时使用右侧节点的画布
            position = bisect.bisect_right(point_times, note_time) - 1
            if position < 0:
                return None
            canvas_index = line_points[position]["canvasIndex"]
            note_plan.append(
                (note, canvas_floor_position(canvas_index, note_time))
            )

            if note.get("type") != 2:
                continue
            extra = note.get("otherInformations")
            if not isinstance(extra, list) or len(extra) != 3:
                return None
            tail_time = extra[0]
            if (
                not _is_finite_number(tail_time)
                or tail_time < 0
                or tail_time > point_times[-1]
            ):
                return None

            # 尾部：正好在节点时间上时使用左侧节点（前一段）的画布
            tail_position = bisect.bisect_left(point_times, tail_time) - 1
            if tail_position < 0:
                return None
            tail_index = line_points[tail_position]["canvasIndex"]
            if tail_index not in canvas_speeds:
                return None
            hold_plan.append(
                (
                    extra,
                    tail_index,
                    canvas_floor_position(tail_index, tail_time),
                )
            )

    return {
        "bpmShifts": list(zip(shifts, seconds)),
        "canvasSpeedKeyPoints": canvas_plan,
        "linePoints": point_plan,
        "notes": note_plan,
        "holds": hold_plan,
    }


def _apply_floor_plan(plan: dict) -> None:
    """把 ``_make_floor_plan()`` 的结果写回谱面。"""
    for node, floor_position in plan["bpmShifts"]:
        node["floorPosition"] = floor_position
    for key_point, floor_position in plan["canvasSpeedKeyPoints"]:
        key_point["floorPosition"] = floor_position
    for point, floor_position in plan["linePoints"]:
        point["floorPosition"] = floor_position
    for note, floor_position in plan["notes"]:
        note["floorPosition"] = floor_position
    for extra, canvas_index, floor_position in plan["holds"]:
        extra[1] = canvas_index
        extra[2] = floor_position
