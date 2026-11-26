"""谱面查询工具。"""

from __future__ import annotations

from ._exception_wrapper import install_exception_api
from ._failure import fail, last_failure

import bisect
import math

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
from .chart import (
    _chart_failure,
    _index_failure,
    _structure_failure,
    _type_failure,
    _value_failure,
    mixColor,
)
from ._shade_opacity_data import SHADE_OPACITY_ALPHA

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
    "getRingColor",
    "getMixColor",
    "getLinePosition",
    "getLineByPoint",
    "getLineByNote",
    "getLineTimeRange",
    "getNotePosition",
    "getNoteCanvas",
    "getXYRatio",
    "getXYRatioByChart",
    "getXBorder",
    "getXBorderByChart",
    "getYBorder",
    "getYBorderByChart",
    "getGameScale",
    "getLineWidth",
    "getRingRadius",
    "getShadeOpacity",
]


def getFileVersion(chart: dict) -> int | None:
    """查询谱面文件版本。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    value = chart.get("fileVersion")
    if not _is_int(value):
        return _type_failure(
            None,
            "fileVersion",
            value,
            "int",
            path=["fileVersion"],
        )
    return value


def getDelay(chart: dict) -> int | None:
    """查询谱面延迟（毫秒）。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    value = chart.get("chartDelayMs")
    if not _is_int(value):
        return _type_failure(
            None,
            "chartDelayMs",
            value,
            "int",
            path=["chartDelayMs"],
        )
    return value


def getBaseBpm(chart: dict) -> float | None:
    """查询基准 BPM。缺失或非正数时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    value = chart.get("bPM")
    if not _is_finite_number(value) or value <= 0:
        return _value_failure(
            None,
            "bPM",
            value,
            "有限数且 > 0",
            path=["bPM"],
            code="bpm.invalid",
        )
    return float(value)


def getLineCount(chart: dict) -> int | None:
    """查询引导线数量。``lines`` 结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )
    return len(lines)


def getCanvasCount(chart: dict) -> int | None:
    """查询画布数量。``canvasMoves`` 结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return _structure_failure(
            None,
            ["canvasMoves"],
            "list",
            actual=type(canvas_moves).__name__,
        )
    return len(canvas_moves)


def getBpmShiftCount(chart: dict) -> int | None:
    """查询 BPM 变化节点数量。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list):
        return _structure_failure(
            None,
            ["bpmShifts"],
            "list",
            actual=type(shifts).__name__,
        )
    return len(shifts)


def getRiztimeCount(chart: dict) -> int | None:
    """查询 Riztime 数量。结构非法时返回 ``None``。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    challenge_times = chart.get("challengeTimes")
    if not isinstance(challenge_times, list):
        return _structure_failure(
            None,
            ["challengeTimes"],
            "list",
            actual=type(challenge_times).__name__,
        )
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
        return _chart_failure()
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )

    if endindex is None:
        index = _resolve_single_index(
            startindex,
            len(lines),
            parameter="startindex",
        )
        if index is None:
            return None
        line = lines[index]
        if not isinstance(line, dict):
            return _structure_failure(
                None,
                ["lines", index],
                "线 dict",
                actual=type(line).__name__,
            )
        notes = line.get("notes")
        if not isinstance(notes, list):
            return _structure_failure(
                None,
                ["lines", index, "notes"],
                "list",
                actual=type(notes).__name__,
            )
        return len(notes)

    indices = _resolve_range_indices(startindex, endindex, len(lines))
    if indices is None:
        return None

    total = 0
    for index in indices:
        line = lines[index]
        if not isinstance(line, dict):
            return _structure_failure(
                None,
                ["lines", index],
                "线 dict",
                actual=type(line).__name__,
            )
        notes = line.get("notes")
        if not isinstance(notes, list):
            return _structure_failure(
                None,
                ["lines", index, "notes"],
                "list",
                actual=type(notes).__name__,
            )
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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return _structure_failure(
            None,
            ["bPM", "bpmShifts"],
            "可用的 BPM 时间轴（bPM > 0 且 bpmShifts[0].time == 0）",
            actual={"bPM": chart.get("bPM"), "bpmShifts": chart.get("bpmShifts")},
            message="谱面 BPM 时间轴非法，无法查询 BPM",
        )
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
            return fail(
                None,
                f"实际秒数 time={time!r} 无法换算为 tick",
                code="time.conversion_failed",
                parameter="time",
                actual=time,
                expected="可换算的非负 tick",
                path=["bpmShifts"],
            )
    else:
        tick = float(time)

    position = bisect.bisect_right(times, tick) - 1
    if position < 0:
        return _value_failure(
            None,
            "time",
            tick,
            f">= {times[0]!r}",
            message=f"时间 tick={tick!r} 早于第一个 BPM 节点 {times[0]!r}",
            path=["bpmShifts"],
            code="time.out_of_range",
        )
    return float(base_bpm * values[position])


def getSecondsAt(chart: dict, tick: float) -> float | None:
    """查询指定 tick 对应的绝对秒数。

    ``tick`` 必须大于等于 0。谱面必须在 ``time=0.0`` 处有一个 BPM
    节点；查询晚于最后一个 BPM 节点时继续按最后一个 BPM 节点计算。
    失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return _chart_failure()
    if not _is_finite_number(tick) or tick < 0:
        return _value_failure(None, "tick", tick, "有限数且 >= 0")

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return _structure_failure(
            None,
            ["bPM", "bpmShifts"],
            "可用的 BPM 时间轴（bPM > 0 且 bpmShifts[0].time == 0）",
            actual={"bPM": chart.get("bPM"), "bpmShifts": chart.get("bpmShifts")},
            message="谱面 BPM 时间轴非法，无法换算秒数",
        )
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
        return _chart_failure()
    if not _is_finite_number(seconds) or seconds < 0:
        return _value_failure(None, "seconds", seconds, "有限数且 >= 0")

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return _structure_failure(
            None,
            ["bPM", "bpmShifts"],
            "可用的 BPM 时间轴（bPM > 0 且 bpmShifts[0].time == 0）",
            actual={"bPM": chart.get("bPM"), "bpmShifts": chart.get("bpmShifts")},
            message="谱面 BPM 时间轴非法，无法换算 tick",
        )
    base_bpm, times, values, floor_positions = timeline

    tick = _tick_at_realtime(
        float(seconds),
        base_bpm,
        times,
        values,
        floor_positions,
    )
    if tick is None or tick < 0:
        return fail(
            None,
            f"实际秒数 seconds={seconds!r} 无法换算为非负 tick",
            code="time.conversion_failed",
            parameter="seconds",
            actual=seconds,
            expected="可换算的非负 tick",
            path=["bpmShifts"],
        )
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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")

    query_time = float(time)

    if canvasindex is None:
        timeline = _get_bpm_timeline(chart)
        if timeline is None:
            return _structure_failure(
                None,
                ["bPM", "bpmShifts"],
                "可用的 BPM 时间轴（bPM > 0 且 bpmShifts[0].time == 0）",
                actual={"bPM": chart.get("bPM"), "bpmShifts": chart.get("bpmShifts")},
                message="谱面 BPM 时间轴非法，无法查询 floorPosition",
            )
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
        if result is None:
            return fail(
                None,
                "无法按 BPM 时间轴计算 floorPosition",
                code="bpm.floor_calculation_failed",
                parameter="time",
                actual=query_time,
                expected="可计算的 BPM 时间轴",
                path=["bpmShifts"],
            )
        return float(result)

    if not _is_int(canvasindex):
        return _type_failure(None, "canvasindex", canvasindex, "int 或 None")

    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return _structure_failure(
            None,
            ["canvasMoves"],
            "list",
            actual=type(canvas_moves).__name__,
        )

    canvas = None
    for item in canvas_moves:
        if isinstance(item, dict) and item.get("index") == canvasindex:
            canvas = item
            break
    if canvas is None:
        return fail(
            None,
            f"画布索引 canvasindex={canvasindex!r} 不存在",
            code="canvas.not_found",
            parameter="canvasindex",
            actual=canvasindex,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )

    if isRealTime:
        timeline = _get_bpm_timeline(chart)
        if timeline is None:
            return _structure_failure(
                None,
                ["bPM", "bpmShifts"],
                "可用的 BPM 时间轴（bPM > 0 且 bpmShifts[0].time == 0）",
                actual={"bPM": chart.get("bPM"), "bpmShifts": chart.get("bpmShifts")},
                message="谱面 BPM 时间轴非法，无法换算实际时间",
            )
        base_bpm, times, values, floor_positions = timeline
        tick = _tick_at_realtime(
            query_time,
            base_bpm,
            times,
            values,
            floor_positions,
        )
        if tick is None:
            return fail(
                None,
                f"实际秒数 time={time!r} 无法换算为 tick",
                code="time.conversion_failed",
                parameter="time",
                actual=time,
                expected="可换算的非负 tick",
                path=["bpmShifts"],
            )
    else:
        tick = query_time

    result = _canvas_floor_position(chart, canvas, tick)
    if result is None:
        return _structure_failure(
            None,
            ["canvasMoves", canvas.get("index"), "speedKeyPoints"],
            "可计算 floorPosition 的画布流速节点",
            actual=canvas.get("speedKeyPoints"),
            message="画布流速时间轴非法，无法计算 floorPosition",
        )
    return float(result)


def _resolve_single_index(
    index: object,
    length: int,
    parameter: str = "index",
) -> int | None:
    if not _is_int(index):
        return _type_failure(
            None,
            parameter,
            index,
            "int（负数从末尾计算）",
        )
    position = index + length if index < 0 else index
    if 0 <= position < length:
        return position
    return _index_failure(None, parameter, index, length)


def _resolve_range_indices(
    startindex: object,
    endindex: object,
    length: int,
) -> list[int] | None:
    if not _is_int(startindex) or not _is_int(endindex):
        bad_key = "startindex" if not _is_int(startindex) else "endindex"
        bad_value = startindex if bad_key == "startindex" else endindex
        return _type_failure(
            None,
            bad_key,
            bad_value,
            "int（负数从末尾计算）",
        )
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
        return _structure_failure(
            None,
            ["items"],
            "查询目标集合必须是 list",
            actual=type(items).__name__,
        )
    if endindex is None:
        index = _resolve_single_index(
            startindex,
            len(items),
            parameter="startindex",
        )
        if index is None:
            return None
        item = builder(items[index])
        if item is None:
            if last_failure() is None:
                return fail(
                    None,
                    f"查询集合第 {index} 项结构非法",
                    code="query.item_invalid",
                    actual=items[index],
                    expected="符合对应查询规格的对象",
                    path=["items", index],
                )
            return None
        return item

    indices = _resolve_range_indices(startindex, endindex, len(items))
    if indices is None:
        return None

    result = []
    for index in indices:
        item = builder(items[index])
        if item is None:
            if last_failure() is None:
                return fail(
                    None,
                    f"查询集合第 {index} 项结构非法",
                    code="query.item_invalid",
                    actual=items[index],
                    expected="符合对应查询规格的对象",
                    path=["items", index],
                )
            return None
        result.append(item)
    return result


