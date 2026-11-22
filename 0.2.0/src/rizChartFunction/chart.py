"""谱面字段修改与颜色工具。"""

from __future__ import annotations

import bisect
import math

from ._internal import (
    _apply_floor_plan,
    _bpm_seconds,
    _canvas_ref,
    _canvas_x_at,
    _ease,
    _find_canvas,
    _is_finite_number,
    _is_int,
    _is_number,
    _make_floor_plan,
    _parse_color,
    _round_color_channel,
    _seconds_at,
    _seconds_to_tick,
)

__all__ = [
    "setBaseBpm",
    "setDelay",
    "setFileVersion",
    "rgb",
    "rgba",
    "mixColor",
    "splitColor",
    "setNormalTheme",
    "setRiztime",
    "addRiztime",
    "deleteRiztime",
    "addCanvas",
    "deleteCanvas",
    "addCanvasPosition",
    "setCanvasPosition",
    "deleteCanvasPosition",
    "addCanvasSpeed",
    "setCanvasSpeed",
    "deleteCanvasSpeed",
    "addCameraPosition",
    "setCameraPosition",
    "deleteCameraPosition",
    "addCameraScale",
    "setCameraScale",
    "deleteCameraScale",
    "createLinePoint",
    "createRingPoint",
    "addRingPoint",
    "setRingPoint",
    "deleteRingPoint",
    "addLine",
    "deleteLine",
    "addLinePoint",
    "setLinePoint",
    "deleteLinePoint",
    "addLineColor",
    "setLineColor",
    "deleteLineColor",
    "addNote",
    "setNote",
    "deleteNote",
    "addBpmShift",
    "setBpmShift",
    "deleteBpmShift",
]


def setBaseBpm(
    chart: dict,
    basebpm: float,
    isFixedBpm: bool = False,
) -> object | None:
    """重置基准 BPM，返回原 BPM。

    ``isFixedBpm`` 为 ``True`` 时，同时按比例调整 ``bpmShifts`` 中的
    ``value``，使每个节点的实际 BPM（``bPM * value``）保持不变。
    成功修改后会按新的 BPM 时间轴重新计算整份谱面的相关
    ``floorPosition``。

    谱面必须在 ``time=0.0`` 处有一个 BPM 节点，否则返回 ``None``。
    """
    if not isinstance(chart, dict) or "bPM" not in chart:
        return None
    if not _is_finite_number(basebpm) or basebpm <= 0:
        return None

    old_bpm = chart["bPM"]

    if not isFixedBpm:
        chart["bPM"] = basebpm
        plan = _make_floor_plan(chart)
        if plan is None:
            chart["bPM"] = old_bpm
            return None
        _apply_floor_plan(plan)
        return old_bpm

    shifts = chart.get("bpmShifts")
    if (
        not isinstance(shifts, list)
        or not shifts
        or not _is_number(old_bpm)
        or old_bpm <= 0
    ):
        return None

    new_values = []
    for key_point in shifts:
        if not isinstance(key_point, dict):
            return None
        value = key_point.get("value")
        if not _is_number(value):
            return None
        new_values.append(old_bpm * value / basebpm)

    old_values = [key_point["value"] for key_point in shifts]

    chart["bPM"] = basebpm
    for key_point, value in zip(shifts, new_values):
        key_point["value"] = value

    plan = _make_floor_plan(chart)
    if plan is None:
        chart["bPM"] = old_bpm
        for key_point, value in zip(shifts, old_values):
            key_point["value"] = value
        return None
    _apply_floor_plan(plan)

    return old_bpm


def setDelay(chart: dict, delay: int) -> object | None:
    """重置谱面延迟，返回原 ``chartDelayMs``。

    ``chartDelayMs`` 必须是 ``int``（``bool`` 不接受）；类型不正确时
    返回 ``None``，且不修改谱面。
    """
    if not isinstance(chart, dict) or "chartDelayMs" not in chart:
        return None
    if not _is_int(delay):
        return None

    old_delay = chart["chartDelayMs"]
    chart["chartDelayMs"] = delay
    return old_delay


def setFileVersion(chart: dict, fileversion: int) -> object | None:
    """重置文件版本，返回原 ``fileVersion``。

    ``fileVersion`` 必须是 ``int``（``bool`` 不接受）；类型不正确时
    返回 ``None``，且不修改谱面。
    """
    if not isinstance(chart, dict) or "fileVersion" not in chart:
        return None
    if not _is_int(fileversion):
        return None

    old_version = chart["fileVersion"]
    chart["fileVersion"] = fileversion
    return old_version


