"""谱面查询工具。"""

from __future__ import annotations

import bisect

from ._internal import (
    _bpm_seconds as _get_bpm_timeline,
    _canvas_ref,
    _canvas_x_at,
    _ease,
    _find_canvas,
    _is_finite_number,
    _is_int,
    _parse_color,
    _round_color_channel,
    _seconds_at,
    _seconds_to_tick as _tick_at_realtime,
)
from .chart import mixColor

__all__ = [
    "getFileVersion",
    "getDelay",
    "getBaseBpm",
    "getLineCount",
    "getCanvasCount",
    "getBpmShiftCount",
    "getRiztimeCount",
    "getNoteCount",
    "getBpmAt",
    "getSecondsAt",
    "getTickAt",
    "getFloorPosition",
    "getBpmShift",
    "getCanvas",
    "getCanvasPosition",
    "getCanvasPositionAt",
    "getCanvasSpeedAt",
    "getCanvasSpeed",
    "getCamera",
    "getCameraPositionAt",
    "getCameraScaleAt",
    "getCameraPosition",
    "getCameraScale",
    "getLine",
    "getLinePoint",
    "getRingPoint",
    "getLineColor",
    "getNote",
    "getTheme",
    "getThemeColor",
    "getChallengeTime",
    "getRiztime",
    "getBpmShiftByTime",
    "getCanvasPositionByTime",
    "getCanvasSpeedByTime",
    "getCameraPositionByTime",
    "getCameraScaleByTime",
    "getLinePointByTime",
    "getRingPointByTime",
    "getLineColorByTime",
    "getNoteByTime",
    "getThemeByColor",
    "getLinePointByColor",
    "getRingPointByColor",
    "getLineColorByColor",
    "getBaseColor",
    "getCoverColor",
    "getMixColor",
    "getLinePosition",
    "getLineByPoint",
    "getLineByNote",
    "getLineTimeRange",
    "getNotePosition",
    "getNoteCanvas",
]


def getFileVersion(chart: dict) -> int | None:
    """查询谱面文件版本。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    value = chart.get("fileVersion")
    return value if _is_int(value) else None


def getDelay(chart: dict) -> int | None:
    """查询谱面延迟（毫秒）。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    value = chart.get("chartDelayMs")
    return value if _is_int(value) else None


def getBaseBpm(chart: dict) -> float | None:
    """查询基准 BPM。缺失或非正数时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    value = chart.get("bPM")
    if not _is_finite_number(value) or value <= 0:
        return None
    return float(value)


def getLineCount(chart: dict) -> int | None:
    """查询引导线数量。``lines`` 结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None
    return len(lines)


def getCanvasCount(chart: dict) -> int | None:
    """查询画布数量。``canvasMoves`` 结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return None
    return len(canvas_moves)


def getBpmShiftCount(chart: dict) -> int | None:
    """查询 BPM 变化节点数量。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list):
        return None
    return len(shifts)


def getRiztimeCount(chart: dict) -> int | None:
    """查询 Riztime 数量。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return None
    challenge_times = chart.get("challengeTimes")
    if not isinstance(challenge_times, list):
        return None
    return len(challenge_times)


def getNoteCount(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> int | None:
    """查询指定线索引范围内所有线的 Note 总数。

    ``endindex=None`` 时只查询 ``startindex`` 一条线；否则查询闭区间
    ``[startindex, endindex]``。成功返回 ``int``（包括 0），失败返回
    ``None``。
    """
    if not isinstance(chart, dict):
        return None
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    if endindex is None:
        index = _resolve_single_index(startindex, len(lines))
        if index is None:
            return None
        line = lines[index]
        if not isinstance(line, dict):
            return None
        notes = line.get("notes")
        if not isinstance(notes, list):
            return None
        return len(notes)

    indices = _resolve_range_indices(startindex, endindex, len(lines))
    if indices is None:
        return None

    total = 0
    for index in indices:
        line = lines[index]
        if not isinstance(line, dict):
            return None
        notes = line.get("notes")
        if not isinstance(notes, list):
            return None
        total += len(notes)
    return total


def _bpm_floor_position(
    tick: float,
    base_bpm: float,
    times: list,
    values: list,
    floor_positions: list,
) -> float | None:
    last_index = None
    for position, node_time in enumerate(times):
        if node_time <= tick:
            last_index = position
        else:
            break

    if last_index is None:
        return None

    return (
        floor_positions[last_index]
        + (tick - times[last_index])
        * 60.0
        / (base_bpm * values[last_index])
    )


def _canvas_floor_position(
    chart: dict,
    canvas: dict,
    tick: float,
) -> float | None:
    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return None
    base_bpm, times, values, floor_positions = timeline

    key_points = canvas.get("speedKeyPoints")
    if not isinstance(key_points, list) or not key_points:
        return None

    last_key_point = None
    previous_time = None

    for key_point in key_points:
        if not isinstance(key_point, dict):
            return None
        key_time = key_point.get("time")
        key_value = key_point.get("value")
        key_floor_position = key_point.get("floorPosition")
        if (
            not _is_finite_number(key_time)
            or not _is_finite_number(key_value)
            or not _is_finite_number(key_floor_position)
        ):
            return None
        if previous_time is not None and key_time < previous_time:
            return None
        previous_time = key_time

        if key_time <= tick:
            last_key_point = key_point

    if last_key_point is None:
        return None

    return (
        last_key_point["floorPosition"]
        + last_key_point["value"]
        * (
            _seconds_at(tick, base_bpm, times, values, floor_positions)
            - _seconds_at(
                last_key_point["time"],
                base_bpm,
                times,
                values,
                floor_positions,
            )
        )
    )


def getBpmAt(
    chart: dict,
    time: float,
    isRealTime: bool = False,
) -> float | None:
    """查询指定时间点的实际 BPM。

    ``time`` 默认是 tick；``isRealTime=True`` 时是实际秒数。返回
    ``bPM * bpmShifts[].value``，即该时刻生效的实际 BPM。谱面必须在
    ``time=0.0`` 处有一个 BPM 节点；失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return None
    base_bpm, times, values, floor_positions = timeline

    if isRealTime:
        tick = _tick_at_realtime(
            float(time),
            base_bpm,
            times,
            values,
            floor_positions,
        )
        if tick is None:
            return None
    else:
        tick = float(time)

    position = bisect.bisect_right(times, tick) - 1
    if position < 0:
        return None
    return float(base_bpm * values[position])


def getSecondsAt(chart: dict, tick: float) -> float | None:
    """查询指定 tick 对应的绝对秒数。

    ``tick`` 必须大于等于 0。谱面必须在 ``time=0.0`` 处有一个 BPM
    节点；查询晚于最后一个 BPM 节点时继续按最后一个 BPM 节点计算。
    失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(tick) or tick < 0:
        return None

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return None
    base_bpm, times, values, floor_positions = timeline
    return float(
        _seconds_at(
            float(tick),
            base_bpm,
            times,
            values,
            floor_positions,
        )
    )


def getTickAt(chart: dict, seconds: float) -> float | None:
    """查询指定绝对秒数对应的 tick。

    ``seconds`` 必须大于等于 0。谱面必须在 ``time=0.0`` 处有一个 BPM
    节点；查询晚于最后一个 BPM 节点时继续按最后一个 BPM 节点计算。
    失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(seconds) or seconds < 0:
        return None

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return None
    base_bpm, times, values, floor_positions = timeline

    tick = _tick_at_realtime(
        float(seconds),
        base_bpm,
        times,
        values,
        floor_positions,
    )
    if tick is None or tick < 0:
        return None
    return float(tick)