def _valid_index_list(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, list):
        _type_failure(
            None,
            "indexlist",
            value,
            "list[int] 或 None",
        )
        return False
    for index, item in enumerate(value):
        if not _is_int(item):
            _type_failure(
                None,
                f"indexlist[{index}]",
                item,
                "int",
                path=["indexlist", index],
            )
            return False
    return True


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
        return _type_failure(None, "keyPoint", value, "关键点 dict")
    time = value.get("time")
    key_value = value.get("value")
    ease_type = value.get("easeType")
    if not _is_finite_number(time) or time < 0:
        return _value_failure(
            None,
            "time",
            time,
            "有限数且 >= 0",
            path=["time"],
        )
    if not _is_finite_number(key_value):
        return _type_failure(None, "value", key_value, "有限数", path=["value"])
    if not _is_int(ease_type) or not 0 <= ease_type <= 18:
        return _value_failure(
            None,
            "easeType",
            ease_type,
            "0..18 的 int",
            path=["easeType"],
        )
    return {
        "time": float(time),
        "value": float(key_value),
        "easeType": ease_type,
    }


def _bpm_shift_spec(value: object) -> dict | None:
    spec = _key_point_spec(value)
    if spec is None:
        return None
    if spec["value"] <= 0:
        return _value_failure(
            None,
            "value",
            spec["value"],
            "有限数且 > 0",
            path=["value"],
            code="bpm.non_positive",
        )
    return spec


def _key_point_specs(
    values: object,
    non_empty: bool = True,
) -> list | None:
    if not isinstance(values, list):
        return _structure_failure(
            None,
            ["keyPoints"],
            "关键点列表（list）",
            actual=type(values).__name__,
        )
    if non_empty and not values:
        return fail(
            None,
            "关键点列表不能为空",
            code="keypoints.empty",
            actual=[],
            expected="至少一个关键点",
            path=["keyPoints"],
        )
    result = []
    previous_time = None
    for index, value in enumerate(values):
        spec = _key_point_spec(value)
        if spec is None:
            return fail(
                None,
                f"关键点列表第 {index} 项结构非法",
                code="keypoints.item_invalid",
                actual=value,
                expected="有效 time、value、easeType 的关键点",
                path=["keyPoints", index],
            )
        if previous_time is not None and spec["time"] < previous_time:
            return _structure_failure(
                None,
                ["keyPoints"],
                "time 非递减",
                actual=[item.get("time") for item in values],
                message="关键点列表的 time 必须非递减",
            )
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
        return _type_failure(None, "colorPoint", value, "颜色节点 dict")
    time = value.get("time")
    if not _is_finite_number(time) or time < 0:
        return _value_failure(
            None,
            "time",
            time,
            "有限数且 >= 0",
            path=["time"],
        )
    start_color = _parse_color(value.get("startColor"))
    if start_color is None:
        return fail(
            None,
            "startColor 不是可解析的颜色",
            code="color.invalid",
            parameter="startColor",
            actual=value.get("startColor"),
            expected="HEX 字符串或 RGB(A) 列表",
            path=["startColor"],
        )
    end_color = _parse_color(value.get("endColor"))
    if end_color is None:
        return fail(
            None,
            "endColor 不是可解析的颜色",
            code="color.invalid",
            parameter="endColor",
            actual=value.get("endColor"),
            expected="HEX 字符串或 RGB(A) 列表",
            path=["endColor"],
        )
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
        return _structure_failure(
            None,
            ["colorPoints"],
            "颜色节点列表（list）",
            actual=type(values).__name__,
        )
    if non_empty and not values:
        return fail(
            None,
            "颜色节点列表不能为空",
            code="colors.empty",
            actual=[],
            expected="至少一个颜色节点",
            path=["colorPoints"],
        )
    result = []
    previous_time = None
    for index, value in enumerate(values):
        spec = _color_change_spec(value)
        if spec is None:
            return fail(
                None,
                f"颜色节点列表第 {index} 项结构非法",
                code="colors.item_invalid",
                actual=value,
                expected="有效 time、startColor、endColor 的颜色节点",
                path=["colorPoints", index],
            )
        if previous_time is not None and spec["time"] < previous_time:
            return _structure_failure(
                None,
                ["colorPoints"],
                "time 非递减",
                actual=[item.get("time") for item in values],
                message="颜色节点列表的 time 必须非递减",
            )
        previous_time = spec["time"]
        result.append(spec)
    return result


def _parse_color_range(
    startcolor: object,
    endcolor: object,
) -> dict | None:
    start = _parse_color(startcolor)
    if start is None:
        return fail(
            None,
            "参数 startcolor 不是可解析的颜色",
            code="color.invalid",
            parameter="startcolor",
            actual=startcolor,
            expected="HEX 字符串或 RGB(A) 列表",
        )
    if endcolor is None:
        end = dict(start)
    else:
        end = _parse_color(endcolor)
        if end is None:
            return fail(
                None,
                "参数 endcolor 不是可解析的颜色",
                code="color.invalid",
                parameter="endcolor",
                actual=endcolor,
                expected="HEX 字符串或 RGB(A) 列表",
            )

    ranges = {}
    for channel in ("r", "g", "b", "a"):
        low = start[channel]
        high = end[channel]
        if high < low:
            return fail(
                None,
                f"颜色通道 {channel} 的下界 {low!r} 大于上界 {high!r}",
                code="color.range_reversed",
                parameter="startcolor/endcolor",
                actual={channel: [low, high]},
                expected="每个通道 startColor <= endColor",
            )
        ranges[channel] = (low, high)
    return ranges


def _color_in_range(color: dict, ranges: dict) -> bool:
    return all(
        ranges[channel][0] <= color[channel] <= ranges[channel][1]
        for channel in ("r", "g", "b", "a")
    )


def _theme_spec(value: object) -> dict | None:
    if not isinstance(value, dict):
        return _type_failure(None, "theme", value, "主题 dict")
    colors = value.get("colorsList")
    if not isinstance(colors, list) or len(colors) != 3:
        return _structure_failure(
            None,
            ["colorsList"],
            "长度为 3 的颜色列表",
            actual=colors,
        )
    result = []
    for index, color in enumerate(colors):
        parsed = _parse_color(color)
        if parsed is None:
            return fail(
                None,
                f"colorsList[{index}] 不是可解析的颜色",
                code="color.invalid",
                parameter=f"colorsList[{index}]",
                actual=color,
                expected="HEX 字符串或 RGB(A) 列表",
                path=["colorsList", index],
            )
        result.append(_color_list(parsed))
    return {"colorsList": result}


def _challenge_time_spec(value: object) -> dict | None:
    if not isinstance(value, dict):
        return _type_failure(None, "challengeTime", value, "挑战时间 dict")
    result = {}
    for key in ("checkPoint", "start", "end", "transTime"):
        item = value.get(key)
        if not _is_finite_number(item):
            return _type_failure(
                None,
                key,
                item,
                "有限数",
                path=[key],
            )
        result[key] = float(item)
    if result["end"] < result["start"]:
        return _value_failure(
            None,
            "end",
            result["end"],
            f">= start（start={result['start']!r}）",
            message=(
                f"end={result['end']!r} 不能小于 start={result['start']!r}"
            ),
            path=["end"],
            code="range.reversed",
        )
    if result["transTime"] < 0:
        return _value_failure(
            None,
            "transTime",
            result["transTime"],
            ">= 0",
            path=["transTime"],
        )
    return result


def _riztime_specs(chart: dict) -> list | None:
    challenge_times = chart.get("challengeTimes")
    themes = chart.get("themes")
    if not isinstance(challenge_times, list):
        return _structure_failure(
            None,
            ["challengeTimes"],
            "list",
            actual=type(challenge_times).__name__,
        )
    if not isinstance(themes, list):
        return _structure_failure(
            None,
            ["themes"],
            "list",
            actual=type(themes).__name__,
        )
    if len(themes) != len(challenge_times) + 1:
        return _structure_failure(
            None,
            ["themes", "challengeTimes"],
            "len(themes) == len(challengeTimes) + 1",
            actual=[len(themes), len(challenge_times)],
        )

    result = []
    for index, challenge in enumerate(challenge_times):
        theme_spec = _theme_spec(themes[index + 1])
        if theme_spec is None:
            return fail(
                None,
                f"themes[{index + 1}] 主题结构非法",
                code="theme.invalid",
                actual=themes[index + 1],
                expected="包含 3 个有效颜色的主题",
                path=["themes", index + 1],
            )
        challenge_spec = _challenge_time_spec(challenge)
        if challenge_spec is None:
            return fail(
                None,
                f"challengeTimes[{index}] 结构非法",
                code="riztime.invalid",
                actual=challenge,
                expected="有效 checkPoint/start/end/transTime 的挑战时间",
                path=["challengeTimes", index],
            )
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
        return _type_failure(None, "linePoint", value, "线节点 dict")
    time = value.get("time")
    x_position = value.get("xPosition")
    canvas_index = value.get("canvasIndex")
    ease_type = value.get("easeType")
    if not _is_finite_number(time) or time < 0:
        return _value_failure(
            None,
            "time",
            time,
            "有限数且 >= 0",
            path=["time"],
        )
    if not _is_finite_number(x_position):
        return _type_failure(None, "xPosition", x_position, "有限数", path=["xPosition"])
    if not _is_int(canvas_index):
        return _type_failure(None, "canvasIndex", canvas_index, "int", path=["canvasIndex"])
    canvas = _find_canvas(chart, canvas_index)
    if canvas is None:
        return fail(
            None,
            f"画布索引 canvasIndex={canvas_index!r} 不存在",
            code="canvas.not_found",
            parameter="canvasIndex",
            actual=canvas_index,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )
    if not _is_int(ease_type) or not 0 <= ease_type <= 18:
        return _value_failure(
            None,
            "easeType",
            ease_type,
            "0..18 的 int",
            path=["easeType"],
        )
    color = _parse_color(value.get("color"))
    if color is None:
        return fail(
            None,
            "color 不是可解析的颜色",
            code="color.invalid",
            parameter="color",
            actual=value.get("color"),
            expected="HEX 字符串或 RGB(A) 列表",
            path=["color"],
        )
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
        return _structure_failure(
            None,
            ["linePoints"],
            "至少两个线节点的列表",
            actual=points,
        )
    result = []
    previous_time = None
    for index, point in enumerate(points):
        spec = _line_point_export_spec(chart, point)
        if spec is None:
            return fail(
                None,
                f"linePoints[{index}] 不是有效线节点",
                code="line.point_invalid",
                actual=point,
                expected="有效 time、xPosition、canvasIndex、easeType、color",
                path=["linePoints", index],
            )
        if previous_time is not None and spec["time"] < previous_time:
            return _structure_failure(
                None,
                ["linePoints"],
                "time 非递减",
                actual=[item.get("time") for item in points],
                message="linePoints 的 time 必须非递减",
            )
        previous_time = spec["time"]
        result.append(spec)
    return result