def _channel(value: object) -> int:
    """把单个通道转换为 0-255 的整数。

    ``int`` 按 0-255 处理，``float`` 按 0.0-1.0 处理。越界值会被夹到
    边界，非数字视为 0。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0

    if isinstance(value, float):
        if math.isnan(value):
            return 0
        if value < 0.0:
            value = 0.0
        elif value > 1.0:
            value = 1.0
        return int(value * 255 + 0.5)

    if value < 0:
        value = 0
    elif value > 255:
        value = 255
    return value


def rgb(red: int | float, green: int | float, blue: int | float) -> list[int]:
    """把 RGB 通道转换为 0-255 的 ``[r, g, b, 255]``。

    每个通道可以是 ``int``（0-255）或 ``float``（0.0-1.0），可混用。
    """
    return [
        _channel(red),
        _channel(green),
        _channel(blue),
        255,
    ]


def rgba(
    red: int | float,
    green: int | float,
    blue: int | float,
    alpha: int | float,
) -> list[int]:
    """把 RGBA 通道转换为 0-255 的 ``[r, g, b, a]``。

    每个通道可以是 ``int``（0-255）或 ``float``（0.0-1.0），可混用。
    """
    return [
        _channel(red),
        _channel(green),
        _channel(blue),
        _channel(alpha),
    ]


def mixColor(
    basecolor: str | list,
    covercolor: str | list,
) -> list[int] | None:
    """按 Rizline 覆盖色公式混合两个颜色。

    返回 ``[r, g, b, a]``。公式为::

        R0' = R1' * (1 - A2') + R2' * A2'
        G0' = G1' * (1 - A2') + G2' * A2'
        B0' = B1' * (1 - A2') + B2' * A2'
        A0 = A1

    其中 1 为基础色、2 为覆盖色，通道值归一化到 0-1，RGB 最后四舍五入
    回 0-255。输入非法时返回 ``None``。
    """
    base = _parse_color(basecolor)
    cover = _parse_color(covercolor)
    if base is None or cover is None:
        return None

    alpha = cover["a"] / 255.0
    inverse = 1.0 - alpha
    return [
        _round_color_channel(
            base["r"] * inverse + cover["r"] * alpha
        ),
        _round_color_channel(
            base["g"] * inverse + cover["g"] * alpha
        ),
        _round_color_channel(
            base["b"] * inverse + cover["b"] * alpha
        ),
        base["a"],
    ]


def _integer_interval(
    low: float,
    high: float,
) -> tuple[int, int] | None:
    """返回满足 ``low <= n < high`` 的 0-255 整数区间。"""
    start = max(0, math.ceil(low))
    end = min(255, math.ceil(high) - 1)
    if start > end:
        return None
    return start, end


def _interval_value(interval: tuple[int, int], target: float) -> int:
    low, high = interval
    value = _round_color_channel(target)
    return min(high, max(low, value))


def _derive_base_from_mix(
    mix: dict,
    cover: dict,
) -> list[int] | None:
    """已知覆盖色和混合色，推导基础色。"""
    if cover["a"] == 255:
        if all(
            mix[channel] == cover[channel]
            for channel in ("r", "g", "b")
        ):
            return [mix["r"], mix["g"], mix["b"], mix["a"]]
        return None
    if cover["a"] == 0:
        return [mix["r"], mix["g"], mix["b"], mix["a"]]

    alpha = cover["a"] / 255.0
    inverse = 1.0 - alpha
    intervals = []
    targets = []
    for channel in ("r", "g", "b"):
        value = (mix[channel] - cover[channel] * alpha) / inverse
        low = (
            mix[channel] - 0.5 - cover[channel] * alpha
        ) / inverse
        high = (
            mix[channel] + 0.5 - cover[channel] * alpha
        ) / inverse
        interval = _integer_interval(low, high)
        if interval is None:
            return None
        intervals.append(interval)
        targets.append(value)

    base = [
        _interval_value(interval, target)
        for interval, target in zip(intervals, targets)
    ]
    base.append(mix["a"])
    if mixColor(base, cover) != [
        mix["r"],
        mix["g"],
        mix["b"],
        mix["a"],
    ]:
        return None
    return base


def _derive_cover_from_mix(
    mix: dict,
    base: dict,
) -> list[int] | None:
    """已知基础色和混合色，推导一个覆盖色。

    覆盖色不唯一；返回能够复现混合色、且 alpha 最小的覆盖色。
    """
    if mix["a"] != base["a"]:
        return None

    target = [mix["r"], mix["g"], mix["b"], mix["a"]]
    if all(mix[channel] == base[channel] for channel in ("r", "g", "b")):
        cover = [mix["r"], mix["g"], mix["b"], 0]
        return cover if mixColor(base, cover) == target else None

    for cover_alpha in range(1, 256):
        alpha = cover_alpha / 255.0
        inverse = 1.0 - alpha
        intervals = []
        targets = []
        valid = True
        for channel in ("r", "g", "b"):
            value = base[channel] + (
                mix[channel] - base[channel]
            ) / alpha
            low = (
                mix[channel] - 0.5 - base[channel] * inverse
            ) / alpha
            high = (
                mix[channel] + 0.5 - base[channel] * inverse
            ) / alpha
            interval = _integer_interval(low, high)
            if interval is None:
                valid = False
                break
            intervals.append(interval)
            targets.append(value)
        if not valid:
            continue

        cover = [
            _interval_value(interval, target_value)
            for interval, target_value in zip(intervals, targets)
        ]
        cover.append(cover_alpha)
        if mixColor(base, cover) == target:
            return cover
    return None


def splitColor(
    mixcolor: str | list,
    basecolor: str | list | None = None,
    covercolor: str | list | None = None,
) -> list[int] | bool | None:
    """拆分混合色、基础色和覆盖色。

    - 只给 ``basecolor``：推导覆盖色
    - 只给 ``covercolor``：推导基础色
    - 两者都给：校验混合结果，匹配返回 ``True``，不匹配返回 ``False``
    - 两者都不给、输入非法或无法推导：返回 ``None``

    覆盖色在数学上通常不唯一；本函数返回能复现混合色且 alpha 最小的
    覆盖色。基础色在覆盖色 alpha 为 255 时也不唯一，此时返回混合色本身
    作为规范基础色；若混合色 RGB 与覆盖色不一致则返回 ``None``。
    """
    mix = _parse_color(mixcolor)
    if mix is None:
        return None

    if basecolor is not None and covercolor is not None:
        base = _parse_color(basecolor)
        cover = _parse_color(covercolor)
        if base is None or cover is None:
            return None
        return mixColor(base, cover) == [
            mix["r"],
            mix["g"],
            mix["b"],
            mix["a"],
        ]

    if basecolor is not None:
        base = _parse_color(basecolor)
        if base is None:
            return None
        return _derive_cover_from_mix(mix, base)

    if covercolor is not None:
        cover = _parse_color(covercolor)
        if cover is None:
            return None
        return _derive_base_from_mix(mix, cover)

    return None


def _export_color(value: object) -> list[int] | None:
    color = _parse_color(value)
    if color is None:
        return None
    return [color["r"], color["g"], color["b"], color["a"]]


def _export_key_point(value: object) -> dict | None:
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


def _export_bpm_shift(value: object) -> dict | None:
    spec = _export_key_point(value)
    if spec is None or spec["value"] <= 0:
        return None
    return spec


def _export_line_point(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    time = value.get("time")
    x_position = value.get("xPosition")
    canvas_index = value.get("canvasIndex")
    ease_type = value.get("easeType")
    color = _export_color(value.get("color"))
    if not _is_finite_number(time) or time < 0:
        return None
    if not _is_finite_number(x_position):
        return None
    if not _is_int(canvas_index):
        return None
    if not _is_int(ease_type) or not 0 <= ease_type <= 18:
        return None
    if color is None:
        return None
    return {
        "time": float(time),
        "xPosition": float(x_position),
        "canvasIndex": canvas_index,
        "easeType": ease_type,
        "color": color,
    }


def _export_color_change(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    time = value.get("time")
    start_color = _export_color(value.get("startColor"))
    end_color = _export_color(value.get("endColor"))
    if not _is_finite_number(time) or time < 0:
        return None
    if start_color is None or end_color is None:
        return None
    return {
        "time": float(time),
        "startColor": start_color,
        "endColor": end_color,
    }


def _export_note(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    note_type = value.get("type")
    head_time = value.get("time")
    if not _is_int(note_type) or note_type not in (0, 1, 2):
        return None
    if not _is_finite_number(head_time) or head_time < 0:
        return None

    spec = {
        "type": note_type,
        "time": float(head_time),
    }
    if note_type == 2:
        extra = value.get("otherInformations")
        if not isinstance(extra, list) or len(extra) != 3:
            return None
        tail_time = extra[0]
        if not _is_finite_number(tail_time) or tail_time <= head_time:
            return None
        spec["endtime"] = float(tail_time)
    return spec


def _export_canvas(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    index = value.get("index")
    x_points = value.get("xPositionKeyPoints")
    speed_points = value.get("speedKeyPoints")
    if not _is_int(index) or index < 0:
        return None
    if not isinstance(x_points, list) or not x_points:
        return None
    if not isinstance(speed_points, list) or not speed_points:
        return None

    x_specs = [_export_key_point(point) for point in x_points]
    speed_specs = [_export_key_point(point) for point in speed_points]
    if any(spec is None for spec in x_specs):
        return None
    if any(spec is None for spec in speed_specs):
        return None
    return {
        "index": index,
        "xPositionKeyPoints": x_specs,
        "speedKeyPoints": speed_specs,
    }


def _export_line(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    points = value.get("linePoints")
    notes = value.get("notes")
    rings = value.get("judgeRingColor")
    colors = value.get("lineColor")
    if not isinstance(points, list) or len(points) < 2:
        return None
    if not isinstance(notes, list):
        return None
    if not isinstance(rings, list) or not rings:
        return None
    if not isinstance(colors, list):
        return None

    point_specs = [_export_line_point(point) for point in points]
    note_specs = [_export_note(note) for note in notes]
    ring_specs = [_export_color_change(ring) for ring in rings]
    color_specs = [_export_color_change(color) for color in colors]
    if any(spec is None for spec in point_specs):
        return None
    if any(spec is None for spec in note_specs):
        return None
    if any(spec is None for spec in ring_specs):
        return None
    if any(spec is None for spec in color_specs):
        return None
    return {
        "linePoints": point_specs,
        "notes": note_specs,
        "judgeRingColor": ring_specs,
        "lineColor": color_specs,
    }


def _export_theme(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    colors = value.get("colorsList")
    if not isinstance(colors, list) or len(colors) != 3:
        return None
    specs = [_export_color(color) for color in colors]
    if any(spec is None for spec in specs):
        return None
    return {"colorsList": specs}


def _export_riztime(
    theme_index: int,
    challenge_index: int,
    theme: object,
    challenge: object,
) -> dict | None:
    theme_spec = _export_theme(theme)
    if theme_spec is None or not isinstance(challenge, dict):
        return None

    values = {}
    for key in ("checkPoint", "start", "end", "transTime"):
        value = challenge.get(key)
        if not _is_finite_number(value):
            return None
        values[key] = float(value)
    if values["end"] < values["start"] or values["transTime"] < 0:
        return None

    return {
        "themeIndex": theme_index,
        "challengeIndex": challenge_index,
        "colorsList": theme_spec["colorsList"],
        **values,
    }


def setNormalTheme(
    chart: dict,
    color1: str | list,
    color2: str | list,
    color3: str | list,
) -> dict | None:
    """设置第一个主题的三种颜色，返回原主题规格 Dict。

    ``color1`` / ``color2`` / ``color3`` 支持 ``#RRGGBB``、``#RRGGBBAA``、
    ``RRGGBB``、``RRGGBBAA``，或 ``[r, g, b]`` / ``[r, g, b, a]``。
    """
    colors = [_parse_color(color) for color in (color1, color2, color3)]
    if any(color is None for color in colors):
        return None

    if not isinstance(chart, dict):
        return None

    themes = chart.get("themes")
    if not isinstance(themes, list) or not themes:
        return None

    old_theme = themes[0]
    if not isinstance(old_theme, dict):
        return None
    old_spec = _export_theme(old_theme)
    if old_spec is None:
        return None

    new_theme = dict(old_theme)
    new_theme["colorsList"] = colors
    themes[0] = new_theme

    return old_spec


def _resolve_riztime_index(
    index: object,
    themes: list,
    challenge_times: list,
) -> tuple[int, int] | None:
    if not _is_int(index):
        return None
    if index == 0:
        index = 1

    if index > 0:
        theme_index = index
        challenge_index = index - 1
    else:
        theme_index = len(themes) + index
        challenge_index = len(challenge_times) + index

    if not 0 <= theme_index < len(themes):
        return None
    if not 0 <= challenge_index < len(challenge_times):
        return None
    if theme_index == 0:
        return None

    return theme_index, challenge_index


def _sorted_starts(
    challenge_times: list,
    skip_index: int | None = None,
) -> list | None:
    """返回 challengeTimes 的 start 列表，要求全部合法且非递减。"""
    starts = []
    for position, challenge in enumerate(challenge_times):
        if position == skip_index:
            continue
        if not isinstance(challenge, dict):
            return None
        start = challenge.get("start")
        if not _is_number(start):
            return None
        starts.append(start)

    for left, right in zip(starts, starts[1:]):
        if left > right:
            return None

    return starts


def setRiztime(
    chart: dict,
    index: int = -1,
    color1: str | list | None = None,
    color2: str | list | None = None,
    color3: str | list | None = None,
    start: float | None = None,
    end: float | None = None,
    transtime: float | None = None,
    checkpoint: float | None = None,
) -> dict | None:
    """设置一个 Riztime 的主题颜色与时间，返回 Riztime 规格 Dict。

    成功时返回原 Riztime 的合并规格 Dict。颜色参数为
    ``None`` 时保持该颜色不变；时间参数为 ``None`` 时保持原值。
    """
    if not isinstance(chart, dict):
        return None

    themes = chart.get("themes")
    challenge_times = chart.get("challengeTimes")
    if not isinstance(themes, list) or not isinstance(challenge_times, list):
        return None

    resolved = _resolve_riztime_index(index, themes, challenge_times)
    if resolved is None:
        return None
    theme_index, challenge_index = resolved

    old_theme = themes[theme_index]
    old_challenge = challenge_times[challenge_index]
    if not isinstance(old_theme, dict) or not isinstance(old_challenge, dict):
        return None
    old_spec = _export_riztime(
        theme_index,
        challenge_index,
        old_theme,
        old_challenge,
    )
    if old_spec is None:
        return None

    color_args = (color1, color2, color3)
    provided_colors = [color is not None for color in color_args]
    parsed_colors = [None, None, None]
    for position, color in enumerate(color_args):
        if color is None:
            continue
        parsed = _parse_color(color)
        if parsed is None:
            return None
        parsed_colors[position] = parsed

    challenge_values = {
        "start": start,
        "end": end,
        "transTime": transtime,
        "checkPoint": checkpoint,
    }
    for value in challenge_values.values():
        if value is not None and not _is_number(value):
            return None

    effective_start = start if start is not None else old_challenge.get("start")
    effective_end = end if end is not None else old_challenge.get("end")
    if start is not None or end is not None:
        if not _is_number(effective_start) or not _is_number(effective_end):
            return None
        if effective_end < effective_start:
            return None
    if transtime is not None and transtime < 0:
        return None

    has_colors = any(provided_colors)
    has_challenge_values = any(
        value is not None for value in challenge_values.values()
    )

    new_theme = old_theme
    if has_colors:
        if all(provided_colors):
            new_colors = parsed_colors
        else:
            old_colors = old_theme.get("colorsList")
            if not isinstance(old_colors, list) or len(old_colors) != 3:
                return None
            new_colors = list(old_colors)
            for position, parsed in enumerate(parsed_colors):
                if parsed is not None:
                    new_colors[position] = parsed

        new_theme = dict(old_theme)
        new_theme["colorsList"] = new_colors

    new_challenge = old_challenge
    if has_challenge_values:
        new_challenge = dict(old_challenge)
        for key, value in challenge_values.items():
            if value is not None:
                new_challenge[key] = value

    if start is not None:
        remaining_starts = _sorted_starts(
            challenge_times,
            skip_index=challenge_index,
        )
        if remaining_starts is None:
            return None
        insert_position = bisect.bisect_right(remaining_starts, start)

        new_themes = [
            theme
            for position, theme in enumerate(themes)
            if position != theme_index
        ]
        new_challenge_times = [
            challenge
            for position, challenge in enumerate(challenge_times)
            if position != challenge_index
        ]
        if insert_position + 1 > len(new_themes):
            return None

        new_themes.insert(insert_position + 1, new_theme)
        new_challenge_times.insert(insert_position, new_challenge)
        themes[:] = new_themes
        challenge_times[:] = new_challenge_times
    else:
        if has_colors:
            themes[theme_index] = new_theme
        if has_challenge_values:
            challenge_times[challenge_index] = new_challenge

    return old_spec


def addRiztime(
    chart: dict,
    color1: str | list,
    color2: str | list,
    color3: str | list,
    start: float = 0.0,
    end: float = 0.0,
    transtime: float = 0.5,
    checkpoint: float = 0.0,
) -> int | None:
    """按 ``start`` 升序插入一个 Riztime，成功返回 Riztime 索引。

    如果当前只有一个 Riztime，且它的 ``start`` 与 ``end`` 相同，则视为
    占位用的空 Riztime：先删除它及其配对主题，再插入新的 Riztime。
    """
    if not isinstance(chart, dict):
        return None

    themes = chart.get("themes")
    challenge_times = chart.get("challengeTimes")
    if not isinstance(themes, list) or not isinstance(challenge_times, list):
        return None

    colors = [_parse_color(color) for color in (color1, color2, color3)]
    if any(color is None for color in colors):
        return None

    for value in (start, end, transtime, checkpoint):
        if not _is_number(value):
            return None
    if end < start or transtime < 0:
        return None

    if len(themes) != len(challenge_times) + 1:
        return None

    empty_single = (
        len(challenge_times) == 1
        and isinstance(challenge_times[0], dict)
        and _is_number(challenge_times[0].get("start"))
        and _is_number(challenge_times[0].get("end"))
        and challenge_times[0]["start"] == challenge_times[0]["end"]
    )

    if empty_single:
        new_themes = list(themes)
        del new_themes[1]
        new_challenge_times = []
    else:
        new_themes = list(themes)
        new_challenge_times = list(challenge_times)

    starts = _sorted_starts(new_challenge_times)
    if starts is None:
        return None

    insert_position = bisect.bisect_right(starts, start)
    if insert_position + 1 > len(new_themes):
        return None

    new_theme = {"colorsList": colors}
    new_challenge = {
        "checkPoint": checkpoint,
        "start": start,
        "end": end,
        "transTime": transtime,
    }

    new_themes.insert(insert_position + 1, new_theme)
    new_challenge_times.insert(insert_position, new_challenge)

    themes[:] = new_themes
    challenge_times[:] = new_challenge_times

    return insert_position


def deleteRiztime(chart: dict, index: int = -1) -> dict | None:
    """删除指定 Riztime，成功时返回原 Riztime 的合并规格 Dict。"""
    if not isinstance(chart, dict):
        return None

    themes = chart.get("themes")
    challenge_times = chart.get("challengeTimes")
    if not isinstance(themes, list) or not isinstance(challenge_times, list):
        return None

    resolved = _resolve_riztime_index(index, themes, challenge_times)
    if resolved is None:
        return None
    theme_index, challenge_index = resolved

    old_theme = themes[theme_index]
    old_challenge = challenge_times[challenge_index]
    if not isinstance(old_theme, dict) or not isinstance(old_challenge, dict):
        return None
    old_spec = _export_riztime(
        theme_index,
        challenge_index,
        old_theme,
        old_challenge,
    )
    if old_spec is None:
        return None

    del themes[theme_index]
    del challenge_times[challenge_index]

    return old_spec


def _resolve_insert_position(index: object, length: int) -> int | None:
    if index is None:
        return length
    if not _is_int(index):
        return None

    position = length + index if index < 0 else index
    if not 0 <= position <= length:
        return None
    return position


def addCanvas(chart: dict, index: int | None = None) -> int | None:
    """插入一个画布，成功返回新画布的 index，失败返回 ``None``。

    新画布使用与 ``new()`` 中第 0 个画布相同的初始化结构。插入位置之后
    的画布 ``index`` 会顺延，并同步更新引导线节点与 Hold 音符中绑定的
    画布索引。
    """
    if not isinstance(chart, dict):
        return None

    canvas_moves = chart.get("canvasMoves")
    if not isinstance(canvas_moves, list):
        return None

    position = _resolve_insert_position(index, len(canvas_moves))
    if position is None:
        return None

    for canvas_index, canvas in enumerate(canvas_moves):
        if (
            not isinstance(canvas, dict)
            or not _is_int(canvas.get("index"))
            or canvas["index"] != canvas_index
        ):
            return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    for line in lines:
        if not isinstance(line, dict):
            return None
        line_points = line.get("linePoints")
        notes = line.get("notes")
        if not isinstance(line_points, list) or not isinstance(notes, list):
            return None

        for point in line_points:
            if not isinstance(point, dict) or not _is_int(point.get("canvasIndex")):
                return None

        for note in notes:
            if not isinstance(note, dict):
                return None
            if "otherInformations" not in note:
                continue
            extra = note["otherInformations"]
            if not isinstance(extra, list) or len(extra) not in (0, 3):
                return None
            if len(extra) == 3 and not _is_number(extra[1]):
                return None

    for canvas in canvas_moves[position:]:
        canvas["index"] += 1

    for line in lines:
        for point in line["linePoints"]:
            if point["canvasIndex"] >= position:
                point["canvasIndex"] += 1
        for note in line["notes"]:
            extra = note.get("otherInformations")
            if (
                isinstance(extra, list)
                and len(extra) == 3
                and extra[1] >= position
            ):
                extra[1] += 1

    new_canvas = {
        "index": position,
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

    canvas_moves.insert(position, new_canvas)
    return position


def _resolve_existing_index(index: object, length: int) -> int | None:
    if not _is_int(index):
        return None
    if index < 0:
        index += length
    if 0 <= index < length:
        return index
    return None


def _is_canvas_reference(value: object) -> bool:
    return _canvas_ref(value) is not None


def _collect_canvas_references(lines: list) -> list | None:
    references = []
    for line in lines:
        if not isinstance(line, dict):
            return None
        line_points = line.get("linePoints")
        notes = line.get("notes")
        if not isinstance(line_points, list) or not isinstance(notes, list):
            return None

        for point in line_points:
            if not isinstance(point, dict) or not _is_int(point.get("canvasIndex")):
                return None
            references.append((point["canvasIndex"], "point", point))

        for note in notes:
            if not isinstance(note, dict):
                return None
            if "otherInformations" not in note:
                continue
            extra = note["otherInformations"]
            if not isinstance(extra, list) or len(extra) not in (0, 3):
                return None
            if len(extra) == 3:
                if not _is_canvas_reference(extra[1]):
                    return None
                references.append((extra[1], "note", note))

    return references


def deleteCanvas(
    chart: dict,
    index: int = -1,
    isRelative: bool = False,
) -> dict | None:
    """删除一个空画布，成功返回被删除画布的规格 Dict。

    ``isRelative=False`` 时 ``index`` 是画布索引；为 ``True`` 时 ``index``
    是空画布列表中的位置。两者均为 0 起，负数从末尾计算。只有没有任何
    引导线节点或音符绑定到该画布时才能删除。
    """
    if not isinstance(chart, dict):
        return None

    canvas_moves = chart.get("canvasMoves")
    lines = chart.get("lines")
    if not isinstance(canvas_moves, list) or not isinstance(lines, list):
        return None

    for canvas_index, canvas in enumerate(canvas_moves):
        if (
            not isinstance(canvas, dict)
            or not _is_int(canvas.get("index"))
            or canvas["index"] != canvas_index
        ):
            return None

    references = _collect_canvas_references(lines)
    if references is None:
        return None
    referenced = {value for value, _, _ in references}

    if isRelative:
        empty_indices = [
            canvas_index
            for canvas_index in range(len(canvas_moves))
            if canvas_index not in referenced
        ]
        resolved = _resolve_existing_index(index, len(empty_indices))
        if resolved is None:
            return None
        target = empty_indices[resolved]
    else:
        target = _resolve_existing_index(index, len(canvas_moves))
        if target is None or target in referenced:
            return None

    deleted_spec = _export_canvas(canvas_moves[target])
    if deleted_spec is None:
        return None
    canvas_moves.pop(target)

    for canvas in canvas_moves[target:]:
        canvas["index"] -= 1

    for value, kind, target_object in references:
        if value <= target:
            continue
        if kind == "point":
            target_object["canvasIndex"] -= 1
        else:
            target_object["otherInformations"][1] -= 1

    return deleted_spec


def _canvas_position_points(canvas: dict) -> list | None:
    """取出并校验 xPositionKeyPoints，要求 time 非递减。"""
    key_points = canvas.get("xPositionKeyPoints")
    if not isinstance(key_points, list):
        return None

    previous_time = None
    for key_point in key_points:
        if not isinstance(key_point, dict):
            return None
        key_time = key_point.get("time")
        if not _is_finite_number(key_time) or key_time < 0:
            return None
        if previous_time is not None and key_time < previous_time:
            return None
        previous_time = key_time

    return key_points


def _ease_type(value: object, clamp: bool) -> int | None:
    """校验缓动类型；``clamp`` 为真时把越界值夹到 0-18。"""
    if not _is_int(value):
        return None
    if clamp:
        return max(0, min(18, value))
    return value if 0 <= value <= 18 else None


def _node_time(
    chart: dict,
    time: object,
    is_real_time: bool,
) -> float | None:
    """把节点时间转换为 tick；``is_real_time`` 为真时按秒换算。"""
    if not _is_finite_number(time) or time < 0:
        return None

    if not is_real_time:
        return float(time)

    if not isinstance(chart, dict):
        return None

    timeline = _bpm_seconds(chart)
    if timeline is None:
        return None
    base_bpm, times, values, seconds = timeline
    tick = _seconds_to_tick(
        float(time),
        base_bpm,
        times,
        values,
        seconds,
    )
    if tick is None or tick < 0:
        return None
    return tick


def addCanvasPosition(
    chart: dict,
    index: int,
    time: float,
    position: float = 0.0,
    easetype: int = 0,
    isRealTime: bool = False,
) -> int | None:
    """为指定画布的 ``xPositionKeyPoints`` 添加一个节点。

    ``index`` 为画布索引，负数从末尾计算。``time`` 为节点时间，默认是
    tick；``isRealTime=True`` 时按实际秒数换算。时间相同的节点会排在
    已有节点之后。``easetype`` 越界时夹到 0-18。
    """
    canvas = _find_canvas(chart, index)
    if canvas is None:
        return None

    key_points = _canvas_position_points(canvas)
    if key_points is None:
        return None

    if not _is_finite_number(position):
        return None

    ease_type = _ease_type(easetype, clamp=True)
    if ease_type is None:
        return None

    target_time = _node_time(chart, time, isRealTime)
    if target_time is None:
        return None

    insert_at = bisect.bisect_right(
        [key_point["time"] for key_point in key_points],
        target_time,
    )
    key_points.insert(
        insert_at,
        {
            "time": target_time,
            "value": float(position),
            "easeType": ease_type,
            "floorPosition": 0.0,
        },
    )
    return insert_at


def setCanvasPosition(
    chart: dict,
    canvasindex: int,
    positionindex: int = -1,
    time: float | None = None,
    position: float | None = None,
    easetype: int | None = None,
    isRealTime: bool = False,
) -> dict | None:
    """修改画布 ``xPositionKeyPoints`` 中的一个节点，返回原节点规格 Dict。

    ``positionindex`` 从 0 起，负数从末尾计算。所有修改参数为 ``None``
    时不做修改，直接返回原节点规格 Dict。修改 ``time`` 后会自动按时间重排。
    指向第 0 个节点时不能修改 ``time``（允许传入 ``0.0``）。
    ``easetype`` 越界时夹到 0-18。
    """
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None

    key_points = _canvas_position_points(canvas)
    if key_points is None:
        return None

    target_index = _resolve_existing_index(positionindex, len(key_points))
    if target_index is None:
        return None

    old_node = key_points[target_index]
    old_spec = _export_key_point(old_node)
    if old_spec is None:
        return None
    current_time = old_node["time"]

    if time is None:
        target_time = current_time
    else:
        target_time = _node_time(chart, time, isRealTime)
        if target_time is None:
            return None
        if (
            target_index == 0
            and target_time != 0.0
            and target_time != current_time
        ):
            return None

    if position is None:
        new_position = old_node.get("value")
    else:
        if not _is_finite_number(position):
            return None
        new_position = float(position)

    if easetype is None:
        new_ease = old_node.get("easeType")
    else:
        new_ease = _ease_type(easetype, clamp=True)
        if new_ease is None:
            return None

    if (
        target_time == current_time
        and new_position == old_node.get("value")
        and new_ease == old_node.get("easeType")
    ):
        return old_spec

    new_node = dict(old_node)
    new_node["time"] = target_time
    new_node["value"] = new_position
    new_node["easeType"] = new_ease

    if target_time == current_time:
        key_points[target_index] = new_node
    else:
        remaining = (
            key_points[:target_index] + key_points[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [key_point["time"] for key_point in remaining],
            target_time,
        )
        remaining.insert(insert_at, new_node)
        key_points[:] = remaining

    return old_spec


def deleteCanvasPosition(
    chart: dict,
    canvasindex: int,
    positionindex: int = -1,
) -> dict | None:
    """删除画布的 ``xPositionKeyPoints`` 节点，返回原节点规格 Dict。

    ``positionindex`` 从 0 起，负数从末尾计算。指向第 0 个节点时不删除，
    而是重置为 ``new()`` 中的初始节点。
    """
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None

    key_points = _canvas_position_points(canvas)
    if key_points is None:
        return None

    target_index = _resolve_existing_index(positionindex, len(key_points))
    if target_index is None:
        return None

    old_node = key_points[target_index]
    old_spec = _export_key_point(old_node)
    if old_spec is None:
        return None
    if target_index == 0:
        key_points[0] = {
            "time": 0.0,
            "value": 0.0,
            "easeType": 0,
            "floorPosition": 0.0,
        }
    else:
        key_points.pop(target_index)

    return old_spec


def _canvas_speed_points(canvas: dict) -> list | None:
    """取出并校验 speedKeyPoints，要求 time 非递减。"""
    key_points = canvas.get("speedKeyPoints")
    if not isinstance(key_points, list):
        return None

    previous_time = None
    for key_point in key_points:
        if not isinstance(key_point, dict):
            return None
        key_time = key_point.get("time")
        if not _is_finite_number(key_time) or key_time < 0:
            return None
        if previous_time is not None and key_time < previous_time:
            return None
        previous_time = key_time

    return key_points


def _canvas_speed_value(
    speed: object,
    is_change_zero_speed: bool,
) -> float | None:
    """校验流速；接近 0 时按需要替换为 ``±0.0001``。"""
    if not _is_finite_number(speed):
        return None

    if is_change_zero_speed:
        if 0.0 <= speed <= 0.0001:
            return 0.0001
        if -0.0001 <= speed < 0.0:
            return -0.0001

    return float(speed)


def addCanvasSpeed(
    chart: dict,
    index: int,
    time: float,
    speed: float = 1.0,
    isDelayCalculate: bool = False,
    isChangeZeroSpeed: bool = True,
    isRealTime: bool = False,
) -> int | None:
    """为指定画布的 ``speedKeyPoints`` 添加一个流速节点。

    ``index`` 为画布索引，负数从末尾计算。``time`` 默认是 tick；
    ``isRealTime=True`` 时按实际秒数换算。时间相同的节点会排在已有
    节点之后。``isChangeZeroSpeed=True`` 时，``speed`` 落在
    ``[0.0, 0.0001]`` 内写为 ``0.0001``，落在 ``[-0.0001, 0.0)`` 内
    写为 ``-0.0001``。

    添加后会重新计算相关的 ``floorPosition``；失败时不修改谱面。
    ``isDelayCalculate=True`` 时跳过全谱重算，新节点的 ``floorPosition``
    写为 ``NaN``，需要随后调用 :func:`refresh`。
    """
    canvas = _find_canvas(chart, index)
    if canvas is None:
        return None

    key_points = _canvas_speed_points(canvas)
    if key_points is None:
        return None

    new_speed = _canvas_speed_value(speed, isChangeZeroSpeed)
    if new_speed is None:
        return None

    target_time = _node_time(chart, time, isRealTime)
    if target_time is None:
        return None

    insert_at = bisect.bisect_right(
        [key_point["time"] for key_point in key_points],
        target_time,
    )
    key_points.insert(
        insert_at,
        {
            "time": target_time,
            "value": new_speed,
            "easeType": 0,
            "floorPosition": math.nan if isDelayCalculate else 0.0,
        },
    )

    if isDelayCalculate:
        return insert_at

    plan = _make_floor_plan(chart)
    if plan is None:
        key_points.pop(insert_at)
        return None
    _apply_floor_plan(plan)
    return insert_at


def setCanvasSpeed(
    chart: dict,
    canvasindex: int,
    speedindex: int = -1,
    time: float | None = None,
    speed: float | None = None,
    isDelayCalculate: bool = False,
    isChangeZeroSpeed: bool = True,
    isRealTime: bool = False,
) -> dict | None:
    """修改画布 ``speedKeyPoints`` 中的一个节点，返回原节点规格 Dict。

    ``speedindex`` 从 0 起，负数从末尾计算。所有修改参数为 ``None``
    时不做修改，直接返回原节点规格 Dict。修改 ``time`` 后会自动按时间重排，
    时间相同的节点排在已有节点之后。指向第 0 个节点时不能修改
    ``time``（允许传入 ``0.0``）。``isChangeZeroSpeed`` 的规则与
    :func:`addCanvasSpeed` 相同。

    修改后会重新计算相关的 ``floorPosition``；失败时不修改谱面。
    ``isDelayCalculate=True`` 时跳过全谱重算，修改后节点的
    ``floorPosition`` 写为 ``NaN``，需要随后调用 :func:`refresh`。
    """
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None

    key_points = _canvas_speed_points(canvas)
    if key_points is None:
        return None

    target_index = _resolve_existing_index(speedindex, len(key_points))
    if target_index is None:
        return None

    old_node = key_points[target_index]
    old_spec = _export_key_point(old_node)
    if old_spec is None:
        return None
    current_time = old_node["time"]

    if time is None:
        target_time = current_time
    else:
        target_time = _node_time(chart, time, isRealTime)
        if target_time is None:
            return None
        if (
            target_index == 0
            and target_time != 0.0
            and target_time != current_time
        ):
            return None

    if speed is None:
        new_speed = old_node.get("value")
    else:
        new_speed = _canvas_speed_value(speed, isChangeZeroSpeed)
        if new_speed is None:
            return None

    if (
        target_time == current_time
        and new_speed == old_node.get("value")
    ):
        return old_spec

    new_node = dict(old_node)
    new_node["time"] = target_time
    new_node["value"] = new_speed
    if isDelayCalculate:
        new_node["floorPosition"] = math.nan

    old_nodes = list(key_points)
    if target_time == current_time:
        key_points[target_index] = new_node
    else:
        remaining = (
            key_points[:target_index] + key_points[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [key_point["time"] for key_point in remaining],
            target_time,
        )
        remaining.insert(insert_at, new_node)
        key_points[:] = remaining

    if isDelayCalculate:
        return old_spec

    plan = _make_floor_plan(chart)
    if plan is None:
        key_points[:] = old_nodes
        return None
    _apply_floor_plan(plan)
    return old_spec


def deleteCanvasSpeed(
    chart: dict,
    canvasindex: int,
    speedindex: int = -1,
    isDelayCalculate: bool = False,
) -> dict | None:
    """删除画布的 ``speedKeyPoints`` 节点，返回原节点规格 Dict。

    ``speedindex`` 从 0 起，负数从末尾计算。指向第 0 个节点时不删除，
    而是重置为 ``new()`` 中的初始节点。删除后会重新计算相关的
    ``floorPosition``；失败时不修改谱面。``isDelayCalculate=True`` 时
    跳过全谱重算，需要随后调用 :func:`refresh`。
    """
    canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None

    key_points = _canvas_speed_points(canvas)
    if key_points is None:
        return None

    target_index = _resolve_existing_index(speedindex, len(key_points))
    if target_index is None:
        return None

    old_node = key_points[target_index]
    old_spec = _export_key_point(old_node)
    if old_spec is None:
        return None
    old_nodes = list(key_points)

    if target_index == 0:
        key_points[0] = {
            "time": 0.0,
            "value": 1.0,
            "easeType": 0,
            "floorPosition": math.nan if isDelayCalculate else 0.0,
        }
    else:
        key_points.pop(target_index)

    if isDelayCalculate:
        return old_spec

    plan = _make_floor_plan(chart)
    if plan is None:
        key_points[:] = old_nodes
        return None
    _apply_floor_plan(plan)
    return old_spec


def _camera_move(chart: object) -> dict | None:
    """取出 ``cameraMove`` 对象。"""
    if not isinstance(chart, dict):
        return None
    camera = chart.get("cameraMove")
    if not isinstance(camera, dict):
        return None
    return camera


def _camera_key_points(camera: dict, key: str) -> list | None:
    """取出并校验摄像机关键点数组，要求 time 非递减。"""
    key_points = camera.get(key)
    if not isinstance(key_points, list):
        return None

    previous_time = None
    for key_point in key_points:
        if not isinstance(key_point, dict):
            return None
        key_time = key_point.get("time")
        if not _is_finite_number(key_time) or key_time < 0:
            return None
        if previous_time is not None and key_time < previous_time:
            return None
        previous_time = key_time

    return key_points


def _add_camera_key_point(
    chart: dict,
    key: str,
    time: object,
    value: object,
    easetype: object,
    is_real_time: bool,
) -> int | None:
    camera = _camera_move(chart)
    if camera is None:
        return None

    key_points = _camera_key_points(camera, key)
    if key_points is None:
        return None

    if not _is_finite_number(value):
        return None

    ease_type = _ease_type(easetype, clamp=True)
    if ease_type is None:
        return None

    target_time = _node_time(chart, time, is_real_time)
    if target_time is None:
        return None

    insert_at = bisect.bisect_right(
        [key_point["time"] for key_point in key_points],
        target_time,
    )
    key_points.insert(
        insert_at,
        {
            "time": target_time,
            "value": float(value),
            "easeType": ease_type,
            "floorPosition": 0.0,
        },
    )
    return insert_at


def _set_camera_key_point(
    chart: dict,
    key: str,
    index: object,
    time: object,
    value: object,
    easetype: object,
    is_real_time: bool,
) -> dict | None:
    camera = _camera_move(chart)
    if camera is None:
        return None

    key_points = _camera_key_points(camera, key)
    if key_points is None:
        return None

    target_index = _resolve_existing_index(index, len(key_points))
    if target_index is None:
        return None

    old_node = key_points[target_index]
    current_time = old_node["time"]

    if time is None:
        target_time = current_time
    else:
        target_time = _node_time(chart, time, is_real_time)
        if target_time is None:
            return None
        if (
            target_index == 0
            and target_time != 0.0
            and target_time != current_time
        ):
            return None

    if value is None:
        new_value = old_node.get("value")
    else:
        if not _is_finite_number(value):
            return None
        new_value = float(value)

    if easetype is None:
        new_ease = old_node.get("easeType")
    else:
        new_ease = _ease_type(easetype, clamp=True)
        if new_ease is None:
            return None

    if (
        target_time == current_time
        and new_value == old_node.get("value")
        and new_ease == old_node.get("easeType")
    ):
        return old_node

    new_node = dict(old_node)
    new_node["time"] = target_time
    new_node["value"] = new_value
    new_node["easeType"] = new_ease

    if target_time == current_time:
        key_points[target_index] = new_node
    else:
        remaining = (
            key_points[:target_index] + key_points[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [key_point["time"] for key_point in remaining],
            target_time,
        )
        remaining.insert(insert_at, new_node)
        key_points[:] = remaining

    return old_node


def _delete_camera_key_point(
    chart: dict,
    key: str,
    index: object,
    reset_value: float,
) -> dict | None:
    camera = _camera_move(chart)
    if camera is None:
        return None

    key_points = _camera_key_points(camera, key)
    if key_points is None:
        return None

    target_index = _resolve_existing_index(index, len(key_points))
    if target_index is None:
        return None

    old_node = key_points[target_index]
    if target_index == 0:
        key_points[0] = {
            "time": 0.0,
            "value": reset_value,
            "easeType": 0,
            "floorPosition": 0.0,
        }
    else:
        key_points.pop(target_index)

    return old_node


def addCameraPosition(
    chart: dict,
    time: float,
    position: float = 0.0,
    easetype: int = 0,
    isRealTime: bool = False,
) -> int | None:
    """为 ``cameraMove.xPositionKeyPoints`` 添加节点。

    ``time`` 默认是 tick；``isRealTime=True`` 时按实际秒数换算。
    时间相同的节点排在已有节点之后。``easetype`` 夹取到 0-18。
    """
    return _add_camera_key_point(
        chart,
        "xPositionKeyPoints",
        time,
        position,
        easetype,
        isRealTime,
    )


def setCameraPosition(
    chart: dict,
    index: int = -1,
    time: float | None = None,
    position: float | None = None,
    easetype: int | None = None,
    isRealTime: bool = False,
) -> dict | None:
    """修改 ``cameraMove.xPositionKeyPoints`` 节点，返回原节点规格 Dict。

    修改 ``time`` 后自动按时间重排；时间相同的节点排在已有节点之后。
    指向第 0 个节点时不能修改 ``time``（允许传入 ``0.0``）。
    ``easetype`` 夹取到 0-18。
    """
    if position is not None and not _is_finite_number(position):
        return None
    old_node = _set_camera_key_point(
        chart,
        "xPositionKeyPoints",
        index,
        time,
        position,
        easetype,
        isRealTime,
    )
    return None if old_node is None else _export_key_point(old_node)


def deleteCameraPosition(
    chart: dict,
    index: int = -1,
) -> dict | None:
    """删除 ``cameraMove.xPositionKeyPoints`` 节点，返回原节点规格 Dict。

    指向第 0 个节点时不删除，而是重置为 ``new()`` 中的初始节点。
    """
    old_node = _delete_camera_key_point(
        chart,
        "xPositionKeyPoints",
        index,
        0.0,
    )
    return None if old_node is None else _export_key_point(old_node)


def addCameraScale(
    chart: dict,
    time: float,
    scale: float = 1.0,
    easetype: int = 0,
    isRealTime: bool = False,
) -> int | None:
    """为 ``cameraMove.scaleKeyPoints`` 添加节点。

    ``scale`` 必须大于 ``0.0``，但不限制在 0.1-10.0 内。``time`` 默认
    是 tick；``isRealTime=True`` 时按实际秒数换算。时间相同的节点排在
    已有节点之后。``easetype`` 夹取到 0-18。
    """
    if not _is_finite_number(scale) or scale <= 0.0:
        return None
    return _add_camera_key_point(
        chart,
        "scaleKeyPoints",
        time,
        scale,
        easetype,
        isRealTime,
    )


def setCameraScale(
    chart: dict,
    index: int = -1,
    time: float | None = None,
    scale: float | None = None,
    easetype: int | None = None,
    isRealTime: bool = False,
) -> dict | None:
    """修改 ``cameraMove.scaleKeyPoints`` 节点，返回原节点规格 Dict。

    ``scale`` 必须大于 ``0.0``，但不限制在 0.1-10.0 内。修改 ``time``
    后自动按时间重排；时间相同的节点排在已有节点之后。指向第 0 个
    节点时不能修改 ``time``（允许传入 ``0.0``）。``easetype`` 夹取到
    0-18。
    """
    if scale is not None and (
        not _is_finite_number(scale) or scale <= 0.0
    ):
        return None
    old_node = _set_camera_key_point(
        chart,
        "scaleKeyPoints",
        index,
        time,
        scale,
        easetype,
        isRealTime,
    )
    return None if old_node is None else _export_key_point(old_node)


def deleteCameraScale(
    chart: dict,
    index: int = -1,
) -> dict | None:
    """删除 ``cameraMove.scaleKeyPoints`` 节点，返回原节点规格 Dict。

    指向第 0 个节点时不删除，而是重置为 ``new()`` 中的初始节点。
    """
    old_node = _delete_camera_key_point(
        chart,
        "scaleKeyPoints",
        index,
        1.0,
    )
    return None if old_node is None else _export_key_point(old_node)


def _canvas_floor_position_at(
    chart: dict,
    canvas: dict,
    tick: float,
) -> float | None:
    """按画布流速节点计算指定 tick 处的 floorPosition。"""
    timeline = _bpm_seconds(chart)
    if timeline is None:
        return None
    base_bpm, times, values, seconds = timeline

    key_points = _canvas_speed_points(canvas)
    if key_points is None or not key_points:
        return None

    last_key_point = None
    for key_point in key_points:
        key_value = key_point.get("value")
        key_floor_position = key_point.get("floorPosition")
        if (
            not _is_finite_number(key_value)
            or not _is_finite_number(key_floor_position)
        ):
            return None
        if key_point["time"] <= tick:
            last_key_point = key_point

    if last_key_point is None:
        return None

    return float(
        last_key_point["floorPosition"]
        + last_key_point["value"]
        * (
            _seconds_at(tick, base_bpm, times, values, seconds)
            - _seconds_at(
                last_key_point["time"],
                base_bpm,
                times,
                values,
                seconds,
            )
        )
    )


def _build_line_point(
    chart: dict,
    time: float,
    x_position: float,
    canvas: dict,
    ease_type: int,
    color: dict,
    calculate_floor: bool = True,
) -> dict | None:
    """组装线节点并计算 ``floorPosition``。"""
    if calculate_floor:
        floor_position = _canvas_floor_position_at(
            chart,
            canvas,
            float(time),
        )
        if floor_position is None:
            return None
    else:
        floor_position = math.nan

    return {
        "time": float(time),
        "xPosition": float(x_position),
        "color": color,
        "easeType": ease_type,
        "canvasIndex": canvas["index"],
        "floorPosition": floor_position,
    }


def _line_point_spec(
    value: dict,
    chart: dict | None = None,
) -> dict | None:
    """校验并规范化线节点输入，不计算 ``floorPosition``。"""
    if not isinstance(value, dict):
        return None

    target_time = _node_time(
        chart,
        value.get("time"),
        value.get("isRealTime", False),
    )
    if target_time is None:
        return None

    x_position = value.get("xPosition")
    if not _is_finite_number(x_position):
        return None

    canvas_index = value.get("canvasIndex")
    if not _is_int(canvas_index):
        return None

    ease_type = _ease_type(value.get("easeType"), clamp=True)
    if ease_type is None:
        return None

    color = _parse_color(value.get("color"))
    if color is None:
        return None

    return {
        "time": target_time,
        "xPosition": float(x_position),
        "color": color,
        "easeType": ease_type,
        "canvasIndex": canvas_index,
    }


def createLinePoint(
    time: float,
    xPosition: float,
    index: int,
    easetype: int,
    color: str | list,
    isRealTime: bool = False,
    chart: dict | None = None,
) -> dict | None:
    """创建一个线节点规格 Dict，不修改谱面，也不计算 ``floorPosition``。

    ``easetype`` 夹取到 0-18；``color`` 支持 HEX / RGB(A) 列表 / RGBA
    Dict。``isRealTime=True`` 时需要提供 ``chart``，用于把实际秒数换算
    为 tick。返回的规格可传给 :func:`addLine`；单节点追加使用
    :func:`addLinePoint`，由后者计算 ``floorPosition``。失败返回 ``None``。
    """
    spec = _line_point_spec(
        {
            "time": time,
            "xPosition": xPosition,
            "canvasIndex": index,
            "easeType": easetype,
            "color": color,
            "isRealTime": isRealTime,
        },
        chart,
    )
    return None if spec is None else _export_line_point(spec)


def _make_color_point(
    time: float,
    startcolor: str | list,
    endcolor: str | list | None = None,
) -> dict | None:
    """组装判定环 / 线色覆盖节点。"""
    if not _is_finite_number(time) or time < 0:
        return None

    start_color = _parse_color(startcolor)
    if start_color is None:
        return None

    if endcolor is None:
        end_color = dict(start_color)
    else:
        end_color = _parse_color(endcolor)
        if end_color is None:
            return None

    return {
        "startColor": start_color,
        "endColor": end_color,
        "time": float(time),
    }


def _create_color_point(
    time: float,
    startcolor: str | list,
    endcolor: str | list | None,
    is_real_time: bool,
    chart: dict | None,
) -> dict | None:
    """按 tick / 实际秒数转换后组装颜色节点。"""
    if is_real_time:
        if not isinstance(chart, dict):
            return None
        target_time = _node_time(chart, time, True)
        if target_time is None:
            return None
    else:
        if not _is_finite_number(time) or time < 0:
            return None
        target_time = float(time)

    return _make_color_point(target_time, startcolor, endcolor)


def createRingPoint(
    time: float,
    startcolor: str | list,
    endcolor: str | list | None = None,
    isRealTime: bool = False,
    chart: dict | None = None,
) -> dict | None:
    """创建一个判定环颜色节点，不修改谱面。

    ``endcolor`` 为 ``None`` 时与 ``startcolor`` 相同。``chart`` 仅在
    ``isRealTime=True`` 时使用，用于把实际秒数换算为 tick；此时必须
    提供有效谱面。失败返回 ``None``。
    """
    node = _create_color_point(
        time,
        startcolor,
        endcolor,
        isRealTime,
        chart,
    )
    return None if node is None else _export_color_change(node)


def createLineColor(
    time: float,
    startcolor: str | list,
    endcolor: str | list | None = None,
    isRealTime: bool = False,
    chart: dict | None = None,
) -> dict | None:
    """创建一个线色覆盖节点，不修改谱面。

    ``endcolor`` 为 ``None`` 时与 ``startcolor`` 相同。``chart`` 仅在
    ``isRealTime=True`` 时使用，用于把实际秒数换算为 tick；此时必须
    提供有效谱面。节点结构与判定环颜色节点相同。失败返回 ``None``。
    """
    node = _create_color_point(
        time,
        startcolor,
        endcolor,
        isRealTime,
        chart,
    )
    return None if node is None else _export_color_change(node)


def _validate_line_point(
    point: object,
    require_floor: bool = True,
) -> bool:
    """检查一个线节点是否符合标准格式。"""
    if not isinstance(point, dict):
        return False

    point_time = point.get("time")
    if not _is_finite_number(point_time) or point_time < 0:
        return False
    if not _is_finite_number(point.get("xPosition")):
        return False
    if not _is_int(point.get("easeType")):
        return False
    canvas_index = point.get("canvasIndex")
    if not _is_int(canvas_index) or canvas_index < 0:
        return False
    if require_floor and not _is_finite_number(point.get("floorPosition")):
        return False

    color = point.get("color")
    if not isinstance(color, dict):
        return False
    return all(
        _is_int(color.get(channel))
        for channel in ("r", "g", "b", "a")
    )


def _validate_color_point(point: object) -> bool:
    """检查一个判定环颜色节点是否符合标准格式。"""
    if not isinstance(point, dict) or not point:
        return False

    point_time = point.get("time")
    if not _is_finite_number(point_time) or point_time < 0:
        return False

    for key in ("startColor", "endColor"):
        color = point.get(key)
        if not isinstance(color, dict):
            return False
        if not all(
            _is_int(color.get(channel))
            for channel in ("r", "g", "b", "a")
        ):
            return False

    return True


def _normalize_line_point(
    chart: dict,
    value: object,
    calculate_floor: bool = True,
) -> dict | None:
    """把线节点输入归一化，并按需计算 ``floorPosition``。"""
    if not isinstance(value, dict):
        return None
    if (
        calculate_floor
        and "floorPosition" in value
        and not _is_finite_number(value.get("floorPosition"))
    ):
        return None

    spec = _line_point_spec(value, chart)
    if spec is None:
        return None

    canvas = _find_canvas(chart, spec["canvasIndex"])
    if canvas is None:
        return None

    return _build_line_point(
        chart,
        spec["time"],
        spec["xPosition"],
        canvas,
        spec["easeType"],
        spec["color"],
        calculate_floor,
    )


def _normalize_color_node(chart: dict, value: object) -> dict | None:
    """把完整颜色节点或规格 Dict 归一化为完整颜色节点。"""
    if not isinstance(value, dict):
        return None
    return _create_color_point(
        value.get("time"),
        value.get("startColor"),
        value.get("endColor"),
        value.get("isRealTime", False),
        chart,
    )


def addLine(
    chart: dict,
    linepointslist: list,
    ringpointslist: list | dict,
    index: int | None = None,
    isDelayCalculate: bool = False,
    *,
    notes: list | None = None,
    linecolors: list | None = None,
) -> int | None:
    """在 ``lines`` 的指定位置插入一条引导线。

    ``linepointslist`` 至少需要两个节点；``ringpointslist`` 可以是一个
    判定环颜色节点（dict），也可以是节点列表，但至少要有一个节点。
    ``notes`` / ``linecolors`` 可选，分别写入新线的 ``notes`` 与
    ``lineColor``。

    四类节点都支持两种格式：

    - 完整节点：符合 JSON 格式，可包含派生字段；``floorPosition`` 等
      派生值不会直接使用，而是重新计算；
    - 规格 Dict：省略派生字段，由本函数计算。

    所有节点按 ``time`` 稳定排序后写入。``index=None`` 时追加到末尾；
    负数从末尾计算。新线的 ``floorPosition`` 需要重新计算，因此默认要求
    谱面在 ``time=0.0`` 处有 BPM 节点。``isDelayCalculate=True`` 时跳过
    高度计算，新节点的 ``floorPosition`` 写为 ``NaN``，需要随后调用
    :func:`refresh`。成功返回新线索引；任一项非法时返回 ``None``，且
    不修改谱面。
    """
    if not isinstance(chart, dict):
        return None
    if not isinstance(linepointslist, list) or len(linepointslist) < 2:
        return None

    if isinstance(ringpointslist, dict):
        ring_values = [ringpointslist]
    elif isinstance(ringpointslist, list):
        ring_values = ringpointslist
    else:
        return None
    if not ring_values:
        return None

    if notes is None:
        note_values = []
    elif isinstance(notes, list):
        note_values = notes
    else:
        return None

    if linecolors is None:
        color_values = []
    elif isinstance(linecolors, list):
        color_values = linecolors
    else:
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    position = _resolve_insert_position(index, len(lines))
    if position is None:
        return None

    line_points = []
    for value in linepointslist:
        point = _normalize_line_point(
            chart,
            value,
            calculate_floor=not isDelayCalculate,
        )
        if point is None:
            return None
        line_points.append(point)
    line_points = sorted(
        line_points,
        key=lambda point: point["time"],
    )

    ring_points = []
    for value in ring_values:
        point = _normalize_color_node(chart, value)
        if point is None:
            return None
        ring_points.append(point)
    ring_points = sorted(
        ring_points,
        key=lambda point: point["time"],
    )

    note_nodes = []
    for value in note_values:
        note = _normalize_note(
            chart,
            line_points,
            value,
            calculate_floor=not isDelayCalculate,
        )
        if note is None:
            return None
        note_nodes.append(note)
    note_nodes = sorted(
        note_nodes,
        key=lambda note: note["time"],
    )

    color_nodes = []
    for value in color_values:
        point = _normalize_color_node(chart, value)
        if point is None:
            return None
        color_nodes.append(point)
    color_nodes = sorted(
        color_nodes,
        key=lambda point: point["time"],
    )

    lines.insert(
        position,
        {
            "linePoints": line_points,
            "notes": note_nodes,
            "judgeRingColor": ring_points,
            "lineColor": color_nodes,
        },
    )
    return position


def deleteLine(
    chart: dict,
    index: int = -1,
) -> dict | None:
    """删除指定索引的引导线，成功返回被删除引导线的规格 Dict。

    ``index`` 从 0 起，负数从末尾计算。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    target_index = _resolve_existing_index(index, len(lines))
    if target_index is None:
        return None

    line_spec = _export_line(lines[target_index])
    if line_spec is None:
        return None
    lines.pop(target_index)
    return line_spec


def _validate_line_points(points: object) -> list | None:
    """校验线节点列表，要求 time 非递减。"""
    if not isinstance(points, list):
        return None

    previous_time = None
    for point in points:
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        if not _is_finite_number(point_time) or point_time < 0:
            return None
        if previous_time is not None and point_time < previous_time:
            return None
        previous_time = point_time

    return points


def _line_points(line: dict) -> list | None:
    """取出并校验 linePoints，要求 time 非递减。"""
    return _validate_line_points(line.get("linePoints"))


def addLinePoint(
    chart: dict,
    time: float,
    xPosition: float,
    canvasindex: int,
    easetype: int,
    color: str | list,
    lineindex: int = -1,
    isDelayCalculate: bool = False,
    isRealTime: bool = False,
    isAbsolutePosition: bool = False,
) -> int | None:
    """向指定引导线添加一个节点。

    ``lineindex`` 从 0 起，负数从末尾计算。节点按 ``time`` 插入；
    时间相同时放在已有节点之后。``floorPosition`` 自动计算。
    ``isRealTime=True`` 时 ``time`` 是实际秒数。``isAbsolutePosition=True``
    时 ``xPosition`` 是绝对 x 坐标，会减去目标时刻画布的中线 x 后存储为
    相对坐标。``isDelayCalculate=True`` 时跳过高度计算，新节点
    ``floorPosition`` 写为 ``NaN``，需要随后调用 :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_points(line)
    if points is None:
        return None

    target_time = _node_time(chart, time, isRealTime)
    if target_time is None:
        return None

    target_x = xPosition
    if isAbsolutePosition:
        if not _is_finite_number(target_x):
            return None
        canvas = _find_canvas(chart, canvasindex)
        if canvas is None:
            return None
        canvas_x = _canvas_x_at(canvas, target_time)
        if canvas_x is None:
            return None
        target_x = float(target_x) - canvas_x

    point = _normalize_line_point(
        chart,
        {
            "time": target_time,
            "xPosition": target_x,
            "canvasIndex": canvasindex,
            "easeType": easetype,
            "color": color,
        },
        calculate_floor=not isDelayCalculate,
    )
    if point is None:
        return None

    insert_at = bisect.bisect_right(
        [existing["time"] for existing in points],
        point["time"],
    )
    points.insert(insert_at, point)

    if isDelayCalculate:
        return insert_at

    plan = _make_floor_plan(chart)
    if plan is None:
        points.pop(insert_at)
        return None
    _apply_floor_plan(plan)
    return insert_at


def setLinePoint(
    chart: dict,
    lineindex: int = -1,
    pointindex: int = -1,
    time: float | None = None,
    xPosition: float | None = None,
    canvasindex: int | None = None,
    easetype: int | None = None,
    color: str | list | None = None,
    isDelayCalculate: bool = False,
    isRealTime: bool = False,
) -> dict | None:
    """修改引导线中的一个节点，返回原节点规格 Dict。

    ``lineindex`` / ``pointindex`` 从 0 起，负数从末尾计算。修改
    ``time`` 后自动按时间重排；时间相同时放在已有节点之后。
    ``floorPosition`` 自动重算。所有修改参数为 ``None`` 时直接返回原
    节点规格 Dict，不修改谱面。``isDelayCalculate=True`` 时跳过高度计算，
    修改后节点的 ``floorPosition`` 写为 ``NaN``，需要随后调用
    :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_points(line)
    if points is None:
        return None

    target_index = _resolve_existing_index(pointindex, len(points))
    if target_index is None:
        return None

    old_node = points[target_index]
    if not _validate_line_point(
        old_node,
        require_floor=not isDelayCalculate,
    ):
        return None
    old_spec = _export_line_point(old_node)
    if old_spec is None:
        return None

    old_time = old_node["time"]
    old_x = old_node["xPosition"]
    old_canvas = old_node["canvasIndex"]
    old_ease = old_node["easeType"]
    old_color = old_node["color"]

    if time is None:
        target_time = old_time
    else:
        target_time = _node_time(chart, time, isRealTime)
        if target_time is None:
            return None

    if xPosition is None:
        new_x = old_x
    else:
        if not _is_finite_number(xPosition):
            return None
        new_x = float(xPosition)

    if canvasindex is None:
        canvas = _find_canvas(chart, old_canvas)
    else:
        canvas = _find_canvas(chart, canvasindex)
    if canvas is None:
        return None
    new_canvas = canvas["index"]

    if easetype is None:
        new_ease = old_ease
    else:
        new_ease = _ease_type(easetype, clamp=True)
        if new_ease is None:
            return None

    if color is None:
        new_color = dict(old_color)
    else:
        new_color = _parse_color(color)
        if new_color is None:
            return None

    if (
        target_time == old_time
        and new_x == old_x
        and new_canvas == old_canvas
        and new_ease == old_ease
        and new_color == old_color
    ):
        return old_spec

    new_node = _build_line_point(
        chart,
        target_time,
        new_x,
        canvas,
        new_ease,
        new_color,
        calculate_floor=not isDelayCalculate,
    )
    if new_node is None:
        return None

    old_points = list(points)
    if target_time == old_time:
        points[target_index] = new_node
    else:
        remaining = (
            points[:target_index] + points[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [point["time"] for point in remaining],
            target_time,
        )
        remaining.insert(insert_at, new_node)
        points[:] = remaining

    if isDelayCalculate:
        return old_spec

    plan = _make_floor_plan(chart)
    if plan is None:
        points[:] = old_points
        return None
    _apply_floor_plan(plan)

    return old_spec


def deleteLinePoint(
    chart: dict,
    lineindex: int = -1,
    pointindex: int = -1,
) -> dict | None:
    """删除引导线中的一个节点，返回原节点规格 Dict。

    ``lineindex`` / ``pointindex`` 从 0 起，负数从末尾计算。
    当该线只有两个或更少节点时不能删除，返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_points(line)
    if points is None:
        return None
    if len(points) <= 2:
        return None

    target_index = _resolve_existing_index(pointindex, len(points))
    if target_index is None:
        return None

    deleted_spec = _export_line_point(points[target_index])
    if deleted_spec is None:
        return None
    old_points = list(points)
    points.pop(target_index)

    plan = _make_floor_plan(chart)
    if plan is None:
        points[:] = old_points
        return None
    _apply_floor_plan(plan)

    return deleted_spec


def _ring_points(line: dict) -> list | None:
    """取出并校验 judgeRingColor，要求 time 非递减。"""
    points = line.get("judgeRingColor")
    if not isinstance(points, list):
        return None

    previous_time = None
    for point in points:
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        if not _is_finite_number(point_time) or point_time < 0:
            return None
        if previous_time is not None and point_time < previous_time:
            return None
        previous_time = point_time

    return points


def addRingPoint(
    chart: dict,
    index: int,
    time: float,
    startcolor: str | list,
    endcolor: str | list | None = None,
    isRealTime: bool = False,
) -> int | None:
    """向指定引导线添加判定环颜色节点。

    ``index`` 为线索引，0 起，负数从末尾计算。节点按 ``time`` 插入；
    时间相同时放在已有节点之后。``endcolor=None`` 时与 ``startcolor``
    相同。``isRealTime=True`` 时 ``time`` 是实际秒数。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(index, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _ring_points(line)
    if points is None:
        return None

    target_time = _node_time(chart, time, isRealTime)
    if target_time is None:
        return None

    node = _make_color_point(
        target_time,
        startcolor,
        endcolor,
    )
    if node is None:
        return None

    insert_at = bisect.bisect_right(
        [point["time"] for point in points],
        node["time"],
    )
    points.insert(insert_at, node)
    return insert_at


def setRingPoint(
    chart: dict,
    lineindex: int = -1,
    ringindex: int = -1,
    time: float | None = None,
    startcolor: str | list | None = None,
    endcolor: str | list | None = None,
    isRealTime: bool = False,
) -> dict | None:
    """修改判定环颜色节点，返回原节点规格 Dict。

    ``lineindex`` / ``ringindex`` 从 0 起，负数从末尾计算。修改 ``time``
    后自动按时间重排；时间相同时放在已有节点之后。所有修改参数为
    ``None`` 时直接返回原节点规格 Dict，不修改谱面。

    注意：这里的 ``endcolor=None`` 表示**不修改**，而不是与起始颜色相同。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _ring_points(line)
    if points is None:
        return None

    target_index = _resolve_existing_index(ringindex, len(points))
    if target_index is None:
        return None

    old_node = points[target_index]
    old_spec = _export_color_change(old_node)
    if old_spec is None:
        return None

    if time is None and startcolor is None and endcolor is None:
        return old_spec

    if not _validate_color_point(old_node):
        return None

    old_time = old_node["time"]
    old_start = old_node["startColor"]
    old_end = old_node["endColor"]

    if time is None:
        target_time = old_time
    else:
        target_time = _node_time(chart, time, isRealTime)
        if target_time is None:
            return None

    if startcolor is None:
        new_start = dict(old_start)
    else:
        new_start = _parse_color(startcolor)
        if new_start is None:
            return None

    if endcolor is None:
        new_end = dict(old_end)
    else:
        new_end = _parse_color(endcolor)
        if new_end is None:
            return None

    if (
        target_time == old_time
        and new_start == old_start
        and new_end == old_end
    ):
        return old_spec

    new_node = {
        "startColor": new_start,
        "endColor": new_end,
        "time": target_time,
    }

    if target_time == old_time:
        points[target_index] = new_node
    else:
        remaining = (
            points[:target_index] + points[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [point["time"] for point in remaining],
            target_time,
        )
        remaining.insert(insert_at, new_node)
        points[:] = remaining

    return old_spec


def deleteRingPoint(
    chart: dict,
    lineindex: int = -1,
    ringindex: int = -1,
) -> dict | None:
    """删除判定环颜色节点，返回原节点规格 Dict。

    ``lineindex`` / ``ringindex`` 从 0 起，负数从末尾计算。
    当该线只剩一个判定环节点时不能删除，返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _ring_points(line)
    if points is None:
        return None
    if len(points) <= 1:
        return None

    target_index = _resolve_existing_index(ringindex, len(points))
    if target_index is None:
        return None

    deleted_spec = _export_color_change(points[target_index])
    if deleted_spec is None:
        return None
    points.pop(target_index)
    return deleted_spec


def _line_colors(line: dict) -> list | None:
    """取出并校验 lineColor，要求 time 非递减。"""
    points = line.get("lineColor")
    if not isinstance(points, list):
        return None

    previous_time = None
    for point in points:
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        if not _is_finite_number(point_time) or point_time < 0:
            return None
        if previous_time is not None and point_time < previous_time:
            return None
        previous_time = point_time

    return points


def addLineColor(
    chart: dict,
    index: int,
    time: float,
    startcolor: str | list,
    endcolor: str | list | None = None,
    isRealTime: bool = False,
) -> int | None:
    """向指定引导线添加线色覆盖节点。

    ``index`` 为线索引，0 起，负数从末尾计算。节点按 ``time`` 插入；
    时间相同时放在已有节点之后。``endcolor=None`` 时与 ``startcolor``
    相同。``isRealTime=True`` 时 ``time`` 是实际秒数。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(index, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_colors(line)
    if points is None:
        return None

    target_time = _node_time(chart, time, isRealTime)
    if target_time is None:
        return None

    node = _make_color_point(target_time, startcolor, endcolor)
    if node is None:
        return None

    insert_at = bisect.bisect_right(
        [point["time"] for point in points],
        node["time"],
    )
    points.insert(insert_at, node)
    return insert_at


def setLineColor(
    chart: dict,
    lineindex: int = -1,
    colorindex: int = -1,
    time: float | None = None,
    startcolor: str | list | None = None,
    endcolor: str | list | None = None,
    isRealTime: bool = False,
) -> dict | None:
    """修改线色覆盖节点，返回原节点规格 Dict。

    ``lineindex`` / ``colorindex`` 从 0 起，负数从末尾计算。修改
    ``time`` 后自动按时间重排；时间相同时放在已有节点之后。所有修改
    参数为 ``None`` 时直接返回原节点规格 Dict。

    注意：这里的 ``endcolor=None`` 表示**不修改**，而不是与起始颜色相同。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_colors(line)
    if points is None:
        return None

    target_index = _resolve_existing_index(colorindex, len(points))
    if target_index is None:
        return None

    old_node = points[target_index]
    old_spec = _export_color_change(old_node)
    if old_spec is None:
        return None

    if time is None and startcolor is None and endcolor is None:
        return old_spec

    if not _validate_color_point(old_node):
        return None

    old_time = old_node["time"]
    old_start = old_node["startColor"]
    old_end = old_node["endColor"]

    if time is None:
        target_time = old_time
    else:
        target_time = _node_time(chart, time, isRealTime)
        if target_time is None:
            return None

    if startcolor is None:
        new_start = dict(old_start)
    else:
        new_start = _parse_color(startcolor)
        if new_start is None:
            return None

    if endcolor is None:
        new_end = dict(old_end)
    else:
        new_end = _parse_color(endcolor)
        if new_end is None:
            return None

    if (
        target_time == old_time
        and new_start == old_start
        and new_end == old_end
    ):
        return old_spec

    new_node = {
        "startColor": new_start,
        "endColor": new_end,
        "time": target_time,
    }

    if target_time == old_time:
        points[target_index] = new_node
    else:
        remaining = (
            points[:target_index] + points[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [point["time"] for point in remaining],
            target_time,
        )
        remaining.insert(insert_at, new_node)
        points[:] = remaining

    return old_spec


def deleteLineColor(
    chart: dict,
    lineindex: int = -1,
    colorindex: int = -1,
) -> dict | None:
    """删除线色覆盖节点，返回原节点规格 Dict。

    ``lineindex`` / ``colorindex`` 从 0 起，负数从末尾计算。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_colors(line)
    if points is None:
        return None

    target_index = _resolve_existing_index(colorindex, len(points))
    if target_index is None:
        return None

    deleted_spec = _export_color_change(points[target_index])
    if deleted_spec is None:
        return None
    points.pop(target_index)
    return deleted_spec


def _notes(line: dict) -> list | None:
    """取出并校验 notes，要求 time 非递减。"""
    notes = line.get("notes")
    if not isinstance(notes, list):
        return None

    previous_time = None
    for note in notes:
        if not isinstance(note, dict):
            return None
        note_time = note.get("time")
        if not _is_finite_number(note_time) or note_time < 0:
            return None
        if previous_time is not None and note_time < previous_time:
            return None
        previous_time = note_time

    return notes


def _parse_note_type(value: object) -> int | None:
    """把 0/1/2 或 tap/drag/hold 解析为 Note 类型。"""
    if _is_int(value):
        return value if value in (0, 1, 2) else None
    if isinstance(value, str):
        return {"tap": 0, "drag": 1, "hold": 2}.get(value.lower())
    return None


def _validate_note(
    note: object,
    require_floor: bool = True,
) -> bool:
    """检查一个 Note 是否符合标准格式。"""
    if not isinstance(note, dict):
        return False

    note_type = note.get("type")
    if not _is_int(note_type) or note_type not in (0, 1, 2):
        return False

    note_time = note.get("time")
    if not _is_finite_number(note_time) or note_time < 0:
        return False
    if require_floor and not _is_finite_number(note.get("floorPosition")):
        return False

    extra = note.get("otherInformations")
    if note_type == 2:
        if not isinstance(extra, list) or len(extra) != 3:
            return False
        tail_time, tail_canvas, tail_floor = extra
        if not _is_finite_number(tail_time) or tail_time < 0:
            return False
        if not _is_canvas_reference(tail_canvas):
            return False
        if require_floor and not _is_finite_number(tail_floor):
            return False
    elif extra is not None:
        if not isinstance(extra, list) or len(extra) not in (0, 3):
            return False
        if len(extra) == 3 and not all(
            _is_number(item) for item in extra
        ):
            return False

    return True


def _line_note_position(
    chart: dict,
    line_points: list,
    tick: float,
    is_head: bool,
    calculate_floor: bool = True,
) -> tuple[int, float] | None:
    """按头部/尾部规则确定画布并计算 floorPosition。"""
    times = [point["time"] for point in line_points]

    if is_head:
        # 头部：正好在节点时间上时使用右侧节点
        position = bisect.bisect_right(times, tick) - 1
    else:
        # 尾部：正好在节点时间上时使用左侧节点（前一段）
        position = bisect.bisect_left(times, tick) - 1

    if not 0 <= position < len(line_points):
        return None

    canvas_index = line_points[position].get("canvasIndex")
    if not _is_int(canvas_index) or canvas_index < 0:
        return None

    canvas = _find_canvas(chart, canvas_index)
    if canvas is None:
        return None

    if not calculate_floor:
        return canvas_index, math.nan

    floor_position = _canvas_floor_position_at(chart, canvas, tick)
    if floor_position is None:
        return None

    return canvas_index, floor_position


def _build_note(
    chart: dict,
    points: list,
    head_time: float,
    note_type: int,
    tail_time: float | None = None,
    calculate_floor: bool = True,
) -> dict | None:
    """按已换算的 tick 时间构造 Note，不修改谱面。"""
    if note_type not in (0, 1, 2):
        return None
    if not isinstance(points, list) or len(points) < 2:
        return None

    first_time = points[0]["time"]
    last_time = points[-1]["time"]
    if head_time < first_time or head_time > last_time:
        return None

    head = _line_note_position(
        chart,
        points,
        head_time,
        True,
        calculate_floor,
    )
    if head is None:
        return None
    _, head_floor = head

    note = {
        "type": note_type,
        "time": head_time,
        "floorPosition": head_floor,
        "otherInformations": [],
    }

    if note_type == 2:
        if tail_time is None:
            return None
        if tail_time <= head_time or tail_time > last_time:
            return None
        tail = _line_note_position(
            chart,
            points,
            tail_time,
            False,
            calculate_floor,
        )
        if tail is None:
            return None
        tail_canvas, tail_floor = tail
        note["otherInformations"] = [
            tail_time,
            tail_canvas,
            tail_floor,
        ]

    return note


def _note_spec(
    value: dict,
    chart: dict | None = None,
) -> dict | None:
    """校验并规范化 Note 输入，不计算画布与 ``floorPosition``。"""
    if not isinstance(value, dict):
        return None

    note_type = _parse_note_type(value.get("type"))
    if note_type is None:
        return None

    head_time = _node_time(
        chart,
        value.get("time"),
        value.get("isRealTime", False),
    )
    if head_time is None:
        return None

    spec = {
        "type": note_type,
        "time": head_time,
    }

    if note_type == 2:
        tail_time = _node_time(
            chart,
            value.get("endtime"),
            value.get("isRealEndTime", False),
        )
        if tail_time is None or tail_time <= head_time:
            return None
        spec["endtime"] = tail_time

    return spec


def _normalize_note(
    chart: dict,
    line_points: list,
    value: object,
    calculate_floor: bool = True,
) -> dict | None:
    """把 Note 输入归一化，并按需计算派生字段。"""
    if not isinstance(value, dict):
        return None
    if not isinstance(line_points, list) or len(line_points) < 2:
        return None

    preserve_extra = None
    if "floorPosition" in value:
        if not _validate_note(
            value,
            require_floor=calculate_floor,
        ):
            return None
        note_type = value["type"]
        spec_value = {
            "type": note_type,
            "time": float(value["time"]),
        }
        if note_type == 2:
            extra = value["otherInformations"]
            spec_value["endtime"] = float(extra[0])
        elif isinstance(value.get("otherInformations"), list):
            preserve_extra = list(value["otherInformations"])
    else:
        spec_value = value

    spec = _note_spec(spec_value, chart)
    if spec is None:
        return None

    note = _build_note(
        chart,
        line_points,
        spec["time"],
        spec["type"],
        spec.get("endtime"),
        calculate_floor,
    )
    if note is None:
        return None
    if preserve_extra is not None:
        if not calculate_floor and len(preserve_extra) == 3:
            # Tap/Drag 的三元素 otherInformations 只是占位，第三个值不是
            # 需要 refresh() 修复的 Note 头部/尾部高度。
            preserve_extra[2] = 0.0
        note["otherInformations"] = preserve_extra
    return note


def createNote(
    time: float,
    type: int | str,
    endtime: float = 0.0,
    isRealTime: bool = False,
    isRealEndTime: bool = False,
    chart: dict | None = None,
) -> dict | None:
    """创建一个 Note 规格 Dict，不修改谱面，也不计算 ``floorPosition``。

    ``type`` 支持 ``0/"tap"``、``1/"drag"``、``2/"hold"``，不区分大小写。
    Hold 的 ``endtime`` 必须大于 ``time``；Tap / Drag 忽略 ``endtime``。
    ``isRealTime`` / ``isRealEndTime`` 为 ``True`` 时需要提供 ``chart``，
    用于把实际秒数换算为 tick。

    返回的规格：

    - Tap / Drag：``{"type": int, "time": float}``
    - Hold：``{"type": 2, "time": float, "endtime": float}``

    规格可传给 :func:`addLine` 的 ``notes``，由 ``addLine`` 计算头部
    ``floorPosition`` 与 Hold 尾部信息。失败返回 ``None``。
    """
    return _note_spec(
        {
            "type": type,
            "time": time,
            "endtime": endtime,
            "isRealTime": isRealTime,
            "isRealEndTime": isRealEndTime,
        },
        chart,
    )


def addNote(
    chart: dict,
    index: int,
    time: float,
    type: int | str,
    endtime: float = 0.0,
    isDelayCalculate: bool = False,
    isRealTime: bool = False,
    isRealEndTime: bool = False,
) -> int | None:
    """向指定引导线添加一个 Note。

    ``index`` 为线索引，0 起，负数从末尾计算。``time`` 必须在线的
    首末节点之间。Hold 的 ``endtime`` 必须大于 ``time`` 且不超过线的
    尾节点时间；Tap / Drag 忽略 ``endtime``。

    头部与 Hold 尾部采用不同的边界规则：

    - 头部正好落在节点时间上时使用右侧节点的画布；
    - 尾部正好落在节点时间上时使用左侧节点（前一段）的画布。

    ``isDelayCalculate=True`` 时跳过高度计算，新 Note 的
    ``floorPosition``（以及 Hold 尾部高度）写为 ``NaN``，需要随后调用
    :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(index, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_points(line)
    if points is None or len(points) < 2:
        return None
    notes = _notes(line)
    if notes is None:
        return None

    note_type = _parse_note_type(type)
    if note_type is None:
        return None

    head_time = _node_time(chart, time, isRealTime)
    if head_time is None:
        return None

    tail_time = None
    if note_type == 2:
        tail_time = _node_time(chart, endtime, isRealEndTime)
        if tail_time is None:
            return None

    note = _build_note(
        chart,
        points,
        head_time,
        note_type,
        tail_time,
        calculate_floor=not isDelayCalculate,
    )
    if note is None:
        return None

    insert_at = bisect.bisect_right(
        [item["time"] for item in notes],
        head_time,
    )
    notes.insert(insert_at, note)
    return insert_at


def setNote(
    chart: dict,
    lineindex: int = -1,
    noteindex: int = -1,
    time: float | None = None,
    type: int | str | None = None,
    endtime: float | None = None,
    isDelayCalculate: bool = False,
    isRealTime: bool = False,
    isRealEndTime: bool = False,
) -> dict | None:
    """修改一个 Note，成功返回原 Note 规格 Dict。

    ``type=None`` 时保持原类型。Tap / Drag 忽略 ``endtime``；
    Hold→Tap/Drag 会清空 ``otherInformations``；Tap/Drag→Hold 必须
    提供 ``endtime``。``endtime=None`` 且原本就是 Hold 时沿用旧尾部。
    ``isDelayCalculate=True`` 时跳过高度计算，修改后 Note 的
    ``floorPosition``（以及 Hold 尾部高度）写为 ``NaN``，需要随后调用
    :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    points = _line_points(line)
    if points is None or len(points) < 2:
        return None
    notes = _notes(line)
    if notes is None:
        return None

    target_index = _resolve_existing_index(noteindex, len(notes))
    if target_index is None:
        return None

    old_note = notes[target_index]
    if not _validate_note(
        old_note,
        require_floor=not isDelayCalculate,
    ):
        return None
    old_spec = _export_note(old_note)
    if old_spec is None:
        return None

    old_type = old_note["type"]
    old_time = old_note["time"]

    if time is None and type is None and endtime is None:
        return old_spec

    if type is None:
        new_type = old_type
    else:
        new_type = _parse_note_type(type)
        if new_type is None:
            return None

    if time is None:
        head_time = old_time
    else:
        head_time = _node_time(chart, time, isRealTime)
        if head_time is None:
            return None

    first_time = points[0]["time"]
    last_time = points[-1]["time"]
    if head_time < first_time or head_time > last_time:
        return None

    if new_type == 2:
        if endtime is None:
            if old_type != 2:
                return None
            old_extra = old_note.get("otherInformations")
            if not isinstance(old_extra, list) or len(old_extra) != 3:
                return None
            tail_time = old_extra[0]
            if not _is_finite_number(tail_time) or tail_time < 0:
                return None
        else:
            tail_time = _node_time(
                chart,
                endtime,
                isRealEndTime,
            )
            if tail_time is None:
                return None

        if tail_time <= head_time or tail_time > last_time:
            return None
    else:
        tail_time = None

    head = _line_note_position(
        chart,
        points,
        head_time,
        True,
        calculate_floor=not isDelayCalculate,
    )
    if head is None:
        return None
    _, head_floor = head

    new_note = {
        "type": new_type,
        "time": head_time,
        "floorPosition": head_floor,
    }

    if new_type == 2:
        tail = _line_note_position(
            chart,
            points,
            tail_time,
            False,
            calculate_floor=not isDelayCalculate,
        )
        if tail is None:
            return None
        tail_canvas, tail_floor = tail
        new_note["otherInformations"] = [
            tail_time,
            tail_canvas,
            tail_floor,
        ]
    elif old_type == 2:
        new_note["otherInformations"] = []
    elif "otherInformations" in old_note:
        new_note["otherInformations"] = list(
            old_note["otherInformations"]
        )

    if head_time == old_time:
        notes[target_index] = new_note
    else:
        remaining = (
            notes[:target_index] + notes[target_index + 1:]
        )
        insert_at = bisect.bisect_right(
            [item["time"] for item in remaining],
            head_time,
        )
        remaining.insert(insert_at, new_note)
        notes[:] = remaining

    return old_spec


def deleteNote(
    chart: dict,
    lineindex: int = -1,
    noteindex: int = -1,
) -> dict | None:
    """删除一个 Note，成功返回原 Note 规格 Dict。

    ``lineindex`` / ``noteindex`` 从 0 起，负数从末尾计算。
    ``notes`` 为空时索引解析失败，返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None

    lines = chart.get("lines")
    if not isinstance(lines, list):
        return None

    line_index = _resolve_existing_index(lineindex, len(lines))
    if line_index is None:
        return None
    line = lines[line_index]
    if not isinstance(line, dict):
        return None

    notes = _notes(line)
    if notes is None:
        return None

    target_index = _resolve_existing_index(noteindex, len(notes))
    if target_index is None:
        return None

    deleted_spec = _export_note(notes[target_index])
    if deleted_spec is None:
        return None
    notes.pop(target_index)
    return deleted_spec


def addBpmShift(
    chart: dict,
    value: float,
    time: float,
    isDelayCalculate: bool = False,
    isRealtime: bool = False,
    isFixedTime: bool = False,
    isMultiply: bool = False,
) -> int | None:
    """添加一个 BPM 变化节点，成功返回节点索引。

    ``time`` 默认是 tick（节拍）；``isRealtime=True`` 时按实际秒数换算。
    ``isMultiply=False`` 时 ``value`` 是实际 BPM，否则是相对基准 BPM 的倍率。

    谱面通常需要在 ``time=0.0`` 处有一个 BPM 节点。若缺少该节点，
    本函数是唯一可以补上它的入口：此时只接受 ``time=0.0``（或
    ``isRealtime=True`` 且为 ``0.0`` 秒），会在最前方插入节点并重算
    所有 ``floorPosition``；其他时间点仍返回 ``None``。
    相同 ``time`` 的节点不会修改已有节点，而是插入到已有同时间节点之后。
    ``isDelayCalculate=True`` 时跳过全谱重算，新 BPM 节点的
    ``floorPosition`` 写为 ``NaN``，需要随后调用 :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    base_bpm = chart.get("bPM")
    if not _is_finite_number(base_bpm) or base_bpm <= 0:
        return None
    if not _is_finite_number(value) or value <= 0:
        return None
    if not _is_finite_number(time) or time < 0:
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
        times.append(node_time)
        values.append(node_value)

    has_zero = times[0] == 0
    for left, right in zip(times, times[1:]):
        if left > right:
            return None

    old_floor_positions = [0.0] * len(shifts)
    if has_zero:
        for position in range(1, len(shifts)):
            old_floor_positions[position] = (
                old_floor_positions[position - 1]
                + (times[position] - times[position - 1])
                * 60.0
                / (base_bpm * values[position - 1])
            )
    else:
        # 缺少 time=0.0 节点时，旧时间轴未定义，只能用文件中记录的
        # floorPosition（绝对秒数）作为 isFixedTime 的参照。
        for position, node in enumerate(shifts):
            stored = node.get("floorPosition")
            if not _is_finite_number(stored):
                return None
            old_floor_positions[position] = stored

    if isRealtime:
        if not has_zero:
            if float(time) != 0.0:
                return None
            target_time = 0.0
        else:
            tick = _seconds_to_tick(
                float(time),
                base_bpm,
                times,
                values,
                old_floor_positions,
            )
            if tick is None or tick < 0:
                return None
            target_time = tick
    else:
        target_time = float(time)
        if not has_zero and target_time != 0.0:
            return None

    new_multiplier = (
        float(value) if isMultiply else float(value) / float(base_bpm)
    )

    change_index = bisect.bisect_right(times, target_time)
    new_nodes = [dict(node) for node in shifts]
    for position, node in enumerate(new_nodes):
        node["floorPosition"] = old_floor_positions[position]

    new_nodes.insert(
        change_index,
        {
            "time": target_time,
            "value": new_multiplier,
            "easeType": 0,
            "floorPosition": 0.0,
        },
    )

    if change_index == 0:
        new_floor_position = 0.0
    else:
        previous = new_nodes[change_index - 1]
        new_floor_position = (
            previous["floorPosition"]
            + (new_nodes[change_index]["time"] - previous["time"])
            * 60.0
            / (base_bpm * previous["value"])
        )
    new_nodes[change_index]["floorPosition"] = new_floor_position

    if isFixedTime:
        for position in range(change_index + 1, len(new_nodes)):
            previous = new_nodes[position - 1]
            target_floor_position = new_nodes[position]["floorPosition"]
            delta_floor_position = (
                target_floor_position - previous["floorPosition"]
            )
            new_time = (
                previous["time"]
                + delta_floor_position
                * base_bpm
                * previous["value"]
                / 60.0
            )
            if new_time < previous["time"]:
                return None
            new_nodes[position]["time"] = new_time
    else:
        for position in range(change_index + 1, len(new_nodes)):
            previous = new_nodes[position - 1]
            new_nodes[position]["floorPosition"] = (
                previous["floorPosition"]
                + (new_nodes[position]["time"] - previous["time"])
                * 60.0
                / (base_bpm * previous["value"])
            )

    for position, node in enumerate(new_nodes):
        if (
            not _is_finite_number(node.get("time"))
            or not _is_finite_number(node.get("value"))
            or node["value"] <= 0
        ):
            return None
        if position > 0 and node["time"] < new_nodes[position - 1]["time"]:
            return None

    if isDelayCalculate:
        new_nodes[change_index]["floorPosition"] = math.nan

    old_nodes = list(shifts)
    shifts[:] = new_nodes
    if isDelayCalculate:
        return change_index

    plan = _make_floor_plan(chart)
    if plan is None:
        shifts[:] = old_nodes
        return None
    _apply_floor_plan(plan)
    return change_index


def setBpmShift(
    chart: dict,
    index: int = -1,
    value: float | None = None,
    time: float | None = None,
    isDelayCalculate: bool = False,
    isRealtime: bool = False,
    isFixedTime: bool = False,
    isMultiply: bool = False,
) -> dict | None:
    """修改一个 BPM 变化节点，成功返回原节点规格 Dict。

    ``index`` 为 0 起的节点索引，负数从末尾计算。指向第 0 个节点时不能
    修改 ``time``（允许传入 ``0.0``）。修改后会自动重排并重新计算
    ``floorPosition``。谱面必须在 ``time=0.0`` 处有一个 BPM 节点，
    否则返回 ``None``。``isDelayCalculate=True`` 时跳过全谱重算，修改后
    BPM 节点的 ``floorPosition`` 写为 ``NaN``，需要随后调用
    :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    base_bpm = chart.get("bPM")
    if not _is_finite_number(base_bpm) or base_bpm <= 0:
        return None

    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list) or not shifts:
        return None
    if not _is_int(index):
        return None

    target_index = index + len(shifts) if index < 0 else index
    if not 0 <= target_index < len(shifts):
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
            or node_value <= 0
        ):
            return None
        times.append(node_time)
        values.append(node_value)

    if times[0] != 0:
        return None
    for left, right in zip(times, times[1:]):
        if left > right:
            return None

    old_floor_positions = [0.0] * len(shifts)
    for position in range(1, len(shifts)):
        old_floor_positions[position] = (
            old_floor_positions[position - 1]
            + (times[position] - times[position - 1])
            * 60.0
            / (base_bpm * values[position - 1])
        )

    old_node = shifts[target_index]
    old_spec = _export_bpm_shift(old_node)
    if old_spec is None:
        return None
    current_time = times[target_index]

    if value is None:
        new_multiplier = values[target_index]
    else:
        if not _is_finite_number(value) or value <= 0:
            return None
        new_multiplier = (
            float(value) if isMultiply else float(value) / float(base_bpm)
        )

    if time is None:
        target_time = current_time
    else:
        if not _is_finite_number(time) or time < 0:
            return None
        if target_index == 0:
            if time != current_time and time != 0.0:
                return None
            target_time = float(time)
        else:
            if time <= 0:
                return None
            if isRealtime:
                tick = _seconds_to_tick(
                    float(time),
                    base_bpm,
                    times,
                    values,
                    old_floor_positions,
                )
                if tick is None or tick <= 0:
                    return None
                target_time = tick
            else:
                target_time = float(time)

    if (
        new_multiplier == values[target_index]
        and target_time == current_time
    ):
        return old_spec

    new_nodes = [dict(node) for node in shifts]
    for position, node in enumerate(new_nodes):
        node["floorPosition"] = old_floor_positions[position]

    changed_node = new_nodes.pop(target_index)
    changed_node["time"] = target_time
    changed_node["value"] = new_multiplier

    remaining_times = [node["time"] for node in new_nodes]
    if target_time != current_time and any(
        node_time == target_time for node_time in remaining_times
    ):
        return None

    if target_time == current_time:
        change_index = target_index
        new_nodes.insert(target_index, changed_node)
    else:
        change_index = bisect.bisect_left(remaining_times, target_time)
        new_nodes.insert(change_index, changed_node)

    start_index = min(target_index, change_index)
    for position in range(start_index, len(new_nodes)):
        node = new_nodes[position]
        if position == 0:
            node["floorPosition"] = 0.0
            continue

        previous = new_nodes[position - 1]
        if position <= change_index:
            node["floorPosition"] = (
                previous["floorPosition"]
                + (node["time"] - previous["time"])
                * 60.0
                / (base_bpm * previous["value"])
            )
        elif isFixedTime:
            target_floor_position = node["floorPosition"]
            delta_floor_position = (
                target_floor_position - previous["floorPosition"]
            )
            new_time = (
                previous["time"]
                + delta_floor_position
                * base_bpm
                * previous["value"]
                / 60.0
            )
            if new_time < previous["time"]:
                return None
            node["time"] = new_time
            node["floorPosition"] = target_floor_position
        else:
            node["floorPosition"] = (
                previous["floorPosition"]
                + (node["time"] - previous["time"])
                * 60.0
                / (base_bpm * previous["value"])
            )

    for position, node in enumerate(new_nodes):
        if (
            not _is_finite_number(node.get("time"))
            or not _is_finite_number(node.get("value"))
            or node["value"] <= 0
        ):
            return None
        if position > 0 and node["time"] < new_nodes[position - 1]["time"]:
            return None

    if isDelayCalculate:
        new_nodes[change_index]["floorPosition"] = math.nan

    old_nodes = list(shifts)
    shifts[:] = new_nodes
    if isDelayCalculate:
        return old_spec

    plan = _make_floor_plan(chart)
    if plan is None:
        shifts[:] = old_nodes
        return None
    _apply_floor_plan(plan)
    return old_spec


def deleteBpmShift(
    chart: dict,
    index: int = -1,
    isDelayCalculate: bool = False,
    isFixedTime: bool = False,
) -> dict | None:
    """删除一个 BPM 变化节点，成功返回原节点规格 Dict。

    ``index`` 为 0 起的节点索引，负数从末尾计算。指向第 0 个节点时不删除，
    而是把它重置为 ``new()`` 中的初始节点。谱面必须在 ``time=0.0`` 处
    有一个 BPM 节点，否则返回 ``None``。``isDelayCalculate=True`` 时
    跳过全谱重算，被重置节点的 ``floorPosition`` 写为 ``NaN``，需要随后
    调用 :func:`refresh`。
    """
    if not isinstance(chart, dict):
        return None

    base_bpm = chart.get("bPM")
    if not _is_finite_number(base_bpm) or base_bpm <= 0:
        return None

    shifts = chart.get("bpmShifts")
    if not isinstance(shifts, list) or not shifts:
        return None
    if not _is_int(index):
        return None

    target_index = index + len(shifts) if index < 0 else index
    if not 0 <= target_index < len(shifts):
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
            or node_value <= 0
        ):
            return None
        times.append(node_time)
        values.append(node_value)

    if times[0] != 0:
        return None
    for left, right in zip(times, times[1:]):
        if left > right:
            return None

    old_floor_positions = [0.0] * len(shifts)
    for position in range(1, len(shifts)):
        old_floor_positions[position] = (
            old_floor_positions[position - 1]
            + (times[position] - times[position - 1])
            * 60.0
            / (base_bpm * values[position - 1])
        )

    old_node = shifts[target_index]
    old_spec = _export_bpm_shift(old_node)
    if old_spec is None:
        return None
    new_nodes = [dict(node) for node in shifts]
    for position, node in enumerate(new_nodes):
        node["floorPosition"] = old_floor_positions[position]

    if target_index == 0:
        new_nodes[0] = {
            "time": 0.0,
            "value": 1.0,
            "easeType": 0,
            "floorPosition": 0.0,
        }
        start_index = 1
    else:
        new_nodes.pop(target_index)
        start_index = target_index

    for position in range(start_index, len(new_nodes)):
        node = new_nodes[position]
        previous = new_nodes[position - 1]
        if isFixedTime:
            target_floor_position = node["floorPosition"]
            delta_floor_position = (
                target_floor_position - previous["floorPosition"]
            )
            new_time = (
                previous["time"]
                + delta_floor_position
                * base_bpm
                * previous["value"]
                / 60.0
            )
            if new_time < previous["time"]:
                return None
            node["time"] = new_time
        else:
            node["floorPosition"] = (
                previous["floorPosition"]
                + (node["time"] - previous["time"])
                * 60.0
                / (base_bpm * previous["value"])
            )

    for position, node in enumerate(new_nodes):
        if (
            not _is_finite_number(node.get("time"))
            or not _is_finite_number(node.get("value"))
            or node["value"] <= 0
        ):
            return None
        if position > 0 and node["time"] < new_nodes[position - 1]["time"]:
            return None

    if isDelayCalculate and target_index == 0:
        new_nodes[0]["floorPosition"] = math.nan

    old_nodes = list(shifts)
    shifts[:] = new_nodes
    if isDelayCalculate:
        return old_spec

    plan = _make_floor_plan(chart)
    if plan is None:
        shifts[:] = old_nodes
        return None
    _apply_floor_plan(plan)
    return old_spec