def getFloorPosition(
    chart: dict,
    time: float,
    canvasindex: int | None = None,
    isRealTime: bool = False,
) -> float | None:
    """查询指定时间点的 floorPosition。

    ``canvasindex`` 为 ``None`` 时查询 BPM 时间轴，否则查询对应画布。
    ``isRealTime=True`` 时 ``time`` 为实际秒数，否则为 tick。
    谱面必须在 ``time=0.0`` 处有一个 BPM 节点。
    成功返回计算值，失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None

    query_time = float(time)

    if canvasindex is None:
        timeline = _get_bpm_timeline(chart)
        if timeline is None:
            return None
        if isRealTime:
            return query_time

        base_bpm, times, values, floor_positions = timeline
        result = _bpm_floor_position(
            query_time,
            base_bpm,
            times,
            values,
            floor_positions,
        )
        return None if result is None else float(result)

    if not _is_int(canvasindex):
        return None

    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return None

    canvas = None
    for item in canvas_moves:
        if isinstance(item, dict) and item.get("index") == canvasindex:
            canvas = item
            break
    if canvas is None:
        return None

    if isRealTime:
        timeline = _get_bpm_timeline(chart)
        if timeline is None:
            return None
        base_bpm, times, values, floor_positions = timeline
        tick = _tick_at_realtime(
            query_time,
            base_bpm,
            times,
            values,
            floor_positions,
        )
        if tick is None:
            return None
    else:
        tick = query_time

    result = _canvas_floor_position(chart, canvas, tick)
    return None if result is None else float(result)


def _resolve_single_index(index: object, length: int) -> int | None:
    if not _is_int(index):
        return None
    position = index + length if index < 0 else index
    if 0 <= position < length:
        return position
    return None


def _resolve_range_indices(
    startindex: object,
    endindex: object,
    length: int,
) -> list[int] | None:
    if not _is_int(startindex) or not _is_int(endindex):
        return None
    start = startindex + length if startindex < 0 else startindex
    end = endindex + length if endindex < 0 else endindex
    if start < 0:
        start = 0
    if end >= length:
        end = length - 1
    if start > end:
        return []
    return list(range(start, end + 1))


def _query_items(
    items: object,
    startindex: object,
    endindex: object,
    builder,
) -> dict | list | None:
    if not isinstance(items, list):
        return None
    if endindex is None:
        index = _resolve_single_index(startindex, len(items))
        if index is None:
            return None
        return builder(items[index])

    indices = _resolve_range_indices(startindex, endindex, len(items))
    if indices is None:
        return None

    result = []
    for index in indices:
        item = builder(items[index])
        if item is None:
            return None
        result.append(item)
    return result


def _valid_index_list(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, list):
        return False
    return all(_is_int(item) for item in value)


def _allowed_indices(value: list | None, length: int) -> set[int] | None:
    if value is None:
        return None
    result = set()
    for item in value:
        position = item + length if item < 0 else item
        if 0 <= position < length:
            result.add(position)
    return result


def _key_point_spec(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    time = value.get("time")
    key_value = value.get("value")
    ease_type = value.get("easeType")
    if not _is_finite_number(time) or time < 0:
        return None
    if not _is_finite_number(key_value):
        return None
    if not _is_int(ease_type) or not 0 <= ease_type <= 18:
        return None
    return {
        "time": float(time),
        "value": float(key_value),
        "easeType": ease_type,
    }


def _bpm_shift_spec(value: object) -> dict | None:
    spec = _key_point_spec(value)
    if spec is None or spec["value"] <= 0:
        return None
    return spec


def _key_point_specs(
    values: object,
    non_empty: bool = True,
) -> list | None:
    if not isinstance(values, list):
        return None
    if non_empty and not values:
        return None
    result = []
    previous_time = None
    for value in values:
        spec = _key_point_spec(value)
        if spec is None:
            return None
        if previous_time is not None and spec["time"] < previous_time:
            return None
        previous_time = spec["time"]
        result.append(spec)
    return result


def _key_point_value_at(
    values: object,
    tick: float,
) -> float | None:
    """按关键点数组插值计算指定 tick 的数值。"""
    points = _key_point_specs(values)
    if points is None:
        return None

    times = [point["time"] for point in points]
    if tick < times[0]:
        return None
    if tick >= times[-1]:
        return float(points[-1]["value"])

    position = bisect.bisect_right(times, tick) - 1
    if times[position] == tick:
        return float(points[position]["value"])

    start = points[position]
    end = points[position + 1]
    ratio = (tick - start["time"]) / (end["time"] - start["time"])
    eased = _ease(start["easeType"], ratio)
    if eased is None:
        return None
    return float(start["value"] + (end["value"] - start["value"]) * eased)


def _canvas_speed_at(
    values: object,
    tick: float,
) -> float | None:
    """按关键点数组取指定 tick 的流速（阶梯变化，不插值）。"""
    points = _key_point_specs(values)
    if points is None:
        return None

    times = [point["time"] for point in points]
    if tick < times[0]:
        return None

    position = bisect.bisect_right(times, tick) - 1
    if position < 0:
        return None
    return float(points[position]["value"])


def _color_change_spec(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    time = value.get("time")
    if not _is_finite_number(time) or time < 0:
        return None
    start_color = _parse_color(value.get("startColor"))
    end_color = _parse_color(value.get("endColor"))
    if start_color is None or end_color is None:
        return None
    return {
        "startColor": _color_list(start_color),
        "endColor": _color_list(end_color),
        "time": float(time),
    }


def _color_change_specs(
    values: object,
    non_empty: bool = False,
) -> list | None:
    if not isinstance(values, list):
        return None
    if non_empty and not values:
        return None
    result = []
    previous_time = None
    for value in values:
        spec = _color_change_spec(value)
        if spec is None:
            return None
        if previous_time is not None and spec["time"] < previous_time:
            return None
        previous_time = spec["time"]
        result.append(spec)
    return result


def _parse_color_range(
    startcolor: object,
    endcolor: object,
) -> dict | None:
    start = _parse_color(startcolor)
    if start is None:
        return None
    if endcolor is None:
        end = dict(start)
    else:
        end = _parse_color(endcolor)
        if end is None:
            return None

    ranges = {}
    for channel in ("r", "g", "b", "a"):
        low = start[channel]
        high = end[channel]
        if high < low:
            return None
        ranges[channel] = (low, high)
    return ranges


def _color_in_range(color: dict, ranges: dict) -> bool:
    return all(
        ranges[channel][0] <= color[channel] <= ranges[channel][1]
        for channel in ("r", "g", "b", "a")
    )


def _theme_spec(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    colors = value.get("colorsList")
    if not isinstance(colors, list) or len(colors) != 3:
        return None
    result = []
    for color in colors:
        parsed = _parse_color(color)
        if parsed is None:
            return None
        result.append(_color_list(parsed))
    return {"colorsList": result}


def _challenge_time_spec(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    result = {}
    for key in ("checkPoint", "start", "end", "transTime"):
        item = value.get(key)
        if not _is_finite_number(item):
            return None
        result[key] = float(item)
    if result["end"] < result["start"] or result["transTime"] < 0:
        return None
    return result


def _riztime_specs(chart: dict) -> list | None:
    challenge_times = chart.get("challengeTimes")
    themes = chart.get("themes")
    if not isinstance(challenge_times, list):
        return None
    if not isinstance(themes, list):
        return None
    if len(themes) != len(challenge_times) + 1:
        return None

    result = []
    for index, challenge in enumerate(challenge_times):
        theme_spec = _theme_spec(themes[index + 1])
        challenge_spec = _challenge_time_spec(challenge)
        if theme_spec is None or challenge_spec is None:
            return None
        result.append(
            {
                "themeIndex": index + 1,
                "challengeIndex": index,
                "colorsList": theme_spec["colorsList"],
                **challenge_spec,
            }
        )
    return result


def _line_point_export_spec(chart: dict, value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    time = value.get("time")
    x_position = value.get("xPosition")
    canvas_index = value.get("canvasIndex")
    ease_type = value.get("easeType")
    if not _is_finite_number(time) or time < 0:
        return None
    if not _is_finite_number(x_position):
        return None
    if not _is_int(canvas_index):
        return None
    canvas = _find_canvas(chart, canvas_index)
    if canvas is None:
        return None
    if not _is_int(ease_type) or not 0 <= ease_type <= 18:
        return None
    color = _parse_color(value.get("color"))
    if color is None:
        return None
    return {
        "time": float(time),
        "xPosition": float(x_position),
        "canvasIndex": canvas["index"],
        "easeType": ease_type,
        "color": _color_list(color),
    }


def _line_points_spec(chart: dict, line: dict) -> list | None:
    points = line.get("linePoints")
    if not isinstance(points, list) or len(points) < 2:
        return None
    result = []
    previous_time = None
    for point in points:
        spec = _line_point_export_spec(chart, point)
        if spec is None:
            return None
        if previous_time is not None and spec["time"] < previous_time:
            return None
        previous_time = spec["time"]
        result.append(spec)
    return result


def _note_export_spec(line_times: list, value: object) -> dict | None:
    if not isinstance(value, dict) or len(line_times) < 2:
        return None
    note_type = value.get("type")
    head_time = value.get("time")
    if not _is_int(note_type) or note_type not in (0, 1, 2):
        return None
    if not _is_finite_number(head_time) or head_time < 0:
        return None
    if head_time < line_times[0] or head_time > line_times[-1]:
        return None

    if note_type == 2:
        extra = value.get("otherInformations")
        if not isinstance(extra, list) or len(extra) != 3:
            return None
        tail_time = extra[0]
        if not _is_finite_number(tail_time):
            return None
        if tail_time <= head_time or tail_time > line_times[-1]:
            return None
        return {
            "type": 2,
            "time": float(head_time),
            "endtime": float(tail_time),
        }

    return {
        "type": note_type,
        "time": float(head_time),
    }


def _note_specs(line_times: list, values: object) -> list | None:
    if not isinstance(values, list):
        return None
    result = []
    previous_time = None
    for value in values:
        spec = _note_export_spec(line_times, value)
        if spec is None:
            return None
        if previous_time is not None and spec["time"] < previous_time:
            return None
        previous_time = spec["time"]
        result.append(spec)
    return result


def _parse_note_by_time_type(
    value: object,
) -> tuple[int | None, bool] | None:
    if value is None:
        return (None, False)
    if _is_int(value):
        if value in (0, 1, 2):
            return (value, False)
        if value == 3:
            return (2, True)
        return None
    if isinstance(value, str):
        mapping = {
            "tap": (0, False),
            "drag": (1, False),
            "hold": (2, False),
            "holdtail": (2, True),
        }
        return mapping.get(value.lower())
    return None


def _line_spec(chart: dict, value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    point_specs = _line_points_spec(chart, value)
    if point_specs is None:
        return None
    line_times = [point["time"] for point in point_specs]

    ring_specs = _color_change_specs(
        value.get("judgeRingColor"),
        non_empty=True,
    )
    if ring_specs is None:
        return None

    note_specs = _note_specs(line_times, value.get("notes"))
    if note_specs is None:
        return None

    color_specs = _color_change_specs(value.get("lineColor"))
    if color_specs is None:
        return None

    return {
        "linePoints": point_specs,
        "notes": note_specs,
        "judgeRingColor": ring_specs,
        "lineColor": color_specs,
    }


def _canvas_spec(chart: dict, value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    index = value.get("index")
    if not _is_int(index):
        return None
    canvas = _find_canvas(chart, index)
    if canvas is None:
        return None
    x_points = _key_point_specs(canvas.get("xPositionKeyPoints"))
    speed_points = _key_point_specs(canvas.get("speedKeyPoints"))
    if x_points is None or speed_points is None:
        return None
    return {
        "index": canvas["index"],
        "xPositionKeyPoints": x_points,
        "speedKeyPoints": speed_points,
    }


def _camera_spec(chart: dict) -> dict | None:
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    scale_points = _key_point_specs(camera.get("scaleKeyPoints"))
    x_points = _key_point_specs(camera.get("xPositionKeyPoints"))
    if scale_points is None or x_points is None:
        return None
    return {
        "scaleKeyPoints": scale_points,
        "xPositionKeyPoints": x_points,
    }


def _find_line(chart: dict, index: object) -> dict | None:
    if not isinstance(chart, dict):
        return None
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None
    position = _resolve_single_index(index, len(lines))
    if position is None:
        return None
    line = lines[position]
    return line if isinstance(line, dict) else None


def _note_context(
    chart: dict,
    lineindex: object,
    noteindex: object,
) -> tuple[int, dict, dict, int, float, list, list] | None:
    """定位 Note，并返回线索引、Note、头部时间与线节点规格。"""
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None
    line_position = _resolve_single_index(lineindex, len(lines))
    if line_position is None:
        return None
    line = lines[line_position]
    if not isinstance(line, dict):
        return None

    notes = line.get("notes")
    if not isinstance(notes, list):
        return None
    note_position = _resolve_single_index(noteindex, len(notes))
    if note_position is None:
        return None
    note = notes[note_position]
    if not isinstance(note, dict):
        return None

    note_type = note.get("type")
    if not _is_int(note_type) or note_type not in (0, 1, 2):
        return None
    head_time = note.get("time")
    if not _is_finite_number(head_time) or head_time < 0:
        return None

    points = _line_points_spec(chart, line)
    if points is None:
        return None
    times = [point["time"] for point in points]
    if head_time < times[0] or head_time > times[-1]:
        return None

    return (
        line_position,
        line,
        note,
        note_type,
        float(head_time),
        points,
        times,
    )


def _selected_canvases(
    chart: dict,
    canvasindex: object,
) -> list[tuple[int, dict]] | None:
    canvases = chart.get("canvasMoves")
    if not isinstance(canvases, list):
        return None

    if canvasindex is not None:
        canvas = _find_canvas(chart, canvasindex)
        if canvas is None:
            return None
        return [(canvas["index"], canvas)]

    result = []
    for index, canvas in enumerate(canvases):
        if not isinstance(canvas, dict):
            return None
        if not _is_int(canvas.get("index")) or canvas["index"] != index:
            return None
        result.append((index, canvas))
    return result


def _selected_lines(
    chart: dict,
    lineindex: object,
) -> list[tuple[int, dict]] | None:
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    if lineindex is not None:
        position = _resolve_single_index(lineindex, len(lines))
        if position is None:
            return None
        line = lines[position]
        if not isinstance(line, dict):
            return None
        return [(position, line)]

    result = []
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            return None
        result.append((index, line))
    return result


def _query_tick(
    chart: dict,
    time: object,
    is_real_time: bool,
) -> float | None:
    """把查询时间转换为 tick。"""
    if not _is_finite_number(time) or time < 0:
        return None
    if not is_real_time:
        return float(time)

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return None
    base_bpm, times, values, floor_positions = timeline
    tick = _tick_at_realtime(
        float(time),
        base_bpm,
        times,
        values,
        floor_positions,
    )
    if tick is None or tick < 0:
        return None
    return tick


def _parse_range(
    value: object,
    non_negative: bool = False,
) -> tuple[float | None, float | None] | None:
    """把查询值解析为单值/区间；``None`` 表示不限。"""
    if value is None:
        return (None, None)

    if _is_finite_number(value):
        if non_negative and value < 0:
            return None
        return (float(value), float(value))

    if isinstance(value, list) and len(value) == 2:
        low, high = value
        if not _is_finite_number(low) or not _is_finite_number(high):
            return None
        if non_negative and (low < 0 or high < 0):
            return None
        if low > high:
            return None
        return (float(low), float(high))

    return None


def _query_tick_range(
    chart: dict,
    value: object,
    is_real_time: bool,
) -> tuple[float | None, float | None, bool] | None:
    """解析时间查询范围，必要时把秒换算为 tick。"""
    parsed = _parse_range(value, non_negative=True)
    if parsed is None:
        return None

    low, high = parsed
    if low is None:
        return (None, None, True)

    if not is_real_time:
        return (low, high, low == high)

    low_tick = _query_tick(chart, low, True)
    high_tick = _query_tick(chart, high, True)
    if low_tick is None or high_tick is None or low_tick > high_tick:
        return None
    return (low_tick, high_tick, low == high)


def _query_time_range(
    chart: dict,
    starttime: object,
    endtime: object,
    is_real_start_time: bool,
    is_real_end_time: bool,
) -> tuple[float, float | None, bool] | None:
    start = _query_tick(chart, starttime, is_real_start_time)
    if start is None:
        return None

    if endtime is None:
        return (start, None, False)

    end = _query_tick(chart, endtime, is_real_end_time)
    if end is None or end < start:
        return None
    return (start, end, end == start)


def _value_matches(
    value: float,
    low: float,
    high: float,
    single: bool,
) -> bool:
    if single:
        return value == low
    return low <= value <= high


def _time_matches(
    value: float,
    low: float | None,
    high: float | None,
    single: bool,
) -> bool:
    if single and low is not None:
        return value == low
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def _line_x_at(line: dict, tick: float) -> tuple[float, int] | None:
    """计算引导线在指定 tick 的相对 x 坐标与所在画布。"""
    points = line.get("linePoints")
    if not isinstance(points, list) or not points:
        return None

    times = []
    values = []
    canvases = []
    for point in points:
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        point_x = point.get("xPosition")
        canvas_index = point.get("canvasIndex")
        if (
            not _is_finite_number(point_time)
            or point_time < 0
            or not _is_finite_number(point_x)
            or not _is_int(canvas_index)
        ):
            return None
        if times and point_time < times[-1]:
            return None
        times.append(point_time)
        values.append(point_x)
        canvases.append(canvas_index)

    if tick < times[0] or tick > times[-1]:
        return None

    position = bisect.bisect_right(times, tick) - 1
    if times[position] == tick:
        return float(values[position]), canvases[position]

    start = times[position]
    end = times[position + 1]
    ratio = (tick - start) / (end - start)
    eased = _ease(points[position].get("easeType"), ratio)
    if eased is None:
        return None
    value = (
        values[position]
        + (values[position + 1] - values[position]) * eased
    )
    return float(value), canvases[position]


def getBpmShift(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段 BPM 节点规格。"""
    if not isinstance(chart, dict):
        return None
    return _query_items(
        chart.get("bpmShifts"),
        startindex,
        endindex,
        _bpm_shift_spec,
    )