def _note_export_spec(line_times: list, value: object) -> dict | None:
    if not isinstance(value, dict) or len(line_times) < 2:
        return _type_failure(None, "note", value, "Note dict 且线至少有两个节点")
    note_type = value.get("type")
    head_time = value.get("time")
    if not _is_int(note_type) or note_type not in (0, 1, 2):
        return _value_failure(
            None,
            "type",
            note_type,
            "0、1 或 2",
            path=["type"],
            code="note.type_invalid",
        )
    if not _is_finite_number(head_time) or head_time < 0:
        return _value_failure(
            None,
            "time",
            head_time,
            "有限数且 >= 0",
            path=["time"],
            code="time.invalid",
        )
    if head_time < line_times[0] or head_time > line_times[-1]:
        return _value_failure(
            None,
            "time",
            head_time,
            f"{line_times[0]!r}..{line_times[-1]!r}",
            message=(
                f"Note time={head_time!r} 不在线时间 "
                f"{line_times[0]!r}..{line_times[-1]!r} 范围内"
            ),
            path=["time"],
            code="time.out_of_range",
        )

    if note_type == 2:
        extra = value.get("otherInformations")
        if not isinstance(extra, list) or len(extra) != 3:
            return _structure_failure(
                None,
                ["otherInformations"],
                "Hold 的三元素尾部信息",
                actual=extra,
            )
        tail_time = extra[0]
        if not _is_finite_number(tail_time):
            return _type_failure(
                None,
                "endtime",
                tail_time,
                "有限数",
                path=["otherInformations", 0],
            )
        if tail_time <= head_time or tail_time > line_times[-1]:
            return _value_failure(
                None,
                "endtime",
                tail_time,
                f"> {head_time!r} 且 <= {line_times[-1]!r}",
                message="Hold 尾部时间非法",
                path=["otherInformations", 0],
                code="time.out_of_range",
            )
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
        return _structure_failure(
            None,
            ["notes"],
            "list",
            actual=type(values).__name__,
        )
    result = []
    previous_time = None
    for index, value in enumerate(values):
        spec = _note_export_spec(line_times, value)
        if spec is None:
            return fail(
                None,
                f"notes[{index}] 不是有效 Note",
                code="note.invalid",
                actual=value,
                expected="有效 time、type 和 Hold 结束时间",
                path=["notes", index],
            )
        if previous_time is not None and spec["time"] < previous_time:
            return _structure_failure(
                None,
                ["notes"],
                "time 非递减",
                actual=[item.get("time") for item in values],
                message="notes 的 time 必须非递减",
            )
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
        return _type_failure(None, "line", value, "线 dict")
    point_specs = _line_points_spec(chart, value)
    if point_specs is None:
        return None
    line_times = [point["time"] for point in point_specs]

    ring_specs = _color_change_specs(
        value.get("judgeRingColor"),
        non_empty=True,
    )
    if ring_specs is None:
        return fail(
            None,
            "judgeRingColor 至少需要一个有效颜色节点",
            code="line.ring_invalid",
            actual=value.get("judgeRingColor"),
            expected="非空有效颜色节点列表",
            path=["judgeRingColor"],
        )

    note_specs = _note_specs(line_times, value.get("notes"))
    if note_specs is None:
        return None

    color_specs = _color_change_specs(value.get("lineColor"))
    if color_specs is None:
        return fail(
            None,
            "lineColor 必须为有效颜色节点列表",
            code="line.color_invalid",
            actual=value.get("lineColor"),
            expected="有效颜色节点列表",
            path=["lineColor"],
        )

    return {
        "linePoints": point_specs,
        "notes": note_specs,
        "judgeRingColor": ring_specs,
        "lineColor": color_specs,
    }


def _canvas_spec(chart: dict, value: object) -> dict | None:
    if not isinstance(value, dict):
        return _type_failure(None, "canvas", value, "画布 dict")
    index = value.get("index")
    if not _is_int(index):
        return _type_failure(None, "index", index, "int")
    canvas = _find_canvas(chart, index)
    if canvas is None:
        return fail(
            None,
            f"画布索引 index={index!r} 不存在",
            code="canvas.not_found",
            parameter="index",
            actual=index,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )
    x_points = _key_point_specs(canvas.get("xPositionKeyPoints"))
    speed_points = _key_point_specs(canvas.get("speedKeyPoints"))
    if x_points is None:
        return _structure_failure(
            None,
            ["canvasMoves", index, "xPositionKeyPoints"],
            "time 非递减的画布位置关键点列表",
            actual=canvas.get("xPositionKeyPoints"),
        )
    if speed_points is None:
        return _structure_failure(
            None,
            ["canvasMoves", index, "speedKeyPoints"],
            "time 非递减的画布流速关键点列表",
            actual=canvas.get("speedKeyPoints"),
        )
    return {
        "index": canvas["index"],
        "xPositionKeyPoints": x_points,
        "speedKeyPoints": speed_points,
    }


def _camera_spec(chart: dict) -> dict | None:
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return _structure_failure(
            None,
            ["cameraMove"],
            "dict",
            actual=type(camera).__name__,
        )
    scale_points = _key_point_specs(camera.get("scaleKeyPoints"))
    x_points = _key_point_specs(camera.get("xPositionKeyPoints"))
    if scale_points is None:
        return _structure_failure(
            None,
            ["cameraMove", "scaleKeyPoints"],
            "time 非递减的摄像机缩放关键点列表",
            actual=camera.get("scaleKeyPoints"),
        )
    if x_points is None:
        return _structure_failure(
            None,
            ["cameraMove", "xPositionKeyPoints"],
            "time 非递减的摄像机位置关键点列表",
            actual=camera.get("xPositionKeyPoints"),
        )
    return {
        "scaleKeyPoints": scale_points,
        "xPositionKeyPoints": x_points,
    }


def _find_line(chart: dict, index: object) -> dict | None:
    if not isinstance(chart, dict):
        return _chart_failure()
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )
    position = _resolve_single_index(
        index,
        len(lines),
        parameter="lineindex",
    )
    if position is None:
        return None
    line = lines[position]
    if not isinstance(line, dict):
        return _structure_failure(
            None,
            ["lines", position],
            "线 dict",
            actual=type(line).__name__,
        )
    return line


def _note_context(
    chart: dict,
    lineindex: object,
    noteindex: object,
) -> tuple[int, dict, dict, int, float, list, list] | None:
    """定位 Note，并返回线索引、Note、头部时间与线节点规格。"""
    if not isinstance(chart, dict):
        return _chart_failure()

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )
    line_position = _resolve_single_index(
        lineindex,
        len(lines),
        parameter="lineindex",
    )
    if line_position is None:
        return None
    line = lines[line_position]
    if not isinstance(line, dict):
        return _structure_failure(
            None,
            ["lines", line_position],
            "线 dict",
            actual=type(line).__name__,
        )

    notes = line.get("notes")
    if not isinstance(notes, list):
        return _structure_failure(
            None,
            ["lines", line_position, "notes"],
            "list",
            actual=type(notes).__name__,
        )
    note_position = _resolve_single_index(
        noteindex,
        len(notes),
        parameter="noteindex",
    )
    if note_position is None:
        return None
    note = notes[note_position]
    if not isinstance(note, dict):
        return _structure_failure(
            None,
            ["lines", line_position, "notes", note_position],
            "Note dict",
            actual=type(note).__name__,
        )

    note_type = note.get("type")
    if not _is_int(note_type) or note_type not in (0, 1, 2):
        return _value_failure(
            None,
            "type",
            note_type,
            "0、1 或 2",
            path=["lines", line_position, "notes", note_position, "type"],
            code="note.type_invalid",
        )
    head_time = note.get("time")
    if not _is_finite_number(head_time) or head_time < 0:
        return _value_failure(
            None,
            "time",
            head_time,
            "有限数且 >= 0",
            path=["lines", line_position, "notes", note_position, "time"],
            code="time.invalid",
        )

    points = _line_points_spec(chart, line)
    if points is None:
        return None
    times = [point["time"] for point in points]
    if head_time < times[0] or head_time > times[-1]:
        return _value_failure(
            None,
            "time",
            head_time,
            f"{times[0]!r}..{times[-1]!r}",
            message=(
                f"Note 头部 time={head_time!r} 不在线的 "
                f"{times[0]!r}..{times[-1]!r} 范围内"
            ),
            path=["lines", line_position, "notes", note_position, "time"],
            code="time.out_of_range",
        )

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
        return _structure_failure(
            None,
            ["canvasMoves"],
            "list",
            actual=type(canvases).__name__,
        )

    if canvasindex is not None:
        canvas = _find_canvas(chart, canvasindex)
        if canvas is None:
            return fail(
                None,
                f"画布索引 canvasindex={canvasindex!r} 不存在",
                code="canvas.not_found",
                parameter="canvasindex",
                actual=canvasindex,
                expected="有效的画布索引",
                path=["canvasMoves"],
            )
        return [(canvas["index"], canvas)]

    result = []
    for index, canvas in enumerate(canvases):
        if not isinstance(canvas, dict):
            return _structure_failure(
                None,
                ["canvasMoves", index],
                "画布 dict",
                actual=type(canvas).__name__,
            )
        if not _is_int(canvas.get("index")) or canvas["index"] != index:
            return _structure_failure(
                None,
                ["canvasMoves", index],
                "index 连续且与列表位置一致",
                actual=canvas,
            )
        result.append((index, canvas))
    return result


def _selected_lines(
    chart: dict,
    lineindex: object,
) -> list[tuple[int, dict]] | None:
    if not isinstance(chart, dict):
        return _chart_failure()
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )

    if lineindex is not None:
        position = _resolve_single_index(
            lineindex,
            len(lines),
            parameter="lineindex",
        )
        if position is None:
            return None
        line = lines[position]
        if not isinstance(line, dict):
            return _structure_failure(
                None,
                ["lines", position],
                "线 dict",
                actual=type(line).__name__,
            )
        return [(position, line)]

    result = []
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            return _structure_failure(
                None,
                ["lines", index],
                "线 dict",
                actual=type(line).__name__,
            )
        result.append((index, line))
    return result