def getCanvas(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段画布规格。"""
    if not isinstance(chart, dict):
        return None
    return _query_items(
        chart.get("canvasMoves"),
        startindex,
        endindex,
        lambda value: _canvas_spec(chart, value),
    )


def getCanvasPosition(
    chart: dict,
    canvasindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询指定画布的 x 位置关键点规格。"""
    if not isinstance(chart, dict):
        return None
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None
    return _query_items(
        canvas.get("xPositionKeyPoints"),
        startindex,
        endindex,
        _key_point_spec,
    )


def getCanvasSpeed(
    chart: dict,
    canvasindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询指定画布的流速关键点规格。"""
    if not isinstance(chart, dict):
        return None
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None
    return _query_items(
        canvas.get("speedKeyPoints"),
        startindex,
        endindex,
        _key_point_spec,
    )


def getCamera(chart: dict) -> dict | None:
    """查询摄像机规格。"""
    if not isinstance(chart, dict):
        return None
    return _camera_spec(chart)


def getCameraPosition(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段摄像机 x 位置关键点规格。"""
    if not isinstance(chart, dict):
        return None
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    return _query_items(
        camera.get("xPositionKeyPoints"),
        startindex,
        endindex,
        _key_point_spec,
    )


def getCameraScale(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段摄像机缩放关键点规格。"""
    if not isinstance(chart, dict):
        return None
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    return _query_items(
        camera.get("scaleKeyPoints"),
        startindex,
        endindex,
        _key_point_spec,
    )


def getLine(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段引导线规格。"""
    if not isinstance(chart, dict):
        return None
    return _query_items(
        chart.get("lines"),
        startindex,
        endindex,
        lambda value: _line_spec(chart, value),
    )


def getLinePoint(
    chart: dict,
    lineindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一条引导线上的线节点规格。"""
    if not isinstance(chart, dict):
        return None
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    return _query_items(
        line.get("linePoints"),
        startindex,
        endindex,
        lambda value: _line_point_export_spec(chart, value),
    )


def getRingPoint(
    chart: dict,
    lineindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一条引导线上的判定环规格。"""
    if not isinstance(chart, dict):
        return None
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    return _query_items(
        line.get("judgeRingColor"),
        startindex,
        endindex,
        _color_change_spec,
    )


def getLineColor(
    chart: dict,
    lineindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一条引导线上的线色覆盖规格。"""
    if not isinstance(chart, dict):
        return None
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    return _query_items(
        line.get("lineColor"),
        startindex,
        endindex,
        _color_change_spec,
    )


def getNote(
    chart: dict,
    lineindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一条引导线上的 Note 规格。"""
    if not isinstance(chart, dict):
        return None
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    point_specs = _line_points_spec(chart, line)
    if point_specs is None:
        return None
    line_times = [point["time"] for point in point_specs]
    return _query_items(
        line.get("notes"),
        startindex,
        endindex,
        lambda value: _note_export_spec(line_times, value),
    )


def getTheme(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段主题规格。"""
    if not isinstance(chart, dict):
        return None
    return _query_items(
        chart.get("themes"),
        startindex,
        endindex,
        _theme_spec,
    )


def getThemeColor(
    chart: dict,
    themeindex: int,
    startindex: int,
    endindex: int | None = None,
) -> list | None:
    """查询一个主题内的颜色规格。"""
    if not isinstance(chart, dict):
        return None
    themes = chart.get("themes")
    if not isinstance(themes, list):
        return None
    position = _resolve_single_index(themeindex, len(themes))
    if position is None:
        return None
    theme_spec = _theme_spec(themes[position])
    if theme_spec is None:
        return None
    return _query_items(
        theme_spec["colorsList"],
        startindex,
        endindex,
        lambda value: value,
    )


def getChallengeTime(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段 challengeTimes 规格。"""
    if not isinstance(chart, dict):
        return None
    return _query_items(
        chart.get("challengeTimes"),
        startindex,
        endindex,
        _challenge_time_spec,
    )


def getRiztime(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段 Riztime 合并规格。"""
    if not isinstance(chart, dict):
        return None
    specs = _riztime_specs(chart)
    if specs is None:
        return None
    return _query_items(
        specs,
        startindex,
        endindex,
        lambda value: value,
    )


def getBpmShiftByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询 BPM 节点索引。"""
    if not isinstance(chart, dict):
        return None
    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list):
        return None
    time_range = _query_time_range(
        chart,
        starttime,
        endtime,
        isRealStartTime,
        isRealEndTime,
    )
    if time_range is None:
        return None
    if not _valid_index_list(indexlist):
        return None

    start, end, single = time_range
    allowed = _allowed_indices(indexlist, len(shifts))
    result = []
    for index, node in enumerate(shifts):
        if allowed is not None and index not in allowed:
            continue
        if not isinstance(node, dict):
            return None
        node_time = node.get("time")
        if not _is_finite_number(node_time) or node_time < 0:
            return None
        if _time_matches(node_time, start, end, single):
            result.append(index)
    return result


def _get_canvas_point_indexes_by_time(
    chart: dict,
    key: str,
    starttime: float,
    endtime: float | None,
    indexlist: list | None,
    canvasindex: int | None,
    is_real_start_time: bool,
    is_real_end_time: bool,
) -> list | None:
    selected = _selected_canvases(chart, canvasindex)
    if selected is None:
        return None
    time_range = _query_time_range(
        chart,
        starttime,
        endtime,
        is_real_start_time,
        is_real_end_time,
    )
    if time_range is None:
        return None
    if not _valid_index_list(indexlist):
        return None

    start, end, single = time_range
    result = []
    for canvas_index, canvas in selected:
        points = canvas.get(key)
        if not isinstance(points, list):
            return None
        allowed = _allowed_indices(indexlist, len(points))
        for point_index, point in enumerate(points):
            if allowed is not None and point_index not in allowed:
                continue
            if not isinstance(point, dict):
                return None
            point_time = point.get("time")
            if not _is_finite_number(point_time) or point_time < 0:
                return None
            if _time_matches(point_time, start, end, single):
                result.append([canvas_index, point_index])
    return result


def getCanvasPositionByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    canvasindex: int | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询画布 x 位置关键点索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_canvas_point_indexes_by_time(
        chart,
        "xPositionKeyPoints",
        starttime,
        endtime,
        indexlist,
        canvasindex,
        isRealStartTime,
        isRealEndTime,
    )


def getCanvasSpeedByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    canvasindex: int | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询画布流速关键点索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_canvas_point_indexes_by_time(
        chart,
        "speedKeyPoints",
        starttime,
        endtime,
        indexlist,
        canvasindex,
        isRealStartTime,
        isRealEndTime,
    )


def _get_camera_point_indexes_by_time(
    chart: dict,
    key: str,
    starttime: float,
    endtime: float | None,
    indexlist: list | None,
    is_real_start_time: bool,
    is_real_end_time: bool,
) -> list | None:
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    points = camera.get(key)
    if not isinstance(points, list):
        return None
    time_range = _query_time_range(
        chart,
        starttime,
        endtime,
        is_real_start_time,
        is_real_end_time,
    )
    if time_range is None:
        return None
    if not _valid_index_list(indexlist):
        return None

    start, end, single = time_range
    allowed = _allowed_indices(indexlist, len(points))
    result = []
    for index, point in enumerate(points):
        if allowed is not None and index not in allowed:
            continue
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        if not _is_finite_number(point_time) or point_time < 0:
            return None
        if _time_matches(point_time, start, end, single):
            result.append(index)
    return result


def getCameraPositionByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询摄像机 x 位置关键点索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_camera_point_indexes_by_time(
        chart,
        "xPositionKeyPoints",
        starttime,
        endtime,
        indexlist,
        isRealStartTime,
        isRealEndTime,
    )


def getCameraScaleByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询摄像机缩放关键点索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_camera_point_indexes_by_time(
        chart,
        "scaleKeyPoints",
        starttime,
        endtime,
        indexlist,
        isRealStartTime,
        isRealEndTime,
    )


def _get_line_child_indexes_by_time(
    chart: dict,
    key: str,
    starttime: float,
    endtime: float | None,
    indexlist: list | None,
    lineindex: int | None,
    canvasindex: int | None,
    is_real_start_time: bool,
    is_real_end_time: bool,
) -> list | None:
    selected = _selected_lines(chart, lineindex)
    if selected is None:
        return None
    time_range = _query_time_range(
        chart,
        starttime,
        endtime,
        is_real_start_time,
        is_real_end_time,
    )
    if time_range is None:
        return None
    if not _valid_index_list(indexlist):
        return None

    canvas_filter = None
    if canvasindex is not None:
        canvas = _find_canvas(chart, canvasindex)
        if canvas is None:
            return None
        canvas_filter = canvas["index"]

    start, end, single = time_range
    result = []
    for line_index, line in selected:
        values = line.get(key)
        if not isinstance(values, list):
            return None
        allowed = _allowed_indices(indexlist, len(values))
        for index, value in enumerate(values):
            if allowed is not None and index not in allowed:
                continue
            if not isinstance(value, dict):
                return None
            value_time = value.get("time")
            if not _is_finite_number(value_time) or value_time < 0:
                return None
            if canvas_filter is not None:
                point_canvas = value.get("canvasIndex")
                if not _is_int(point_canvas):
                    return None
                point_canvas = _find_canvas(chart, point_canvas)
                if point_canvas is None:
                    return None
                if point_canvas["index"] != canvas_filter:
                    continue
            if _time_matches(value_time, start, end, single):
                result.append([line_index, index])
    return result


def getLinePointByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    canvasindex: int | None = None,
    lineindex: int | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询线节点索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_line_child_indexes_by_time(
        chart,
        "linePoints",
        starttime,
        endtime,
        indexlist,
        lineindex,
        canvasindex,
        isRealStartTime,
        isRealEndTime,
    )


def getRingPointByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    lineindex: int | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询判定环索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_line_child_indexes_by_time(
        chart,
        "judgeRingColor",
        starttime,
        endtime,
        indexlist,
        lineindex,
        None,
        isRealStartTime,
        isRealEndTime,
    )


def getLineColorByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    lineindex: int | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询线色覆盖索引。"""
    if not isinstance(chart, dict):
        return None
    return _get_line_child_indexes_by_time(
        chart,
        "lineColor",
        starttime,
        endtime,
        indexlist,
        lineindex,
        None,
        isRealStartTime,
        isRealEndTime,
    )


def getNoteByTime(
    chart: dict,
    starttime: float,
    endtime: float | None = None,
    indexlist: list | None = None,
    lineindex: int | None = None,
    type: int | str | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list | None:
    """按时间范围查询 Note 索引；``type=3`` 按 Hold 尾部时间查询。"""
    if not isinstance(chart, dict):
        return None
    selected = _selected_lines(chart, lineindex)
    if selected is None:
        return None
    time_range = _query_time_range(
        chart,
        starttime,
        endtime,
        isRealStartTime,
        isRealEndTime,
    )
    if time_range is None:
        return None
    if not _valid_index_list(indexlist):
        return None
    note_filter = _parse_note_by_time_type(type)
    if note_filter is None:
        return None
    wanted_type, use_tail = note_filter

    start, end, single = time_range
    result = []
    for line_index, line in selected:
        notes = line.get("notes")
        if not isinstance(notes, list):
            return None
        allowed = _allowed_indices(indexlist, len(notes))
        for note_index, note in enumerate(notes):
            if allowed is not None and note_index not in allowed:
                continue
            if not isinstance(note, dict):
                return None
            note_type = note.get("type")
            if not _is_int(note_type) or note_type not in (0, 1, 2):
                return None
            head_time = note.get("time")
            if not _is_finite_number(head_time) or head_time < 0:
                return None

            if use_tail:
                if note_type != 2:
                    continue
                extra = note.get("otherInformations")
                if not isinstance(extra, list) or len(extra) != 3:
                    return None
                note_time = extra[0]
                if not _is_finite_number(note_time) or note_time < 0:
                    return None
            else:
                if wanted_type is not None and note_type != wanted_type:
                    continue
                note_time = head_time

            if _time_matches(note_time, start, end, single):
                result.append([line_index, note_index])
    return result


def getThemeByColor(
    chart: dict,
    startcolor: str | list,
    endcolor: str | list | None = None,
    indexlist: list | None = None,
) -> list | None:
    """按颜色区间查询主题颜色索引。

    ``indexlist`` 过滤主题索引。返回
    ``[[themeindex, colorindex], ...]``。
    """
    if not isinstance(chart, dict):
        return None
    ranges = _parse_color_range(startcolor, endcolor)
    if ranges is None:
        return None
    themes = chart.get("themes")
    if not isinstance(themes, list):
        return None
    if not _valid_index_list(indexlist):
        return None

    allowed = _allowed_indices(indexlist, len(themes))
    result = []
    for index, theme in enumerate(themes):
        if allowed is not None and index not in allowed:
            continue
        if not isinstance(theme, dict):
            return None
        colors = theme.get("colorsList")
        if not isinstance(colors, list) or len(colors) != 3:
            return None
        for color_index, value in enumerate(colors):
            color = _parse_color(value)
            if color is None:
                return None
            if _color_in_range(color, ranges):
                result.append([index, color_index])
    return result


def getLinePointByColor(
    chart: dict,
    startcolor: str | list,
    endcolor: str | list | None = None,
    indexlist: list | None = None,
    canvasindex: int | None = None,
    lineindex: int | None = None,
) -> list | None:
    """按颜色区间查询线节点索引。"""
    if not isinstance(chart, dict):
        return None
    ranges = _parse_color_range(startcolor, endcolor)
    if ranges is None:
        return None
    selected = _selected_lines(chart, lineindex)
    if selected is None:
        return None
    if not _valid_index_list(indexlist):
        return None

    canvas_filter = None
    if canvasindex is not None:
        canvas = _find_canvas(chart, canvasindex)
        if canvas is None:
            return None
        canvas_filter = canvas["index"]

    result = []
    for line_index, line in selected:
        points = line.get("linePoints")
        if not isinstance(points, list):
            return None
        allowed = _allowed_indices(indexlist, len(points))
        for point_index, point in enumerate(points):
            if allowed is not None and point_index not in allowed:
                continue
            if not isinstance(point, dict):
                return None
            if canvas_filter is not None:
                point_canvas = point.get("canvasIndex")
                if not _is_int(point_canvas):
                    return None
                point_canvas = _find_canvas(chart, point_canvas)
                if point_canvas is None:
                    return None
                if point_canvas["index"] != canvas_filter:
                    continue
            color = _parse_color(point.get("color"))
            if color is None:
                return None
            if _color_in_range(color, ranges):
                result.append([line_index, point_index])
    return result


def _get_line_color_node_indexes_by_color(
    chart: dict,
    key: str,
    ranges: dict,
    indexlist: list | None,
    lineindex: int | None,
) -> list | None:
    selected = _selected_lines(chart, lineindex)
    if selected is None:
        return None
    if not _valid_index_list(indexlist):
        return None

    result = []
    for line_index, line in selected:
        nodes = line.get(key)
        if not isinstance(nodes, list):
            return None
        allowed = _allowed_indices(indexlist, len(nodes))
        for index, node in enumerate(nodes):
            if allowed is not None and index not in allowed:
                continue
            if not isinstance(node, dict):
                return None
            start_color = _parse_color(node.get("startColor"))
            end_color = _parse_color(node.get("endColor"))
            if start_color is None or end_color is None:
                return None
            if _color_in_range(start_color, ranges):
                result.append([line_index, index])
            elif _color_in_range(end_color, ranges):
                result.append([line_index, index])
    return result


def getRingPointByColor(
    chart: dict,
    startcolor: str | list,
    endcolor: str | list | None = None,
    indexlist: list | None = None,
    lineindex: int | None = None,
) -> list | None:
    """按颜色区间查询判定环索引。

    节点的 ``startColor`` 或 ``endColor`` 任一落入区间即匹配。
    """
    if not isinstance(chart, dict):
        return None
    ranges = _parse_color_range(startcolor, endcolor)
    if ranges is None:
        return None
    return _get_line_color_node_indexes_by_color(
        chart,
        "judgeRingColor",
        ranges,
        indexlist,
        lineindex,
    )


def getLineColorByColor(
    chart: dict,
    startcolor: str | list,
    endcolor: str | list | None = None,
    indexlist: list | None = None,
    lineindex: int | None = None,
) -> list | None:
    """按颜色区间查询线色覆盖索引。

    节点的 ``startColor`` 或 ``endColor`` 任一落入区间即匹配。
    """
    if not isinstance(chart, dict):
        return None
    ranges = _parse_color_range(startcolor, endcolor)
    if ranges is None:
        return None
    return _get_line_color_node_indexes_by_color(
        chart,
        "lineColor",
        ranges,
        indexlist,
        lineindex,
    )


def getCanvasPositionAt(
    chart: dict,
    time: float,
    index: int = -1,
    isRealTime: bool = False,
) -> float | None:
    """查询画布在指定时间的中线绝对 x 坐标。

    ``index`` 为画布索引，0 起，负数从末尾计算。``isRealTime=True``
    时 ``time`` 为实际秒数。查询时间晚于最后一个关键点时保持最后
    节点的值；早于第一个节点或结构非法时返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    canvas = _find_canvas(chart, index)
    if canvas is None:
        return None

    return _canvas_x_at(canvas, tick)


def getCanvasSpeedAt(
    chart: dict,
    index: int,
    time: float,
    isRealTime: bool = False,
) -> float | None:
    """查询画布在指定时间的流速。

    ``index`` 为画布索引，0 起，负数从末尾计算。``isRealTime=True``
    时 ``time`` 为实际秒数。查询时间早于首个流速节点或结构非法时返回
    ``None``；晚于最后一个节点时保持最后值。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    canvas = _find_canvas(chart, index)
    if canvas is None:
        return None

    return _canvas_speed_at(canvas.get("speedKeyPoints"), tick)


def getCameraPositionAt(
    chart: dict,
    time: float,
    isRealTime: bool = False,
) -> float | None:
    """查询摄像机在指定时间的 x 位置。

    ``isRealTime=True`` 时 ``time`` 为实际秒数。查询时间早于首个关键点
    或结构非法时返回 ``None``；晚于最后一个节点时保持最后值。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    return _key_point_value_at(camera.get("xPositionKeyPoints"), tick)


def getCameraScaleAt(
    chart: dict,
    time: float,
    isRealTime: bool = False,
) -> float | None:
    """查询摄像机在指定时间的缩放倍率。

    ``isRealTime=True`` 时 ``time`` 为实际秒数。查询时间早于首个关键点
    或结构非法时返回 ``None``；晚于最后一个节点时保持最后值。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    return _key_point_value_at(camera.get("scaleKeyPoints"), tick)


def getLinePosition(
    chart: dict,
    index: int,
    time: float,
    isAbsolutePosition: bool = False,
    isRealTime: bool = False,
) -> float | None:
    """查询引导线在指定时间的 x 坐标。

    ``index`` 为 lines 数组中的线索引，0 起，负数从末尾计算。
    ``isAbsolutePosition=False`` 时返回相对画布中线的坐标；
    ``True`` 时加上该时刻所在画布的 ``getCanvasPositionAt()``。
    ``isRealTime=True`` 时 ``time`` 为实际秒数。

    查询时间早于首个节点或晚于末个节点时返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or time < 0:
        return None
    if not _is_int(index):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = index + len(lines) if index < 0 else index
    if not 0 <= line_index < len(lines):
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    result = _line_x_at(line, tick)
    if result is None:
        return None

    position, canvas_index = result
    if not isAbsolutePosition:
        return position

    canvas_x = getCanvasPositionAt(chart, tick, index=canvas_index)
    if canvas_x is None:
        return None
    return position + canvas_x


def getLineByPoint(
    chart: dict,
    position: float | list | None = None,
    time: float | list | None = None,
    index: int | None = None,
    color: list | str | None = None,
    isAbsolutePosition: bool = False,
    isRealTime: bool = False,
) -> list | None:
    """按引导线节点位置查询节点所在的线。

    ``position`` / ``time`` 可以是单值、``[a, b]`` 区间或 ``None``。
    ``index`` 为画布索引，``None`` 表示在所有画布中查找。
    ``color`` 支持与 ``setNormalTheme()`` 相同的 HEX / 列表格式。

    ``isAbsolutePosition=True`` 时，用每个候选节点自身的 ``time`` 计算
    所在画布的中线坐标，再与 ``position - getCanvasPositionAt()`` 比较。
    返回 ``[[lineindex, pointindex], ...]``；没有匹配时返回空列表，
    参数或结构非法时返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    position_range = _parse_range(position)
    if position_range is None:
        return None

    time_range = _query_tick_range(chart, time, isRealTime)
    if time_range is None:
        return None

    canvas_filter = None
    if index is not None:
        canvas = _find_canvas(chart, index)
        if canvas is None:
            return None
        canvas_filter = canvas["index"]

    parsed_color = None
    if color is not None:
        parsed_color = _parse_color(color)
        if parsed_color is None:
            return None

    low, high = position_range
    time_low, time_high, time_single = time_range
    results = []

    for line_index, line in enumerate(lines):
        if not isinstance(line, dict):
            return None
        points = line.get("linePoints")
        if not isinstance(points, list):
            return None

        for point_index, point in enumerate(points):
            if not isinstance(point, dict):
                return None

            point_time = point.get("time")
            if not _is_finite_number(point_time) or point_time < 0:
                return None
            if not _time_matches(
                point_time,
                time_low,
                time_high,
                time_single,
            ):
                continue

            point_canvas = point.get("canvasIndex")
            if canvas_filter is not None:
                if not _is_int(point_canvas):
                    return None
                if point_canvas != canvas_filter:
                    continue

            if parsed_color is not None:
                if point.get("color") != parsed_color:
                    continue

            if low is not None:
                point_x = point.get("xPosition")
                if not _is_finite_number(point_x):
                    return None

                if isAbsolutePosition:
                    if not _is_int(point_canvas):
                        return None
                    canvas_x = getCanvasPositionAt(
                        chart,
                        point_time,
                        index=point_canvas,
                    )
                    if canvas_x is None:
                        return None
                    point_x += canvas_x

                if not _value_matches(
                    float(point_x),
                    low,
                    high,
                    low == high,
                ):
                    continue

            results.append([line_index, point_index])

    return results


def getLineByNote(
    chart: dict,
    position: float | list | None = None,
    time: float | list | None = None,
    type: int | str | None = None,
    isAbsolutePosition: bool = False,
    isRealTime: bool = False,
) -> list | None:
    """按 Note 的位置查询 Note 所在的线。

    ``position`` / ``time`` 可以是单值、``[a, b]`` 区间或 ``None``。
    ``type`` 允许 ``0``/``"tap"``、``1``/``"drag"``、``2``/``"hold"``，
    ``None`` 表示任意类型；Hold 只锚定头部。

    返回 ``[[lineindex, noteindex], ...]``；没有匹配时返回空列表，
    参数或结构非法时返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    position_range = _parse_range(position)
    if position_range is None:
        return None

    time_range = _query_tick_range(chart, time, isRealTime)
    if time_range is None:
        return None

    if type is None:
        wanted_type = None
    elif _is_int(type):
        if type not in (0, 1, 2):
            return None
        wanted_type = type
    elif isinstance(type, str):
        type_map = {"tap": 0, "drag": 1, "hold": 2}
        wanted_type = type_map.get(type.lower())
        if wanted_type is None:
            return None
    else:
        return None

    low, high = position_range
    time_low, time_high, time_single = time_range
    results = []

    for line_index, line in enumerate(lines):
        if not isinstance(line, dict):
            return None
        notes = line.get("notes")
        if not isinstance(notes, list):
            return None

        for note_index, note in enumerate(notes):
            if not isinstance(note, dict):
                return None

            note_time = note.get("time")
            if not _is_finite_number(note_time) or note_time < 0:
                return None
            if not _time_matches(
                note_time,
                time_low,
                time_high,
                time_single,
            ):
                continue

            note_type = note.get("type")
            if not _is_int(note_type) or note_type not in (0, 1, 2):
                return None
            if wanted_type is not None and note_type != wanted_type:
                continue

            if low is not None:
                line_x = getLinePosition(
                    chart,
                    line_index,
                    note_time,
                    isAbsolutePosition=isAbsolutePosition,
                )
                if line_x is None:
                    return None
                if not _value_matches(
                    line_x,
                    low,
                    high,
                    low == high,
                ):
                    continue

            results.append([line_index, note_index])

    return results


def getLineTimeRange(
    chart: dict,
    lineindex: int = -1,
    isRealTime: bool = False,
) -> list | None:
    """查询引导线首节点到尾节点的时间范围。

    返回 ``[first_time, last_time]``。``lineindex`` 为线索引，0 起，
    负数从末尾计算。``isRealTime=True`` 时返回实际秒数。线结构非法、
    索引不存在或秒数换算失败时返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None

    line = _find_line(chart, lineindex)
    if line is None:
        return None
    points = _line_points_spec(chart, line)
    if points is None:
        return None

    first = points[0]["time"]
    last = points[-1]["time"]
    if isRealTime:
        first = getSecondsAt(chart, first)
        last = getSecondsAt(chart, last)
        if first is None or last is None:
            return None
    return [float(first), float(last)]


def getNotePosition(
    chart: dict,
    lineindex: int = -1,
    noteindex: int = -1,
    isAbsolutePosition: bool = False,
) -> float | None:
    """查询 Note 头部所在位置的线 x 坐标。

    ``lineindex`` / ``noteindex`` 从 0 起，负数从末尾计算。Hold 使用头部
    时间。``isAbsolutePosition=True`` 时返回绝对 x，否则返回相对画布中线
    的 x。结构非法、索引不存在或 Note 时间越界时返回 ``None``。
    """
    context = _note_context(chart, lineindex, noteindex)
    if context is None:
        return None
    line_position, _, _, _, head_time, _, _ = context
    return getLinePosition(
        chart,
        line_position,
        head_time,
        isAbsolutePosition=isAbsolutePosition,
    )


def getNoteCanvas(
    chart: dict,
    lineindex: int = -1,
    noteindex: int = -1,
    isHoldTail: bool = False,
) -> int | None:
    """查询 Note 对应的画布索引。

    ``lineindex`` / ``noteindex`` 从 0 起，负数从末尾计算。默认返回 Note
    头部所在画布；``isHoldTail=True`` 且 Note 是 Hold 时，返回
    ``otherInformations[1]`` 中记录的尾部画布。非 Hold 会忽略
    ``isHoldTail``。结构非法、索引不存在或画布无效时返回 ``None``。
    """
    context = _note_context(chart, lineindex, noteindex)
    if context is None:
        return None
    _, _, note, note_type, head_time, points, times = context

    if note_type == 2 and isHoldTail:
        extra = note.get("otherInformations")
        if not isinstance(extra, list) or len(extra) != 3:
            return None
        tail_time = extra[0]
        if (
            not _is_finite_number(tail_time)
            or tail_time <= head_time
            or tail_time > times[-1]
        ):
            return None
        raw_canvas = extra[1]
        canvas_index = _canvas_ref(raw_canvas)
        if canvas_index is None or canvas_index < 0:
            return None
        canvas = _find_canvas(chart, canvas_index)
        return None if canvas is None else int(canvas["index"])

    position = bisect.bisect_right(times, head_time) - 1
    if position < 0:
        return None
    canvas_index = points[position]["canvasIndex"]
    if not _is_int(canvas_index) or canvas_index < 0:
        return None
    return int(canvas_index)


def _color_list(color: object) -> list[int]:
    """把颜色 dict 或列表转成 ``[r, g, b, a]``。"""
    if isinstance(color, dict):
        return [color["r"], color["g"], color["b"], color["a"]]
    return list(color)


def _lerp_color(start: object, end: object, ratio: float) -> list[int]:
    """对两个颜色做逐通道线性插值。"""
    start_values = _color_list(start)
    end_values = _color_list(end)
    if ratio <= 0.0:
        return start_values
    if ratio >= 1.0:
        return end_values
    return [
        _round_color_channel(
            start_values[index]
            + (end_values[index] - start_values[index]) * ratio
        )
        for index in range(4)
    ]


def _base_color_at_tick(
    chart: dict,
    index: object,
    tick: float,
    position: object,
    is_absolute: bool,
) -> list[int] | None:
    """按已换算的 tick 查询线节点基础色。"""
    line = _find_line(chart, index)
    if line is None:
        return None

    points = _line_points_spec(chart, line)
    if points is None:
        return None

    times = [point["time"] for point in points]
    if tick < times[0] or tick > times[-1]:
        return None

    left = bisect.bisect_left(times, tick)
    right = bisect.bisect_right(times, tick)

    # 不在节点时间：使用前后节点做时间插值。
    if left == right:
        if left == 0 or left == len(points):
            return None
        start = points[left - 1]
        end = points[left]
        span = end["time"] - start["time"]
        if span <= 0.0:
            return None
        ratio = (tick - start["time"]) / span
        return _lerp_color(start["color"], end["color"], ratio)

    # 正好只有一个节点：直接返回该节点颜色。
    if right - left == 1:
        return _color_list(points[left]["color"])

    # 同一时间有多个节点：必须用 position 选择最上层线段。
    if position is None or not _is_finite_number(position):
        return None

    result = None
    for point_index in range(left, right - 1):
        start = points[point_index]
        end = points[point_index + 1]
        start_x = start["xPosition"]
        end_x = end["xPosition"]

        if is_absolute:
            start_canvas_x = getCanvasPositionAt(
                chart,
                tick,
                index=start["canvasIndex"],
            )
            end_canvas_x = getCanvasPositionAt(
                chart,
                tick,
                index=end["canvasIndex"],
            )
            if start_canvas_x is None or end_canvas_x is None:
                return None
            start_x += start_canvas_x
            end_x += end_canvas_x

        if not min(start_x, end_x) <= position <= max(start_x, end_x):
            continue

        if start_x == end_x:
            # 零宽线段按后一个节点的颜色处理。
            result = _color_list(end["color"])
        else:
            ratio = (position - start_x) / (end_x - start_x)
            result = _lerp_color(start["color"], end["color"], ratio)

    return result


def getBaseColor(
    chart: dict,
    index: int,
    time: float,
    position: float | None = None,
    isRealTime: bool = False,
    isAbsolutePosition: bool = False,
) -> list[int] | None:
    """查询指定引导线在指定时间/位置的基础色。

    ``time`` 必须在线的首节点与尾节点时间之间。该时间没有节点时忽略
    ``position``，在前后节点之间按时间插值；正好一个节点时直接返回该
    节点颜色；同一时间有多个节点时必须提供 ``position``，按节点存储
    顺序连接同时间节点，并返回覆盖该位置的最后一层线段的颜色。

    ``isRealTime=True`` 时 ``time`` 是实际秒数。``isAbsolutePosition``
    为真时，用每个节点自己的画布计算绝对 x 坐标。失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None
    return _base_color_at_tick(
        chart,
        index,
        tick,
        position,
        isAbsolutePosition,
    )


def _cover_color_at_tick(
    chart: dict,
    index: object,
    tick: float,
) -> list[int] | None:
    """按已换算的 tick 查询线色覆盖色。"""
    line = _find_line(chart, index)
    if line is None:
        return None

    nodes = _color_change_specs(line.get("lineColor"), non_empty=True)
    if nodes is None or not nodes:
        return None

    times = [node["time"] for node in nodes]
    position = bisect.bisect_right(times, tick) - 1

    # 早于第一个节点：保持第一个节点的 startColor。
    if position < 0:
        return _color_list(nodes[0]["startColor"])

    # 正好命中节点，或已到最后节点之后：使用该节点 startColor。
    if times[position] == tick or position == len(nodes) - 1:
        return _color_list(nodes[position]["startColor"])

    start = nodes[position]
    end = nodes[position + 1]
    span = end["time"] - start["time"]
    if span <= 0.0:
        return None
    ratio = (tick - start["time"]) / span
    return _lerp_color(start["startColor"], start["endColor"], ratio)


def getCoverColor(
    chart: dict,
    index: int,
    time: float,
    isRealTime: bool = False,
) -> list[int] | None:
    """查询指定引导线在指定时间的线色覆盖色。

    ``lineColor`` 必须非空；覆盖色节点可以位于引导线时间范围之外，
    因此 ``time`` 只要求大于等于 0。早于第一个节点时返回第一个节点的
    ``startColor``；晚于或等于最后一个节点时返回最后一个节点的
    ``startColor``；两个节点之间按 ``startColor -> endColor`` 线性插值。
    ``isRealTime=True`` 时 ``time`` 是实际秒数。失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None
    return _cover_color_at_tick(chart, index, tick)


def getMixColor(
    chart: dict,
    index: int,
    currenttime: float,
    querytime: float | None = None,
    position: float | None = None,
    isRealCurrentTime: bool = False,
    isRealQueryTime: bool = False,
    isAbsolutePosition: bool = False,
) -> list[int] | None:
    """查询指定引导线在指定位置的混合色。

    ``querytime`` 处的基础色作为 basecolor，``currenttime`` 处的线色
    覆盖色作为 covercolor，返回 ``mixColor(base, cover)``。``querytime``
    为 ``None`` 时使用 ``currenttime``。``querytime`` 必须位于线的首尾
    节点时间之间；``currenttime`` 只需大于等于 0。任一步失败返回
    ``None``。
    """
    if not isinstance(chart, dict):
        return None

    current_tick = _query_tick(chart, currenttime, isRealCurrentTime)
    if current_tick is None:
        return None

    if querytime is None:
        query_tick = current_tick
    else:
        query_tick = _query_tick(chart, querytime, isRealQueryTime)
        if query_tick is None:
            return None

    base = _base_color_at_tick(
        chart,
        index,
        query_tick,
        position,
        isAbsolutePosition,
    )
    if base is None:
        return None

    cover = _cover_color_at_tick(chart, index, current_tick)
    if cover is None:
        return None

    return mixColor(base, cover)