def _query_tick(
    chart: dict,
    time: object,
    is_real_time: bool,
) -> float | None:
    """把查询时间转换为 tick。"""
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")
    if not is_real_time:
        return float(time)

    timeline = _get_bpm_timeline(chart)
    if timeline is None:
        return _structure_failure(
            None,
            ["bPM", "bpmShifts"],
            "可用的 BPM 时间轴（bPM > 0 且 bpmShifts[0].time == 0）",
            actual={"bPM": chart.get("bPM"), "bpmShifts": chart.get("bpmShifts")},
            message="谱面 BPM 时间轴非法，无法换算实际时间",
        )
    base_bpm, times, values, floor_positions = timeline
    tick = _tick_at_realtime(
        float(time),
        base_bpm,
        times,
        values,
        floor_positions,
    )
    if tick is None or tick < 0:
        return fail(
            None,
            f"实际时间 time={time!r} 无法换算为非负 tick",
            code="time.conversion_failed",
            parameter="time",
            actual=time,
            expected="可换算的非负 tick",
            path=["bpmShifts"],
        )
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
            return _value_failure(None, "value", value, ">= 0")
        return (float(value), float(value))

    if isinstance(value, list) and len(value) == 2:
        low, high = value
        if not _is_finite_number(low) or not _is_finite_number(high):
            return fail(
                None,
                "查询范围必须包含两个有限数值",
                code="range.invalid",
                parameter="value",
                actual=value,
                expected="[low, high] 且 low/high 为有限数",
            )
        if non_negative and (low < 0 or high < 0):
            return _value_failure(
                None,
                "value",
                value,
                "两个端点均 >= 0",
                code="range.negative",
            )
        if low > high:
            return _value_failure(
                None,
                "value",
                value,
                "low <= high",
                message=f"查询范围下界 {low!r} 大于上界 {high!r}",
                code="range.reversed",
            )
        return (float(low), float(high))

    return _type_failure(
        None,
        "value",
        value,
        "有限数、[low, high] 或 None",
    )


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
    if low_tick is None:
        return None
    if high_tick is None:
        return None
    if low_tick > high_tick:
        return fail(
            None,
            f"换算后的时间范围非法：low={low_tick!r} > high={high_tick!r}",
            code="range.reversed",
            parameter="value",
            actual=value,
            expected="换算后 low <= high",
        )
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
    if end is None:
        return None
    if end < start:
        return _value_failure(
            None,
            "endtime",
            end,
            f">= starttime（{start!r}）",
            message=f"结束时间 {end!r} 小于开始时间 {start!r}",
            code="range.reversed",
        )
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
        return _chart_failure()
    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list):
        return _structure_failure(
            None,
            ["bpmShifts"],
            "list",
            actual=type(shifts).__name__,
        )
    return _query_items(
        shifts,
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
        return _chart_failure()
    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return _structure_failure(
            None,
            ["canvasMoves"],
            "list",
            actual=type(canvas_moves).__name__,
        )
    return _query_items(
        canvas_moves,
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
        return _chart_failure()
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return fail(
            None,
            f"画布索引 canvasindex={canvasindex!r} 不存在",
            code="canvas.not_found",
            parameter="canvasindex",
            actual=canvasindex,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )
    points = canvas.get("xPositionKeyPoints")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["canvasMoves", canvas.get("index"), "xPositionKeyPoints"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
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
        return _chart_failure()
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return fail(
            None,
            f"画布索引 canvasindex={canvasindex!r} 不存在",
            code="canvas.not_found",
            parameter="canvasindex",
            actual=canvasindex,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )
    points = canvas.get("speedKeyPoints")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["canvasMoves", canvas.get("index"), "speedKeyPoints"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
        startindex,
        endindex,
        _key_point_spec,
    )


def getCamera(chart: dict) -> dict | None:
    """查询摄像机规格。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    return _camera_spec(chart)


def getCameraPosition(
    chart: dict,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一个或一段摄像机 x 位置关键点规格。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return _structure_failure(
            None,
            ["cameraMove"],
            "dict",
            actual=type(camera).__name__,
        )
    points = camera.get("xPositionKeyPoints")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["cameraMove", "xPositionKeyPoints"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
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
        return _chart_failure()
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return _structure_failure(
            None,
            ["cameraMove"],
            "dict",
            actual=type(camera).__name__,
        )
    points = camera.get("scaleKeyPoints")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["cameraMove", "scaleKeyPoints"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
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
        return fail(
            None,
            "参数 chart 必须为谱面 dict",
            parameter="chart",
            actual=type(chart).__name__,
            expected="dict",
        )
    lines = chart.get("lines")
    if not isinstance(lines, list):
        return fail(
            None,
            "谱面 lines 字段必须是列表",
            actual=type(lines).__name__,
            expected="list",
            path=["lines"],
        )
    length = len(lines)
    if endindex is None:
        if not _is_int(startindex):
            return fail(
                None,
                f"参数 startindex={startindex!r} 必须是整数",
                parameter="startindex",
                actual=startindex,
                expected="int（负索引从末尾计算）",
            )
        index = _resolve_single_index(startindex, length)
        if index is None:
            resolved = length + startindex if startindex < 0 else startindex
            return fail(
                None,
                f"线索引 startindex={startindex} 越界（lines 长度={length}）",
                code="line.index_out_of_range",
                parameter="startindex",
                actual=startindex,
                expected=(
                    f"无可用索引（lines 长度={length}）"
                    if length == 0
                    else f"{-length}..{length - 1}"
                ),
                index=startindex,
                length=length,
                path=["lines"],
                resolved_index=resolved,
            )
        spec = _line_spec(chart, lines[index])
        if spec is None:
            return fail(
                None,
                f"lines[{index}] 的线数据结构非法",
                actual=type(lines[index]).__name__,
                expected="符合标准格式的线 Dict",
                path=["lines", index],
            )
        return spec

    if not _is_int(startindex) or not _is_int(endindex):
        bad_key = "startindex" if not _is_int(startindex) else "endindex"
        bad_value = startindex if bad_key == "startindex" else endindex
        return fail(
            None,
            f"参数 {bad_key}={bad_value!r} 必须是整数",
            parameter=bad_key,
            actual=bad_value,
            expected="int（负索引从末尾计算）",
        )
    indices = _resolve_range_indices(startindex, endindex, length)
    if indices is None:
        return fail(
            None,
            "线索引范围非法",
            parameter="startindex/endindex",
            actual=[startindex, endindex],
            expected="整数索引范围",
            path=["lines"],
        )
    result = []
    for index in indices:
        spec = _line_spec(chart, lines[index])
        if spec is None:
            return fail(
                None,
                f"lines[{index}] 的线数据结构非法",
                actual=type(lines[index]).__name__,
                expected="符合标准格式的线 Dict",
                path=["lines", index],
            )
        result.append(spec)
    return result


def getLinePoint(
    chart: dict,
    lineindex: int,
    startindex: int,
    endindex: int | None = None,
) -> dict | list | None:
    """查询一条引导线上的线节点规格。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    points = line.get("linePoints")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["lines", line.get("index"), "linePoints"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
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
        return _chart_failure()
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    points = line.get("judgeRingColor")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["lines", line.get("index"), "judgeRingColor"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
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
        return _chart_failure()
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    points = line.get("lineColor")
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["lines", line.get("index"), "lineColor"],
            "list",
            actual=type(points).__name__,
        )
    return _query_items(
        points,
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
        return _chart_failure()
    line = _find_line(chart, lineindex)
    if line is None:
        return None
    point_specs = _line_points_spec(chart, line)
    if point_specs is None:
        return None
    line_times = [point["time"] for point in point_specs]
    notes = line.get("notes")
    if not isinstance(notes, list):
        return _structure_failure(
            None,
            ["lines", line.get("index"), "notes"],
            "list",
            actual=type(notes).__name__,
        )
    return _query_items(
        notes,
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
        return _chart_failure()
    themes = chart.get("themes")
    if not isinstance(themes, list):
        return _structure_failure(
            None,
            ["themes"],
            "list",
            actual=type(themes).__name__,
        )
    return _query_items(themes, startindex, endindex, _theme_spec)


def getThemeColor(
    chart: dict,
    themeindex: int,
    startindex: int,
    endindex: int | None = None,
) -> list | None:
    """查询一个主题内的颜色规格。"""
    if not isinstance(chart, dict):
        return _chart_failure()
    themes = chart.get("themes")
    if not isinstance(themes, list):
        return _structure_failure(
            None,
            ["themes"],
            "list",
            actual=type(themes).__name__,
        )
    position = _resolve_single_index(
        themeindex,
        len(themes),
        parameter="themeindex",
    )
    if position is None:
        return None
    theme_spec = _theme_spec(themes[position])
    if theme_spec is None:
        return fail(
            None,
            f"themes[{position}] 主题结构非法",
            code="theme.invalid",
            actual=themes[position],
            expected="包含 3 个有效颜色的主题",
            path=["themes", position],
        )
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
        return _chart_failure()
    challenge_times = chart.get("challengeTimes")
    if not isinstance(challenge_times, list):
        return _structure_failure(
            None,
            ["challengeTimes"],
            "list",
            actual=type(challenge_times).__name__,
        )
    return _query_items(
        challenge_times,
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
        return _chart_failure()
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
        return _chart_failure()
    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list):
        return _structure_failure(
            None,
            ["bpmShifts"],
            "list",
            actual=type(shifts).__name__,
        )
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
            return _structure_failure(
                None,
                ["bpmShifts", index],
                "BPM 节点 dict",
                actual=type(node).__name__,
            )
        node_time = node.get("time")
        if not _is_finite_number(node_time) or node_time < 0:
            return _value_failure(
                None,
                "time",
                node_time,
                "有限数且 >= 0",
                path=["bpmShifts", index, "time"],
                code="time.invalid",
            )
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
            return _structure_failure(
                None,
                ["canvasMoves", canvas_index, key],
                "list",
                actual=type(points).__name__,
            )
        allowed = _allowed_indices(indexlist, len(points))
        for point_index, point in enumerate(points):
            if allowed is not None and point_index not in allowed:
                continue
            if not isinstance(point, dict):
                return _structure_failure(
                    None,
                    ["canvasMoves", canvas_index, key, point_index],
                    "关键点 dict",
                    actual=type(point).__name__,
                )
            point_time = point.get("time")
            if not _is_finite_number(point_time) or point_time < 0:
                return _value_failure(
                    None,
                    "time",
                    point_time,
                    "有限数且 >= 0",
                    path=["canvasMoves", canvas_index, key, point_index, "time"],
                    code="time.invalid",
                )
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
        return _chart_failure()
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
        return _chart_failure()
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
    if not isinstance(chart, dict):
        return _chart_failure()
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return _structure_failure(
            None,
            ["cameraMove"],
            "dict",
            actual=type(camera).__name__,
        )
    points = camera.get(key)
    if not isinstance(points, list):
        return _structure_failure(
            None,
            ["cameraMove", key],
            "list",
            actual=type(points).__name__,
        )
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
            return _structure_failure(
                None,
                ["cameraMove", key, index],
                "关键点 dict",
                actual=type(point).__name__,
            )
        point_time = point.get("time")
        if not _is_finite_number(point_time) or point_time < 0:
            return _value_failure(
                None,
                "time",
                point_time,
                "有限数且 >= 0",
                path=["cameraMove", key, index, "time"],
                code="time.invalid",
            )
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
        return _chart_failure()
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
        return _chart_failure()
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
            return fail(
                None,
                f"画布索引 canvasindex={canvasindex!r} 不存在",
                code="canvas.not_found",
                parameter="canvasindex",
                actual=canvasindex,
                expected="有效的画布索引",
                path=["canvasMoves"],
            )
        canvas_filter = canvas["index"]

    start, end, single = time_range
    result = []
    for line_index, line in selected:
        values = line.get(key)
        if not isinstance(values, list):
            return _structure_failure(
                None,
                ["lines", line_index, key],
                "list",
                actual=type(values).__name__,
            )
        allowed = _allowed_indices(indexlist, len(values))
        for index, value in enumerate(values):
            if allowed is not None and index not in allowed:
                continue
            if not isinstance(value, dict):
                return _structure_failure(
                    None,
                    ["lines", line_index, key, index],
                    "线节点 dict",
                    actual=type(value).__name__,
                )
            value_time = value.get("time")
            if not _is_finite_number(value_time) or value_time < 0:
                return _value_failure(
                    None,
                    "time",
                    value_time,
                    "有限数且 >= 0",
                    path=["lines", line_index, key, index, "time"],
                    code="time.invalid",
                )
            if canvas_filter is not None:
                point_canvas = value.get("canvasIndex")
                if not _is_int(point_canvas):
                    return _type_failure(
                        None,
                        "canvasIndex",
                        point_canvas,
                        "int",
                        path=["lines", line_index, key, index, "canvasIndex"],
                    )
                point_canvas = _find_canvas(chart, point_canvas)
                if point_canvas is None:
                    return fail(
                        None,
                        f"画布索引 canvasindex={value.get('canvasIndex')!r} 不存在",
                        code="canvas.not_found",
                        parameter="canvasindex",
                        actual=value.get("canvasIndex"),
                        expected="有效的画布索引",
                        path=["canvasMoves"],
                    )
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
        return _chart_failure()
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
        return _chart_failure()
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
        return _chart_failure()
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
        return _chart_failure()
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
        return fail(
            None,
            f"参数 type={type!r} 不是有效的 Note 过滤类型",
            code="note.type_invalid",
            parameter="type",
            actual=type,
            expected='None、0/1/2/3、\"tap\"/\"drag\"/\"hold\"/\"holdEnd\"',
        )
    wanted_type, use_tail = note_filter

    start, end, single = time_range
    result = []
    for line_index, line in selected:
        notes = line.get("notes")
        if not isinstance(notes, list):
            return _structure_failure(
                None,
                ["lines", line_index, "notes"],
                "list",
                actual=type(notes).__name__,
            )
        allowed = _allowed_indices(indexlist, len(notes))
        for note_index, note in enumerate(notes):
            if allowed is not None and note_index not in allowed:
                continue
            if not isinstance(note, dict):
                return _structure_failure(
                    None,
                    ["lines", line_index, "notes", note_index],
                    "Note dict",
                    actual=type(note).__name__,
                )
            note_type = note.get("type")
            if not _is_int(note_type) or note_type not in (0, 1, 2):
                return _value_failure(
                    None,
                    "type",
                    note_type,
                    "0、1 或 2",
                    path=["lines", line_index, "notes", note_index, "type"],
                    code="note.type_invalid",
                )
            head_time = note.get("time")
            if not _is_finite_number(head_time) or head_time < 0:
                return _value_failure(
                    None,
                    "time",
                    head_time,
                    "有限数且 >= 0",
                    path=["lines", line_index, "notes", note_index, "time"],
                    code="time.invalid",
                )

            if use_tail:
                if note_type != 2:
                    continue
                extra = note.get("otherInformations")
                if not isinstance(extra, list) or len(extra) != 3:
                    return _structure_failure(
                        None,
                        ["lines", line_index, "notes", note_index, "otherInformations"],
                        "Hold 的三元素尾部信息",
                        actual=extra,
                    )
                note_time = extra[0]
                if not _is_finite_number(note_time) or note_time < 0:
                    return _value_failure(
                        None,
                        "endtime",
                        note_time,
                        "有限数且 >= 0",
                        path=["lines", line_index, "notes", note_index, "otherInformations", 0],
                        code="time.invalid",
                    )
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
        return _chart_failure()
    ranges = _parse_color_range(startcolor, endcolor)
    if ranges is None:
        return None
    themes = chart.get("themes")
    if not isinstance(themes, list):
        return _structure_failure(
            None,
            ["themes"],
            "list",
            actual=type(themes).__name__,
        )
    if not _valid_index_list(indexlist):
        return None

    allowed = _allowed_indices(indexlist, len(themes))
    result = []
    for index, theme in enumerate(themes):
        if allowed is not None and index not in allowed:
            continue
        if not isinstance(theme, dict):
            return _structure_failure(
                None,
                ["themes", index],
                "主题 dict",
                actual=type(theme).__name__,
            )
        colors = theme.get("colorsList")
        if not isinstance(colors, list) or len(colors) != 3:
            return _structure_failure(
                None,
                ["themes", index, "colorsList"],
                "长度为 3 的颜色列表",
                actual=colors,
            )
        for color_index, value in enumerate(colors):
            color = _parse_color(value)
            if color is None:
                return fail(
                    None,
                    f"themes[{index}].colorsList[{color_index}] 不是可解析的颜色",
                    code="color.invalid",
                    parameter="startcolor/endcolor",
                    actual=value,
                    expected="HEX 字符串或 RGB(A) 列表",
                    path=["themes", index, "colorsList", color_index],
                )
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
        return _chart_failure()
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
            return fail(
                None,
                f"画布索引 canvasindex={canvasindex!r} 不存在",
                code="canvas.not_found",
                parameter="canvasindex",
                actual=canvasindex,
                expected="有效的画布索引",
                path=["canvasMoves"],
            )
        canvas_filter = canvas["index"]

    result = []
    for line_index, line in selected:
        points = line.get("linePoints")
        if not isinstance(points, list):
            return _structure_failure(
                None,
                ["lines", line_index, "linePoints"],
                "list",
                actual=type(points).__name__,
            )
        allowed = _allowed_indices(indexlist, len(points))
        for point_index, point in enumerate(points):
            if allowed is not None and point_index not in allowed:
                continue
            if not isinstance(point, dict):
                return _structure_failure(
                    None,
                    ["lines", line_index, "linePoints", point_index],
                    "线节点 dict",
                    actual=type(point).__name__,
                )
            if canvas_filter is not None:
                point_canvas = point.get("canvasIndex")
                if not _is_int(point_canvas):
                    return _type_failure(
                        None,
                        "canvasIndex",
                        point_canvas,
                        "int",
                        path=["lines", line_index, "linePoints", point_index, "canvasIndex"],
                    )
                point_canvas = _find_canvas(chart, point_canvas)
                if point_canvas is None:
                    return fail(
                        None,
                        f"画布索引 canvasindex={point.get('canvasIndex')!r} 不存在",
                        code="canvas.not_found",
                        parameter="canvasindex",
                        actual=point.get("canvasIndex"),
                        expected="有效的画布索引",
                        path=["canvasMoves"],
                    )
                if point_canvas["index"] != canvas_filter:
                    continue
            color = _parse_color(point.get("color"))
            if color is None:
                return fail(
                    None,
                    "线节点 color 不是可解析的颜色",
                    code="color.invalid",
                    parameter="color",
                    actual=point.get("color"),
                    expected="HEX 字符串或 RGB(A) 列表",
                    path=["lines", line_index, "linePoints", point_index, "color"],
                )
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
            return _structure_failure(
                None,
                ["lines", line_index, key],
                "list",
                actual=type(nodes).__name__,
            )
        allowed = _allowed_indices(indexlist, len(nodes))
        for index, node in enumerate(nodes):
            if allowed is not None and index not in allowed:
                continue
            if not isinstance(node, dict):
                return _structure_failure(
                    None,
                    ["lines", line_index, key, index],
                    "颜色节点 dict",
                    actual=type(node).__name__,
                )
            start_color = _parse_color(node.get("startColor"))
            if start_color is None:
                return fail(
                    None,
                    "startColor 不是可解析的颜色",
                    code="color.invalid",
                    parameter="startColor",
                    actual=node.get("startColor"),
                    expected="HEX 字符串或 RGB(A) 列表",
                    path=["lines", line_index, key, index, "startColor"],
                )
            end_color = _parse_color(node.get("endColor"))
            if end_color is None:
                return fail(
                    None,
                    "endColor 不是可解析的颜色",
                    code="color.invalid",
                    parameter="endColor",
                    actual=node.get("endColor"),
                    expected="HEX 字符串或 RGB(A) 列表",
                    path=["lines", line_index, key, index, "endColor"],
                )
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
        return _chart_failure()
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
        return _chart_failure()
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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    canvas = _find_canvas(chart, index)
    if canvas is None:
        return fail(
            None,
            f"画布索引 index={index!r} 不存在",
            code="canvas.not_found",
            parameter="index",
            actual=index,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )

    result = _canvas_x_at(canvas, tick)
    if result is None:
        return fail(
            None,
            f"tick={tick!r} 不在画布位置关键点范围内或结构非法",
            code="canvas.position_unavailable",
            parameter="time",
            actual=time,
            expected="画布位置关键点时间范围内的时间",
            path=["canvasMoves", canvas.get("index"), "xPositionKeyPoints"],
        )
    return result


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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    canvas = _find_canvas(chart, index)
    if canvas is None:
        return fail(
            None,
            f"画布索引 index={index!r} 不存在",
            code="canvas.not_found",
            parameter="index",
            actual=index,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )

    result = _canvas_speed_at(canvas.get("speedKeyPoints"), tick)
    if result is None:
        return fail(
            None,
            f"tick={tick!r} 不在画布流速关键点范围内或结构非法",
            code="canvas.speed_unavailable",
            parameter="time",
            actual=time,
            expected="画布流速关键点时间范围内的时间",
            path=["canvasMoves", canvas.get("index"), "speedKeyPoints"],
        )
    return result


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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return _structure_failure(
            None,
            ["cameraMove"],
            "dict",
            actual=type(camera).__name__,
        )
    result = _key_point_value_at(camera.get("xPositionKeyPoints"), tick)
    if result is None:
        return fail(
            None,
            f"tick={tick!r} 不在摄像机位置关键点范围内或结构非法",
            code="camera.position_unavailable",
            parameter="time",
            actual=time,
            expected="摄像机位置关键点时间范围内的时间",
            path=["cameraMove", "xPositionKeyPoints"],
        )
    return result


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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return _structure_failure(
            None,
            ["cameraMove"],
            "dict",
            actual=type(camera).__name__,
        )
    result = _key_point_value_at(camera.get("scaleKeyPoints"), tick)
    if result is None:
        return fail(
            None,
            f"tick={tick!r} 不在摄像机缩放关键点范围内或结构非法",
            code="camera.scale_unavailable",
            parameter="time",
            actual=time,
            expected="摄像机缩放关键点时间范围内的时间",
            path=["cameraMove", "scaleKeyPoints"],
        )
    return result


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
        return _chart_failure()
    if not _is_finite_number(time) or time < 0:
        return _value_failure(None, "time", time, "有限数且 >= 0")
    if not _is_int(index):
        return _type_failure(None, "index", index, "int")

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )

    line_index = index + len(lines) if index < 0 else index
    if not 0 <= line_index < len(lines):
        return _index_failure(None, "index", index, len(lines), ["lines"])
    line = lines[line_index]
    if not isinstance(line, dict):
        return _structure_failure(
            None,
            ["lines", line_index],
            "线 dict",
            actual=type(line).__name__,
        )

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None

    result = _line_x_at(line, tick)
    if result is None:
        return fail(
            None,
            f"tick={tick!r} 不在线节点时间范围内或线节点结构非法",
            code="line.position_unavailable",
            parameter="time",
            actual=time,
            expected="线首末节点时间范围内的时间",
            path=["lines", line_index, "linePoints"],
        )

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
        return _chart_failure()

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )

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
            return fail(
                None,
                f"画布索引 index={index!r} 不存在",
                code="canvas.not_found",
                parameter="index",
                actual=index,
                expected="有效的画布索引",
                path=["canvasMoves"],
            )
        canvas_filter = canvas["index"]

    parsed_color = None
    if color is not None:
        parsed_color = _parse_color(color)
        if parsed_color is None:
            return fail(
                None,
                "参数 color 不是可解析的颜色",
                code="color.invalid",
                parameter="color",
                actual=color,
                expected="HEX 字符串或 RGB(A) 列表",
            )

    low, high = position_range
    time_low, time_high, time_single = time_range
    results = []

    for line_index, line in enumerate(lines):
        if not isinstance(line, dict):
            return _structure_failure(
                None,
                ["lines", line_index],
                "线 dict",
                actual=type(line).__name__,
            )
        points = line.get("linePoints")
        if not isinstance(points, list):
            return _structure_failure(
                None,
                ["lines", line_index, "linePoints"],
                "list",
                actual=type(points).__name__,
            )

        for point_index, point in enumerate(points):
            if not isinstance(point, dict):
                return _structure_failure(
                    None,
                    ["lines", line_index, "linePoints", point_index],
                    "线节点 dict",
                    actual=type(point).__name__,
                )

            point_time = point.get("time")
            if not _is_finite_number(point_time) or point_time < 0:
                return _value_failure(
                    None,
                    "time",
                    point_time,
                    "有限数且 >= 0",
                    path=["lines", line_index, "linePoints", point_index, "time"],
                    code="time.invalid",
                )
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
                    return _type_failure(
                        None,
                        "canvasIndex",
                        point_canvas,
                        "int",
                        path=["lines", line_index, "linePoints", point_index, "canvasIndex"],
                    )
                if point_canvas != canvas_filter:
                    continue

            if parsed_color is not None:
                if point.get("color") != parsed_color:
                    continue

            if low is not None:
                point_x = point.get("xPosition")
                if not _is_finite_number(point_x):
                    return _type_failure(
                        None,
                        "xPosition",
                        point_x,
                        "有限数",
                        path=["lines", line_index, "linePoints", point_index, "xPosition"],
                    )

                if isAbsolutePosition:
                    if not _is_int(point_canvas):
                        return _type_failure(
                            None,
                            "canvasIndex",
                            point_canvas,
                            "int",
                            path=["lines", line_index, "linePoints", point_index, "canvasIndex"],
                        )
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
        return _chart_failure()

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return _structure_failure(
            None,
            ["lines"],
            "list",
            actual=type(lines).__name__,
        )

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
            return _value_failure(
                None,
                "type",
                type,
                "0、1、2 或 None",
                code="note.type_invalid",
            )
        wanted_type = type
    elif isinstance(type, str):
        type_map = {"tap": 0, "drag": 1, "hold": 2}
        wanted_type = type_map.get(type.lower())
        if wanted_type is None:
            return _value_failure(
                None,
                "type",
                type,
                '"tap"、"drag"、"hold" 或 None',
                code="note.type_invalid",
            )
    else:
        return _type_failure(
            None,
            "type",
            type,
            "int、str 或 None",
        )

    low, high = position_range
    time_low, time_high, time_single = time_range
    results = []

    for line_index, line in enumerate(lines):
        if not isinstance(line, dict):
            return _structure_failure(
                None,
                ["lines", line_index],
                "线 dict",
                actual=type(line).__name__,
            )
        notes = line.get("notes")
        if not isinstance(notes, list):
            return _structure_failure(
                None,
                ["lines", line_index, "notes"],
                "list",
                actual=type(notes).__name__,
            )

        for note_index, note in enumerate(notes):
            if not isinstance(note, dict):
                return _structure_failure(
                    None,
                    ["lines", line_index, "notes", note_index],
                    "Note dict",
                    actual=type(note).__name__,
                )

            note_time = note.get("time")
            if not _is_finite_number(note_time) or note_time < 0:
                return _value_failure(
                    None,
                    "time",
                    note_time,
                    "有限数且 >= 0",
                    path=["lines", line_index, "notes", note_index, "time"],
                    code="time.invalid",
                )
            if not _time_matches(
                note_time,
                time_low,
                time_high,
                time_single,
            ):
                continue

            note_type = note.get("type")
            if not _is_int(note_type) or note_type not in (0, 1, 2):
                return _value_failure(
                    None,
                    "type",
                    note_type,
                    "0、1 或 2",
                    path=["lines", line_index, "notes", note_index, "type"],
                    code="note.type_invalid",
                )
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
        return _chart_failure()

    line = _find_line(chart, lineindex)
    if line is None:
        return None
    points = _line_points_spec(chart, line)
    if points is None:
        return None

    first = points[0]["time"]
    last = points[-1]["time"]
    if isRealTime:
        first_seconds = getSecondsAt(chart, first)
        if first_seconds is None:
            return None
        last_seconds = getSecondsAt(chart, last)
        if last_seconds is None:
            return None
        first = first_seconds
        last = last_seconds
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
            return _structure_failure(
                None,
                ["notes", "otherInformations"],
                "Hold 的三元素尾部信息",
                actual=extra,
            )
        tail_time = extra[0]
        if (
            not _is_finite_number(tail_time)
            or tail_time <= head_time
            or tail_time > times[-1]
        ):
            return _value_failure(
                None,
                "endtime",
                tail_time,
                f"> {head_time!r} 且 <= {times[-1]!r}",
                message="Hold 尾部时间非法",
                path=["notes", "otherInformations", 0],
                code="time.out_of_range",
            )
        raw_canvas = extra[1]
        canvas_index = _canvas_ref(raw_canvas)
        if canvas_index is None or canvas_index < 0:
            return fail(
                None,
                f"Hold 尾部画布引用 {raw_canvas!r} 不是非负整数",
                code="canvas.invalid_reference",
                parameter="otherInformations[1]",
                actual=raw_canvas,
                expected="非负整数画布索引",
                path=["notes", "otherInformations", 1],
            )
        canvas = _find_canvas(chart, canvas_index)
        if canvas is None:
            return fail(
                None,
                f"Hold 尾部画布索引 {canvas_index!r} 不存在",
                code="canvas.not_found",
                parameter="canvasindex",
                actual=canvas_index,
                expected="有效的画布索引",
                path=["canvasMoves"],
            )
        return int(canvas["index"])

    position = bisect.bisect_right(times, head_time) - 1
    if position < 0:
        return fail(
            None,
            f"Note 头部时间 {head_time!r} 早于第一个线节点",
            code="time.out_of_range",
            parameter="time",
            actual=head_time,
            expected=f">= {times[0]!r}",
            path=["linePoints"],
        )
    canvas_index = points[position]["canvasIndex"]
    if not _is_int(canvas_index) or canvas_index < 0:
        return fail(
            None,
            "Note 头部所在画布索引不是非负整数",
            code="canvas.invalid_reference",
            parameter="canvasIndex",
            actual=canvas_index,
            expected="非负整数画布索引",
            path=["linePoints", position, "canvasIndex"],
        )
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
        return _value_failure(
            None,
            "time",
            tick,
            f"{times[0]!r}..{times[-1]!r}",
            message=f"tick={tick!r} 不在线节点 {times[0]!r}..{times[-1]!r} 范围内",
            path=["lines", index, "linePoints"],
            code="time.out_of_range",
        )

    left = bisect.bisect_left(times, tick)
    right = bisect.bisect_right(times, tick)

    # 不在节点时间：使用前后节点做时间插值。
    if left == right:
        if left == 0 or left == len(points):
            return fail(
                None,
                "无法在当前 tick 找到用于颜色插值的相邻线节点",
                code="color.interpolation_failed",
                parameter="time",
                actual=tick,
                expected="位于线节点时间范围内",
                path=["lines", index, "linePoints"],
            )
        start = points[left - 1]
        end = points[left]
        span = end["time"] - start["time"]
        if span <= 0.0:
            return fail(
                None,
                "相邻线节点的 time span 必须大于 0",
                code="color.interpolation_failed",
                actual=span,
                expected="> 0",
                path=["lines", index, "linePoints", left - 1, "time"],
            )
        ratio = (tick - start["time"]) / span
        return _lerp_color(start["color"], end["color"], ratio)

    # 正好只有一个节点：直接返回该节点颜色。
    if right - left == 1:
        return _color_list(points[left]["color"])

    # 同一时间有多个节点：必须用 position 选择最上层线段。
    if position is None or not _is_finite_number(position):
        return fail(
            None,
            "同一时间有多个线节点时必须提供有限的 position 选择线段",
            code="position.required",
            parameter="position",
            actual=position,
            expected="有限数",
            path=["lines", index, "linePoints"],
        )

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
                return fail(
                    None,
                    "无法计算同时间线节点所在画布的绝对 x",
                    code="canvas.position_unavailable",
                    actual={
                        "start_canvas_x": start_canvas_x,
                        "end_canvas_x": end_canvas_x,
                    },
                    expected="可计算位置的画布",
                    path=["lines", index, "linePoints"],
                )
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
        return _chart_failure()
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
    if nodes is None:
        return None
    if not nodes:
        return fail(
            None,
            "lineColor 至少需要一个颜色节点",
            code="colors.empty",
            parameter="lineColor",
            actual=line.get("lineColor"),
            expected="非空颜色节点列表",
            path=["lines", index, "lineColor"],
        )

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
        return fail(
            None,
            "线色覆盖节点的 time span 必须大于 0",
            code="color.interpolation_failed",
            actual=span,
            expected="> 0",
            path=["lineColor", position, "time"],
        )
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
        return _chart_failure()
    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None
    return _cover_color_at_tick(chart, index, tick)


def _ring_color_at_tick(
    chart: dict,
    index: object,
    tick: float,
) -> list[int] | None:
    """按已换算的 tick 查询判定环颜色。"""
    line = _find_line(chart, index)
    if line is None:
        return None

    nodes = _color_change_specs(line.get("judgeRingColor"), non_empty=True)
    if nodes is None:
        return None
    if not nodes:
        return fail(
            None,
            "judgeRingColor 至少需要一个颜色节点",
            code="colors.empty",
            parameter="judgeRingColor",
            actual=line.get("judgeRingColor"),
            expected="非空颜色节点列表",
            path=["lines", index, "judgeRingColor"],
        )

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
        return fail(
            None,
            "判定环颜色节点的 time span 必须大于 0",
            code="color.interpolation_failed",
            actual=span,
            expected="> 0",
            path=["judgeRingColor", position, "time"],
        )
    ratio = (tick - start["time"]) / span
    return _lerp_color(start["startColor"], start["endColor"], ratio)


def getRingColor(
    chart: dict,
    index: int,
    time: float,
    isRealTime: bool = False,
) -> list[int] | None:
    """查询指定引导线在指定时间的判定环颜色。

    判定环颜色节点必须非空；``time`` 必须大于 ``0.0``。早于第一个
    节点时返回第一个节点的 ``startColor``；正好命中节点时返回该节点
    的 ``startColor``，同一时间有多个节点时取索引最大的节点；两个节点
    之间按前一个节点的 ``startColor -> endColor`` 线性插值；晚于最后
    一个节点时返回最后一个节点的 ``startColor``。``isRealTime=True``
    时 ``time`` 是实际秒数。失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return _chart_failure()
    if not isinstance(isRealTime, bool):
        return _type_failure(None, "isRealTime", isRealTime, "bool")
    if not _is_finite_number(time) or float(time) <= 0.0:
        return _value_failure(
            None,
            "time",
            time,
            "有限数且 > 0",
            code="time.invalid",
        )

    tick = _query_tick(chart, time, isRealTime)
    if tick is None:
        return None
    return _ring_color_at_tick(chart, index, tick)


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
        return _chart_failure()

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


def getXYRatio(
    bpm: float,
    canvasspeed: float,
    gamespeed: float,
    value: float = 1.0,
    type: str = "X",
) -> float | None:
    """计算 BPM/画布流速/游戏流速下 X 与 Y 的视觉比例。

    X 表示 ``floorPosition``，Y 表示 tick。``type="X"`` 时返回
    ``value`` 个 X 对应的 Y；``type="Y"`` 时返回 ``value`` 个 Y 对应的 X。
    除零或 0/0 返回 ``nan``；输入非法返回 ``None``。
    """
    if not _is_finite_number(bpm) or float(bpm) <= 0.0:
        return _value_failure(None, "bpm", bpm, "有限数且 > 0")
    if not _is_finite_number(canvasspeed):
        return _type_failure(None, "canvasspeed", canvasspeed, "有限数")
    if not _is_finite_number(gamespeed) or float(gamespeed) <= 0.0:
        return _value_failure(None, "gamespeed", gamespeed, "有限数且 > 0")
    if not _is_finite_number(value) or float(value) <= 0.0:
        return _value_failure(None, "value", value, "有限数且 > 0")
    if type not in ("X", "Y"):
        return _value_failure(None, "type", type, '"X" 或 "Y"')

    k = 6.0 + 7.0 * (float(gamespeed) - 1.0) / 9.0
    if type == "X":
        denominator = 60.0 * float(canvasspeed) * k
        if denominator == 0.0:
            return math.nan
        return float(value) * 5.625 * float(bpm) / denominator
    return (
        float(value) * 60.0 * float(canvasspeed) * k
        / (5.625 * float(bpm))
    )


def getXYRatioByChart(
    chart: dict,
    index: int,
    time: float,
    gamespeed: float,
    value: float = 1.0,
    type: str = "X",
    isRealTime: bool = False,
) -> float | None:
    """从谱面 BPM 和画布流速计算 X/Y 视觉比例。

    ``index`` 为画布索引，支持负数；``time`` 的语义由 ``isRealTime`` 决定。
    其它参数和计算规则同 :func:`getXYRatio`。
    """
    if not isinstance(chart, dict):
        return _chart_failure()
    if not _is_int(index):
        return _type_failure(None, "index", index, "int")
    if not _is_finite_number(time) or float(time) < 0.0:
        return _value_failure(None, "time", time, "有限数且 >= 0")
    if not isinstance(isRealTime, bool):
        return _type_failure(None, "isRealTime", isRealTime, "bool")
    if not _is_finite_number(gamespeed) or float(gamespeed) <= 0.0:
        return _value_failure(None, "gamespeed", gamespeed, "有限数且 > 0")
    if not _is_finite_number(value) or float(value) <= 0.0:
        return _value_failure(None, "value", value, "有限数且 > 0")
    if type not in ("X", "Y"):
        return _value_failure(None, "type", type, '"X" 或 "Y"')

    bpm = getBpmAt(chart, time, isRealTime)
    if bpm is None:
        return None
    canvasspeed = getCanvasSpeedAt(chart, index, time, isRealTime)
    if canvasspeed is None:
        return None
    return getXYRatio(bpm, canvasspeed, gamespeed, value, type)


_X_BORDER_TYPES = ("solidLeft", "shadeLeft", "solidRight", "shadeRight")


def _x_border_value(
    canvasposition: float,
    cameraposition: float,
    camerascale: float,
    type: str,
    isAbsolutePosition: bool,
) -> float | None:
    if type not in _X_BORDER_TYPES:
        return _value_failure(
            None,
            "type",
            type,
            ", ".join(_X_BORDER_TYPES),
        )
    if not isinstance(isAbsolutePosition, bool):
        return _type_failure(
            None,
            "isAbsolutePosition",
            isAbsolutePosition,
            "bool",
        )
    if not _is_finite_number(cameraposition):
        return _type_failure(None, "cameraposition", cameraposition, "有限数")
    if not _is_finite_number(camerascale) or float(camerascale) <= 0.0:
        return _value_failure(None, "camerascale", camerascale, "有限数且 > 0")
    if not isAbsolutePosition and not _is_finite_number(canvasposition):
        return _type_failure(
            None,
            "canvasposition",
            canvasposition,
            "有限数（isAbsolutePosition=False 时）",
        )

    camera = float(cameraposition)
    scale = float(camerascale)
    canvas = 0.0 if isAbsolutePosition else float(canvasposition)
    center = camera - canvas
    half = scale / 2.0
    shade = scale / 5.625

    if type == "solidLeft":
        return center - half
    if type == "shadeLeft":
        return center - half + shade
    if type == "solidRight":
        return center + half
    return center + half - shade


def getXBorder(
    canvasposition: float = 0.0,
    cameraposition: float = 0.0,
    camerascale: float = 1.0,
    type: str = "solidLeft",
    isAbsolutePosition: bool = False,
) -> float | None:
    """计算指定摄像机参数下的可视 X 边界。

    ``isAbsolutePosition=False`` 时结果会减去 ``canvasposition``；
    ``True`` 时忽略 ``canvasposition``。``camerascale`` 必须大于 0。
    失败返回 ``None``。
    """
    return _x_border_value(
        canvasposition,
        cameraposition,
        camerascale,
        type,
        isAbsolutePosition,
    )


def getXBorderByChart(
    chart: dict,
    time: float,
    index: int = 0,
    type: str = "solidLeft",
    isRealTime: bool = False,
    isAbsolutePosition: bool = False,
) -> float | None:
    """从谱面插值摄像机和画布参数后计算可视 X 边界。

    ``canvasposition``、``cameraposition``、``camerascale`` 分别由
    指定画布、摄像机位置和摄像机缩放在 ``time`` 处按缓动插值得到。
    ``isAbsolutePosition=True`` 时忽略 ``index`` 并对画布位置项置零。
    ``isRealTime=True`` 时 ``time`` 是实际秒数。失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return _chart_failure()
    if not _is_finite_number(time) or float(time) < 0.0:
        return _value_failure(None, "time", time, "有限数且 >= 0")
    if not isinstance(isRealTime, bool):
        return _type_failure(None, "isRealTime", isRealTime, "bool")
    if not isinstance(isAbsolutePosition, bool):
        return _type_failure(
            None,
            "isAbsolutePosition",
            isAbsolutePosition,
            "bool",
        )
    if type not in _X_BORDER_TYPES:
        return _value_failure(
            None,
            "type",
            type,
            ", ".join(_X_BORDER_TYPES),
        )

    camera_position = getCameraPositionAt(chart, time, isRealTime)
    if camera_position is None:
        return None
    camera_scale = getCameraScaleAt(chart, time, isRealTime)
    if camera_scale is None:
        return None
    if float(camera_scale) <= 0.0:
        return _value_failure(
            None,
            "camerascale",
            camera_scale,
            "有限数且 > 0",
            path=["cameraMove", "scaleKeyPoints"],
        )

    if isAbsolutePosition:
        canvas_position = 0.0
    else:
        if not _is_int(index):
            return _type_failure(None, "index", index, "int")
        canvas_position = getCanvasPositionAt(chart, time, index, isRealTime)
        if canvas_position is None:
            return None

    return _x_border_value(
        canvas_position,
        camera_position,
        camera_scale,
        type,
        isAbsolutePosition,
    )


_Y_BORDER_COEFFICIENTS = {
    "solidTop": 6.5,
    "shadeTop": 5.5,
    "solidLineBottom": -0.5,
    "shadeLineBottom": 0.5,
    "solidBottom": -1.5,
    "shadeBottom": -0.5,
}


def _y_border_coefficient(type: object) -> float | None:
    if not isinstance(type, str):
        return None
    return _Y_BORDER_COEFFICIENTS.get(type)


def getYBorder(
    bpm: float,
    canvasspeed: float,
    gamespeed: float,
    type: str = "solidTop",
    isReturnRealTime: bool = False,
    camerascale: float = 1.0,
) -> float | None:
    """计算恒定 BPM/画布流速下的可视 Y 边界。

    ``type`` 可取值见 :data:`_Y_BORDER_COEFFICIENTS`；结果默认为 tick
    （节拍）数，``isReturnRealTime=True`` 时按 BPM 转为实际秒数。
    ``camerascale`` 会乘到实际 W 上。``canvasspeed=0`` 时返回 ``NaN``；
    其它非法输入返回 ``None``。
    """
    coefficient = _y_border_coefficient(type)
    if coefficient is None:
        return _value_failure(
            None,
            "type",
            type,
            ", ".join(_Y_BORDER_COEFFICIENTS),
        )
    if not isinstance(isReturnRealTime, bool):
        return _type_failure(
            None,
            "isReturnRealTime",
            isReturnRealTime,
            "bool",
        )
    if not _is_finite_number(bpm) or float(bpm) <= 0.0:
        return _value_failure(None, "bpm", bpm, "有限数且 > 0")
    if not _is_finite_number(canvasspeed):
        return _type_failure(None, "canvasspeed", canvasspeed, "有限数")
    if not _is_finite_number(gamespeed) or float(gamespeed) <= 0.0:
        return _value_failure(None, "gamespeed", gamespeed, "有限数且 > 0")
    if not _is_finite_number(camerascale) or float(camerascale) <= 0.0:
        return _value_failure(None, "camerascale", camerascale, "有限数且 > 0")

    k = 6.0 + 7.0 * (float(gamespeed) - 1.0) / 9.0
    denominator = 60.0 * float(canvasspeed) * k
    if denominator == 0.0:
        return math.nan

    w = float(bpm) / denominator * float(camerascale)
    result = coefficient * w
    if isReturnRealTime:
        result = result * 60.0 / float(bpm)
    return result


def _y_border_events(chart: dict, index: int) -> list[float] | None:
    bpm_shifts = getBpmShift(chart, 0, -1)
    if not isinstance(bpm_shifts, list):
        return None
    speed_points = getCanvasSpeed(chart, index, 0, -1)
    if not isinstance(speed_points, list):
        return fail(
            None,
            "无法取得画布流速节点列表，不能计算 Y 边界事件",
            code="canvas.speed_unavailable",
            parameter="index",
            actual=index,
            expected="有效的画布索引和流速节点列表",
            path=["canvasMoves"],
        )
    events = {0.0}
    for item in bpm_shifts + speed_points:
        if not isinstance(item, dict):
            return _structure_failure(
                None,
                ["bpmShifts/canvasMoves"],
                "关键点 dict",
                actual=type(item).__name__,
            )
        time = item.get("time")
        if not _is_finite_number(time) or float(time) < 0.0:
            return _value_failure(
                None,
                "time",
                time,
                "有限数且 >= 0",
                path=["bpmShifts/canvasMoves", "time"],
                code="time.invalid",
            )
        events.add(float(time))
    return sorted(events)


def _y_border_sample(
    chart: dict,
    index: int,
    time: float,
) -> tuple[float, float] | None:
    sample_time = 0.0 if time < 0.0 else time
    bpm = getBpmAt(chart, sample_time)
    if bpm is None:
        return None
    if float(bpm) <= 0.0:
        return _value_failure(
            None,
            "bpm",
            bpm,
            "有限数且 > 0",
            path=["bpmShifts"],
            code="bpm.invalid",
        )
    speed = getCanvasSpeedAt(chart, index, sample_time)
    if speed is None:
        return None
    return float(bpm), float(speed)


def getYBorderByChart(
    chart: dict,
    time: float,
    index: int,
    gamespeed: float,
    type: str = "solidTop",
    isRealTime: bool = False,
    isReturnRealTime: bool = False,
) -> float | None:
    """从谱面分段积分计算可视 Y 边界。

    从查询 tick 向边界方向前进，按 BPM/画布流速关键点切段，每段使用
    ``段 W = 段 tick 长度 / 当前段 W`` 累加，直到达到边界系数对应的
    W 数；查询时间的摄像机缩放会乘到实际 W 上。
    ``isReturnRealTime=True`` 时再按每段实际 BPM 积分换算为秒。
    失败返回 ``None``；零画布流速导致除零时返回 ``NaN``。
    """
    if not isinstance(chart, dict):
        return _chart_failure()
    if not _is_finite_number(time) or float(time) < 0.0:
        return _value_failure(None, "time", time, "有限数且 >= 0")
    if not _is_int(index):
        return _type_failure(None, "index", index, "int")
    if not _is_finite_number(gamespeed) or float(gamespeed) <= 0.0:
        return _value_failure(None, "gamespeed", gamespeed, "有限数且 > 0")
    coefficient = _y_border_coefficient(type)
    if coefficient is None:
        return _value_failure(
            None,
            "type",
            type,
            ", ".join(_Y_BORDER_COEFFICIENTS),
        )
    if not isinstance(isRealTime, bool):
        return _type_failure(None, "isRealTime", isRealTime, "bool")
    if not isinstance(isReturnRealTime, bool):
        return _type_failure(
            None,
            "isReturnRealTime",
            isReturnRealTime,
            "bool",
        )

    start_tick = _query_tick(chart, float(time), isRealTime)
    if start_tick is None:
        return None
    camera_scale = getCameraScaleAt(chart, time, isRealTime)
    if camera_scale is None:
        return None
    if float(camera_scale) <= 0.0:
        return _value_failure(
            None,
            "camerascale",
            camera_scale,
            "有限数且 > 0",
            path=["cameraMove", "scaleKeyPoints"],
        )
    events = _y_border_events(chart, index)
    if events is None:
        return None

    k = 6.0 + 7.0 * (float(gamespeed) - 1.0) / 9.0
    direction = 1.0 if coefficient > 0.0 else -1.0
    remaining = abs(float(coefficient))
    position = start_tick
    total_ticks = 0.0
    total_seconds = 0.0

    while remaining > 1e-12:
        if direction > 0.0:
            next_index = bisect.bisect_right(events, position)
            end = events[next_index] if next_index < len(events) else None
        else:
            previous_index = bisect.bisect_left(events, position) - 1
            end = events[previous_index] if previous_index >= 0 else None

        if end is None:
            sample = position + direction * 0.5
            span = None
        else:
            sample = (position + end) / 2.0
            span = abs(end - position)

        sample_values = _y_border_sample(chart, index, sample)
        if sample_values is None:
            return None
        bpm, speed = sample_values
        if speed < 0.0:
            return _value_failure(
                None,
                "speed",
                speed,
                ">= 0",
                path=["canvasMoves", index, "speedKeyPoints"],
                code="canvas.negative_speed",
            )
        w = bpm / (60.0 * speed * k) * float(camera_scale)
        if w == 0.0 or not math.isfinite(w):
            return math.nan
        if w < 0.0:
            return _value_failure(
                None,
                "W",
                w,
                "有限且 > 0",
                path=["bpmShifts", "cameraMove", "canvasMoves"],
                code="y_border.invalid_width",
            )

        units_per_tick = 1.0 / w
        if span is None:
            needed_ticks = remaining / units_per_tick
            total_ticks += needed_ticks
            total_seconds += needed_ticks * 60.0 / bpm
            remaining = 0.0
        else:
            contribution = span * units_per_tick
            if contribution >= remaining:
                needed_ticks = remaining / units_per_tick
                total_ticks += needed_ticks
                total_seconds += needed_ticks * 60.0 / bpm
                remaining = 0.0
            else:
                total_ticks += span
                total_seconds += span * 60.0 / bpm
                remaining -= contribution
                position = end

    if isReturnRealTime:
        return total_seconds * direction
    return total_ticks * direction


def getGameScale(
    Xwidth: float,
    Ywidth: float,
    isPCVersion: bool = False,
) -> float | None:
    """根据屏幕宽高计算游戏区域缩放比例。

    ``Xwidth`` / ``Ywidth`` 必须大于 0。移动端返回 ``Sx``；PC 端返回
    ``Sx * Sc``。失败返回 ``None``。
    """
    if not _is_finite_number(Xwidth) or float(Xwidth) <= 0.0:
        return _value_failure(None, "Xwidth", Xwidth, "有限数且 > 0")
    if not _is_finite_number(Ywidth) or float(Ywidth) <= 0.0:
        return _value_failure(None, "Ywidth", Ywidth, "有限数且 > 0")
    if not isinstance(isPCVersion, bool):
        return _type_failure(None, "isPCVersion", isPCVersion, "bool")

    ratio = float(Xwidth) / float(Ywidth)
    if isPCVersion:
        sx = 32.0 / 29.0
        sc = ratio * 9.0 / 16.0 if ratio <= 16.0 / 9.0 else 1.0
        return sx * sc

    if ratio <= 18.0 / 29.0:
        return ratio * 16.0 / 9.0
    return 32.0 / 29.0


def getLineWidth(
    gamescale: float = 1.0,
) -> float | None:
    """计算引导线宽，单位为 ``xPosition``。

    ``gamescale`` 必须大于 0；成功返回 ``1 / (125 * gamescale)``。
    """
    if not _is_finite_number(gamescale) or float(gamescale) <= 0.0:
        return _value_failure(None, "gamescale", gamescale, "有限数且 > 0")
    return 1.0 / (125.0 * float(gamescale))


def getRingRadius() -> float:
    """查询判定环半径，单位为 ``xPosition``。

    返回固定值 ``1 / 18``。该函数没有失败路径，因此不提供
    ``isReturnException``。
    """
    return 1.0 / 18.0


_SHADE_THRESHOLDS = tuple(index / 511.0 for index in range(512))


def getShadeOpacity(ratio: float) -> int | None:
    """查询底部到顶部遮罩在相对比例处的透明度。

    ``ratio`` 必须在 ``0.0`` 到 ``1.0`` 之间（包含两端）。按
    ``row/511 <= ratio < (row + 1)/511`` 选择内置表中的一行，
    ``ratio=1.0`` 时取最后一行，返回该行
    ``round(alpha_mean_0_255)``。失败返回 ``None``。
    """
    if not _is_finite_number(ratio):
        return _type_failure(None, "ratio", ratio, "有限数")
    value = float(ratio)
    if value < 0.0 or value > 1.0:
        return _value_failure(None, "ratio", ratio, "0.0..1.0")

    row = bisect.bisect_right(_SHADE_THRESHOLDS, value) - 1
    if row < 0:
        return fail(
            None,
            "无法把 ratio 映射到遮罩透明度表行",
            code="shade.row_out_of_range",
            parameter="ratio",
            actual=ratio,
            expected="0.0..1.0",
        )
    if row >= len(SHADE_OPACITY_ALPHA):
        row = len(SHADE_OPACITY_ALPHA) - 1
    return SHADE_OPACITY_ALPHA[row]


install_exception_api(globals())
