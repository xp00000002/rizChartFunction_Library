"""高级缓动设置工具。

所有函数只调用 base / chart / query 暴露的公开函数，不直接修改谱面 dict。
"""

from __future__ import annotations

import copy
import heapq
import math

from .base import refresh
from .chart import (
    addBpmShift,
    addCameraPosition,
    addCameraScale,
    addCanvasPosition,
    addCanvasSpeed,
    addLineColor,
    addLinePoint,
    addRingPoint,
    createLinePoint,
    setCameraPosition,
    setCameraScale,
    setCanvasPosition,
    setLineColor,
    setLinePoint,
    setRingPoint,
)
from .query import (
    getBpmShift,
    getCameraPosition,
    getCameraScale,
    getCanvasCount,
    getCanvasPosition,
    getCanvasSpeed,
    getLine,
    getLineColor,
    getLineCount,
    getLinePoint,
    getRingPoint,
)

__all__ = [
    "setBpmShiftEase",
    "setLinePointPositionEase",
    "setLinePointColorEase",
    "setLinePointColorByList",
    "setRingColorEase",
    "setLineColorEase",
    "setCanvasPositionEase",
    "setCanvasSpeedEase",
    "setCameraPositionEase",
    "setCameraScaleEase",
]


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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
        isinstance(value, (list, tuple))
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


def _parse_ease(value: object) -> int | list | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value if 0 <= value <= 25 else None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        if not all(_is_finite_number(item) for item in value):
            return None
        x1, y1, x2, y2 = value
        if not (0.0 <= x1 <= 1.0 and 0.0 <= x2 <= 1.0):
            return None
        return [float(x1), float(y1), float(x2), float(y2)]
    return None


def _bezier_at(ease: list, t: float) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    x1, y1, x2, y2 = ease
    low = 0.0
    high = 1.0
    for _ in range(60):
        mid = (low + high) * 0.5
        inv = 1.0 - mid
        x_value = 3.0 * inv * inv * mid * x1 + 3.0 * inv * mid * mid * x2 + mid ** 3
        if x_value < t:
            low = mid
        else:
            high = mid
    u = (low + high) * 0.5
    inv = 1.0 - u
    return 3.0 * inv * inv * u * y1 + 3.0 * inv * u * u * y2 + u ** 3


def _ease_value(ease: int | list, t: float) -> float | None:
    if isinstance(ease, list):
        return _bezier_at(ease, t)
    if not isinstance(ease, int) or isinstance(ease, bool) or not 0 <= ease <= 25:
        return None
    u = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else float(t)
    if ease == 0:
        return u
    if ease == 1:
        return u * u
    if ease == 2:
        return 1.0 - (1.0 - u) ** 2
    if ease == 3:
        return 2.0 * u * u if u < 0.5 else 1.0 - 2.0 * (1.0 - u) ** 2
    if ease == 4:
        return u ** 3
    if ease == 5:
        return 1.0 - (1.0 - u) ** 3
    if ease == 6:
        return 4.0 * u ** 3 if u < 0.5 else 1.0 - 4.0 * (1.0 - u) ** 3
    if ease == 7:
        return u ** 4
    if ease == 8:
        return 1.0 - (1.0 - u) ** 4
    if ease == 9:
        return 8.0 * u ** 4 if u < 0.5 else 1.0 - 8.0 * (1.0 - u) ** 4
    if ease == 10:
        return u ** 5
    if ease == 11:
        return 1.0 - (1.0 - u) ** 5
    if ease == 12:
        return 16.0 * u ** 5 if u < 0.5 else 1.0 - 16.0 * (1.0 - u) ** 5
    if ease == 13:
        return 0.0
    if ease == 14:
        return 1.0
    if ease == 15:
        return 1.0 - math.sqrt(max(0.0, 1.0 - u * u))
    if ease == 16:
        return math.sqrt(max(0.0, 1.0 - (1.0 - u) ** 2))
    if ease == 17:
        return math.sin(math.pi * u / 2.0)
    if ease == 18:
        return 1.0 - math.cos(math.pi * u / 2.0)
    if ease == 19:
        if u < 0.5:
            return 0.5 * (1.0 - math.sqrt(max(0.0, 1.0 - 4.0 * u * u)))
        value = -2.0 * u + 2.0
        return 0.5 * (math.sqrt(max(0.0, 1.0 - value * value)) + 1.0)
    if ease == 20:
        value = 2.0 * u - 1.0
        root = math.sqrt(max(0.0, 1.0 - value * value))
        return 0.5 * root if u < 0.5 else 1.0 - 0.5 * root
    if ease == 21:
        return 0.5 * (1.0 - math.cos(math.pi * u))
    if ease == 22:
        if u < 0.5:
            return 0.5 * math.sin(math.pi * u)
        return 1.0 - 0.5 * math.sin(math.pi * u)
    if ease == 23:
        return 0.0 if u == 0.0 else 2.0 ** (10.0 * u - 10.0)
    if ease == 24:
        return 1.0 if u == 1.0 else 1.0 - 2.0 ** (-10.0 * u)
    if ease == 25:
        if u == 0.0:
            return 0.0
        if u < 0.5:
            return 2.0 ** (20.0 * u - 11.0)
        if u == 1.0:
            return 1.0
        return 1.0 - 2.0 ** (-20.0 * u + 9.0)
    return None


def _lerp_value(start, end, ratio: float):
    if isinstance(start, list):
        return [
            float(start[i]) + (float(end[i]) - float(start[i])) * ratio
            for i in range(len(start))
        ]
    return float(start) + (float(end) - float(start)) * ratio


def _round_color(value: list) -> list[int]:
    return [max(0, min(255, int(math.floor(float(item) + 0.5)))) for item in value]


def _color_at(start: list, end: list, ease: int | list, u: float) -> list | None:
    ratio = _ease_value(ease, u)
    if ratio is None:
        return None
    return _round_color(_lerp_value(start, end, ratio))


def _normalized_curve_point(
    u: float,
    value_fn,
    start,
    end,
    is_color: bool,
) -> list[float]:
    raw = value_fn(u)
    if is_color:
        components = [float(item) / 255.0 for item in raw]
    else:
        delta = float(end) - float(start)
        if delta == 0.0:
            components = [0.0]
        else:
            components = [(float(raw) - float(start)) / delta]
    return [float(u)] + components


def _distance(a: list, b: list) -> float:
    total = 0.0
    for left, right in zip(a, b):
        diff = left - right
        total += diff * diff
    return math.sqrt(total)


def _quantile_from_cumulative(values: list[float], fractions: list[float]) -> list[float] | None:
    if not values:
        return None
    total = values[-1]
    if total <= 0.0:
        return None
    result = []
    index = 0
    for fraction in fractions:
        target = total * fraction
        while index < len(values) - 1 and values[index] < target:
            index += 1
        if index == 0:
            result.append(0.0)
        else:
            left = values[index - 1]
            span = values[index] - left
            ratio = 0.0 if span == 0.0 else (target - left) / span
            result.append((index - 1 + ratio) / (len(values) - 1))
    return result


def _make_samples(
    ease: int | list,
    precision: object,
    inserttype: str,
    value_fn,
    start,
    end,
    is_color: bool,
) -> list[float] | None:
    if inserttype == "uniform":
        count = int(precision)
        return [index / (count + 1) for index in range(1, count + 1)]

    if inserttype == "arc":
        count = int(precision)
        steps = 512
        fractions = [index / (count + 1) for index in range(1, count + 1)]
        points = [
            _normalized_curve_point(index / steps, value_fn, start, end, is_color)
            for index in range(steps + 1)
        ]
        cumulative = [0.0]
        for index in range(1, len(points)):
            cumulative.append(cumulative[-1] + _distance(points[index - 1], points[index]))
        if cumulative[-1] <= 0.0:
            return fractions
        sampled = _quantile_from_cumulative(cumulative, fractions)
        return fractions if sampled is None else sampled

    if inserttype == "curvature":
        count = int(precision)
        steps = 512
        points = [
            _normalized_curve_point(index / steps, value_fn, start, end, is_color)
            for index in range(steps + 1)
        ]
        weights = [0.0] * len(points)
        for index in range(1, len(points) - 1):
            second = [
                points[index - 1][dim] - 2.0 * points[index][dim] + points[index + 1][dim]
                for dim in range(len(points[index]))
            ]
            weights[index] = math.sqrt(sum(value * value for value in second))
        cumulative = [0.0]
        for weight in weights[1:]:
            cumulative.append(cumulative[-1] + weight)
        if cumulative[-1] <= 0.0:
            return [index / (count + 1) for index in range(1, count + 1)]
        fractions = [index / (count + 1) for index in range(1, count + 1)]
        sampled = _quantile_from_cumulative(cumulative, fractions)
        return fractions if sampled is None else sampled

    if inserttype in ("recursion", "priority"):
        threshold = float(precision)
        insert_us: list[float] = []

        def error_at(u0: float, u1: float) -> tuple[float, float]:
            mid = (u0 + u1) * 0.5
            a = _normalized_curve_point(u0, value_fn, start, end, is_color)
            b = _normalized_curve_point(u1, value_fn, start, end, is_color)
            m = _normalized_curve_point(mid, value_fn, start, end, is_color)
            linear = [(a[i] + b[i]) * 0.5 for i in range(len(a))]
            distance = _distance(a, b)
            if distance <= 1e-15:
                return 0.0, mid
            return _distance(m, linear) / distance, mid

        if inserttype == "recursion":
            def recurse(u0: float, u1: float, depth: int) -> None:
                if depth > 24 or len(insert_us) >= 4096:
                    return
                err, mid = error_at(u0, u1)
                if err <= threshold:
                    return
                insert_us.append(mid)
                recurse(u0, mid, depth + 1)
                recurse(mid, u1, depth + 1)

            recurse(0.0, 1.0, 0)
        else:
            heap = []
            err, mid = error_at(0.0, 1.0)
            heapq.heappush(heap, (-err, 0.0, 1.0, mid, 0))
            while heap and len(insert_us) < 4096:
                negative, u0, u1, mid, depth = heapq.heappop(heap)
                err = -negative
                if err <= threshold:
                    break
                insert_us.append(mid)
                if depth < 24:
                    left_err, left_mid = error_at(u0, mid)
                    right_err, right_mid = error_at(mid, u1)
                    heapq.heappush(heap, (-left_err, u0, mid, left_mid, depth + 1))
                    heapq.heappush(heap, (-right_err, mid, u1, right_mid, depth + 1))
        return sorted(insert_us)

    return None


def _tick_values(t: float) -> list[int]:
    k = int(math.floor(t))
    result = [k]
    if t == float(k) and k > 0:
        result.append(k - 1)
    return result


def _tick_counts(times: list) -> dict[int, int]:
    counts: dict[int, int] = {}
    for value in times:
        if not _is_finite_number(value):
            continue
        for tick in _tick_values(float(value)):
            counts[tick] = counts.get(tick, 0) + 1
    return counts


def _can_insert(counts: dict[int, int], time: float, limit: int = 48) -> bool:
    return all(counts.get(tick, 0) < limit for tick in _tick_values(time))


def _record_insert(counts: dict[int, int], time: float) -> None:
    for tick in _tick_values(time):
        counts[tick] = counts.get(tick, 0) + 1


def _choose_spread(group: list[tuple[float, float]], capacity: int) -> list[tuple[float, float]]:
    if capacity <= 0:
        return []
    if len(group) <= capacity:
        return list(group)
    if capacity == 1:
        target = (group[0][1] + group[-1][1]) * 0.5
        return [min(group, key=lambda item: abs(item[1] - target))]

    low = group[0][1]
    high = group[-1][1]
    available = list(group)
    chosen = []
    for index in range(capacity):
        target = low + (high - low) * index / (capacity - 1)
        best_index = min(
            range(len(available)),
            key=lambda item: abs(available[item][1] - target),
        )
        chosen.append(available.pop(best_index))
    chosen.sort(key=lambda item: item[1])
    return chosen


def _select_samples_for_capacity(
    samples: list[float],
    start_time: float,
    end_time: float,
    times: list,
    max_per_tick: int = 48,
) -> list[float]:
    counts = _tick_counts(times)
    groups: dict[int, list[tuple[float, float]]] = {}
    integer_samples = []
    seen_times = set()
    for u in samples:
        time = start_time + (end_time - start_time) * u
        if not (start_time < time < end_time) or time in seen_times:
            continue
        seen_times.add(time)
        tick = int(math.floor(time))
        if time == float(tick):
            integer_samples.append((u, time))
        else:
            groups.setdefault(tick, []).append((u, time))

    selected: list[float] = []
    for tick in sorted(groups):
        capacity = max(0, max_per_tick - counts.get(tick, 0))
        if capacity == 0:
            continue
        chosen = _choose_spread(groups[tick], capacity)
        for u, time in chosen:
            selected.append(u)
            _record_insert(counts, time)

    for u, time in sorted(integer_samples, key=lambda item: item[1]):
        if not _can_insert(counts, time, max_per_tick):
            continue
        selected.append(u)
        _record_insert(counts, time)
    selected.sort()
    return selected


def _select_samples(
    samples: list[float],
    start_time: float,
    end_time: float,
    times: list,
    inserttype: str,
) -> list[float]:
    if inserttype in ("recursion", "priority"):
        return _select_samples_for_capacity(
            samples,
            start_time,
            end_time,
            times,
            max_per_tick=48,
        )

    selected = []
    seen_times = set()
    for u in samples:
        time = start_time + (end_time - start_time) * u
        if not (start_time < time < end_time) or time in seen_times:
            continue
        seen_times.add(time)
        selected.append(u)
    selected.sort()
    return selected


def _refresh_all(chart: dict) -> bool:
    return refresh(chart, mode="all", type="all") is not None


def _run_ease_items(
    chart: dict,
    items: list[tuple[list[int], object]],
    isFailAddAllowed: bool,
    post=None,
) -> list[int]:
    def run(target: dict, stop_on_first: bool) -> tuple[bool, list[int]]:
        failures = []
        for positions, action in items:
            if action(target):
                continue
            failures.extend(positions)
            if stop_on_first:
                break
        return not failures, failures

    if not isFailAddAllowed:
        trial = copy.deepcopy(chart)
        ok, failures = run(trial, True)
        if not ok:
            return [failures[0]] if failures else [-1]
        ok, failures = run(chart, False)
        if not ok:
            return [failures[0]] if failures else [-1]
        if post is not None and not post(chart):
            return [-1]
        return []

    failures = []
    successes = 0
    for positions, action in items:
        trial = copy.deepcopy(chart)
        if not action(trial):
            failures.extend(positions)
            continue
        if action(chart):
            successes += 1
        else:
            failures.extend(positions)
    if post is not None and successes and not post(chart):
        return [-1]
    return sorted({int(value) for value in failures})


def _flat_entries(chart: dict, indexlist: object, getter) -> list | None:
    indices = _plain_indices(indexlist)
    if indices is None:
        return None
    specs = getter(chart)
    if not isinstance(specs, list):
        return None
    valid = []
    invalid = []
    for position, index in enumerate(indices):
        resolved = _resolve_index(index, len(specs))
        if resolved is None or resolved + 1 >= len(specs):
            invalid.append((position, None, None, None))
            continue
        valid.append((position, resolved, specs[resolved], specs[resolved + 1]))
    valid.sort(key=lambda item: item[1], reverse=True)
    return valid + invalid


def _line_entries(chart: dict, indexlist: object, getter) -> list | None:
    pairs = _nested_indices(indexlist)
    if pairs is None:
        return None
    line_count = getLineCount(chart)
    if line_count is None:
        return None
    valid = []
    invalid = []
    for position, (line_index, child_index) in enumerate(pairs):
        resolved_line = _resolve_index(line_index, line_count)
        if resolved_line is None:
            invalid.append((position, None, None, None, None))
            continue
        specs = getter(chart, resolved_line, 0, -1)
        if not isinstance(specs, list):
            invalid.append((position, None, None, None, None))
            continue
        resolved_child = _resolve_index(child_index, len(specs))
        if resolved_child is None or resolved_child + 1 >= len(specs):
            invalid.append((position, None, None, None, None))
            continue
        valid.append(
            (
                position,
                resolved_line,
                resolved_child,
                specs[resolved_child],
                specs[resolved_child + 1],
            )
        )
    valid.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return valid + invalid


def _canvas_entries(chart: dict, indexlist: object, getter) -> list | None:
    pairs = _nested_indices(indexlist)
    if pairs is None:
        return None
    canvas_count = getCanvasCount(chart)
    if canvas_count is None:
        return None
    valid = []
    invalid = []
    for position, (canvas_index, child_index) in enumerate(pairs):
        resolved_canvas = _resolve_index(canvas_index, canvas_count)
        if resolved_canvas is None:
            invalid.append((position, None, None, None, None))
            continue
        specs = getter(chart, resolved_canvas, 0, -1)
        if not isinstance(specs, list):
            invalid.append((position, None, None, None, None))
            continue
        resolved_child = _resolve_index(child_index, len(specs))
        if resolved_child is None or resolved_child + 1 >= len(specs):
            invalid.append((position, None, None, None, None))
            continue
        valid.append(
            (
                position,
                resolved_canvas,
                resolved_child,
                specs[resolved_child],
                specs[resolved_child + 1],
            )
        )
    valid.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return valid + invalid


def _line_point_times(chart: dict, line_index: int) -> list | None:
    specs = getLinePoint(chart, line_index, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _ring_times(chart: dict, line_index: int) -> list | None:
    specs = getRingPoint(chart, line_index, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _line_color_times(chart: dict, line_index: int) -> list | None:
    specs = getLineColor(chart, line_index, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _canvas_position_times(chart: dict, canvas_index: int) -> list | None:
    specs = getCanvasPosition(chart, canvas_index, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _canvas_speed_times(chart: dict, canvas_index: int) -> list | None:
    specs = getCanvasSpeed(chart, canvas_index, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _camera_position_times(chart: dict) -> list | None:
    specs = getCameraPosition(chart, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _camera_scale_times(chart: dict) -> list | None:
    specs = getCameraScale(chart, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


def _bpm_times(chart: dict) -> list | None:
    specs = getBpmShift(chart, 0, -1)
    if not isinstance(specs, list):
        return None
    return [spec.get("time") for spec in specs]


_FIRST_HALF = {19: 15, 20: 16, 21: 18, 22: 17}
_SECOND_HALF = {19: 16, 20: 15, 21: 17, 22: 18}


def _position_action(
    start_time: float,
    end_time: float,
    start_value: float,
    end_value: float,
    ease: int | list,
    precision: object,
    inserttype: str,
    set_ease,
    add_value,
    get_times,
):
    def action(chart: dict) -> bool:
        t0 = float(start_time)
        t1 = float(end_time)
        if t1 <= t0:
            return False
        v0 = float(start_value)
        v1 = float(end_value)
        if isinstance(ease, int) and 0 <= ease <= 18:
            return set_ease(chart, ease)
        if isinstance(ease, int) and ease in _FIRST_HALF:
            midpoint_time = (t0 + t1) * 0.5
            midpoint_value = (v0 + v1) * 0.5
            if not (t0 < midpoint_time < t1):
                return False
            if not add_value(
                chart,
                midpoint_time,
                midpoint_value,
                _SECOND_HALF[ease],
                0.5,
            ):
                return False
            return set_ease(chart, _FIRST_HALF[ease])
        samples = _make_samples(
            ease,
            precision,
            inserttype,
            lambda u: v0 + (v1 - v0) * _ease_value(ease, u),
            v0,
            v1,
            False,
        )
        if samples is None:
            return False
        times = get_times(chart)
        if times is None:
            return False
        for u in _select_samples(samples, t0, t1, times, inserttype):
            time = t0 + (t1 - t0) * u
            value = v0 + (v1 - v0) * _ease_value(ease, u)
            if not add_value(chart, time, value, 0, u):
                return False
        return set_ease(chart, 0)

    return action


def _step_action(
    start_time: float,
    end_time: float,
    start_value: float,
    end_value: float,
    ease: int | list,
    precision: object,
    inserttype: str,
    add_value,
    get_times,
):
    def action(chart: dict) -> bool:
        t0 = float(start_time)
        t1 = float(end_time)
        if t1 <= t0:
            return False
        if ease == 13:
            return True
        v0 = float(start_value)
        v1 = float(end_value)
        times = get_times(chart)
        if times is None:
            return False
        if ease == 14:
            time = math.nextafter(t0, t1)
            if time >= t1:
                return False
            return add_value(chart, time, v1)
        samples = _make_samples(
            ease,
            precision,
            inserttype,
            lambda u: v0 + (v1 - v0) * _ease_value(ease, u),
            v0,
            v1,
            False,
        )
        if samples is None:
            return False
        for u in _select_samples(samples, t0, t1, times, inserttype):
            time = t0 + (t1 - t0) * u
            value = v0 + (v1 - v0) * _ease_value(ease, u)
            if not add_value(chart, time, value):
                return False
        return True

    return action


def _color_node_action(
    start_time: float,
    end_time: float,
    start_color: list,
    end_color: list,
    ease: int | list,
    precision: object,
    inserttype: str,
    set_end,
    add_color,
    get_times,
):
    def action(chart: dict) -> bool:
        t0 = float(start_time)
        t1 = float(end_time)
        if t1 <= t0:
            return False
        if ease == 0:
            return True
        if ease == 13:
            return set_end(chart, start_color)
        if ease == 14:
            time = math.nextafter(t0, t1)
            if time >= t1:
                return False
            return add_color(chart, time, end_color, end_color)
        samples = _make_samples(
            ease,
            precision,
            inserttype,
            lambda u: _lerp_value(start_color, end_color, _ease_value(ease, u)),
            start_color,
            end_color,
            True,
        )
        if samples is None:
            return False
        times = get_times(chart)
        if times is None:
            return False
        accepted = _select_samples(samples, t0, t1, times, inserttype)
        if not accepted:
            return True
        first_color = _color_at(start_color, end_color, ease, accepted[0])
        if first_color is None or not set_end(chart, first_color):
            return False
        for index, u in enumerate(accepted):
            time = t0 + (t1 - t0) * u
            next_u = accepted[index + 1] if index + 1 < len(accepted) else 1.0
            segment_end = _color_at(start_color, end_color, ease, next_u)
            segment_start = _color_at(start_color, end_color, ease, u)
            if segment_start is None or segment_end is None:
                return False
            if not add_color(chart, time, segment_start, segment_end):
                return False
        return True

    return action


def _line_point_color_action(
    line_index: int,
    point_index: int,
    start_time: float,
    end_time: float,
    start_color: list,
    end_color: list,
    start_x: float,
    end_x: float,
    original_ease: int,
    canvas_index: int,
    ease: int | list,
    precision: object,
    inserttype: str,
):
    def x_at(u: float) -> float:
        ratio = _ease_value(original_ease, u)
        if ratio is None:
            ratio = u
        return float(start_x) + (float(end_x) - float(start_x)) * ratio

    def action(chart: dict) -> bool:
        t0 = float(start_time)
        t1 = float(end_time)
        if t1 <= t0:
            return False
        times = _line_point_times(chart, line_index)
        if times is None:
            return False

        def insert_point(time: float, color: list, u: float) -> bool:
            return addLinePoint(
                chart,
                time,
                x_at(u),
                canvas_index,
                0,
                color,
                lineindex=line_index,
            ) is not None

        if ease == 0:
            return setLinePoint(
                chart,
                line_index,
                point_index,
                easetype=0,
            ) is not None
        if ease == 13:
            time = math.nextafter(t1, t0)
            if not (t0 < time < t1):
                return False
            u = (time - t0) / (t1 - t0)
            if not insert_point(time, start_color, u):
                return False
            return setLinePoint(
                chart,
                line_index,
                point_index,
                easetype=0,
            ) is not None
        if ease == 14:
            time = math.nextafter(t0, t1)
            if time >= t1:
                return False
            u = (time - t0) / (t1 - t0)
            if not insert_point(time, end_color, u):
                return False
            return setLinePoint(
                chart,
                line_index,
                point_index,
                easetype=0,
            ) is not None

        samples = _make_samples(
            ease,
            precision,
            inserttype,
            lambda u: _lerp_value(start_color, end_color, _ease_value(ease, u)),
            start_color,
            end_color,
            True,
        )
        if samples is None:
            return False
        for u in _select_samples(samples, t0, t1, times, inserttype):
            time = t0 + (t1 - t0) * u
            color = _color_at(start_color, end_color, ease, u)
            if color is None:
                return False
            if not insert_point(time, color, u):
                return False
        return setLinePoint(
            chart,
            line_index,
            point_index,
            easetype=0,
        ) is not None

    return action


def _validate_common(inserttype: object, precision: object) -> bool:
    if inserttype not in ("uniform", "arc", "curvature", "recursion", "priority"):
        return False
    if inserttype in ("uniform", "arc", "curvature"):
        return (
            isinstance(precision, int)
            and not isinstance(precision, bool)
            and precision > 0
        )
    return _is_finite_number(precision) and float(precision) > 0.0


def _invalid_item(position: int):
    return ([position], lambda chart: False)


def setLinePointPositionEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置引导线节点位置缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _line_entries(chart, indexlist, getLinePoint)
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, line_index, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if (
            selected.get("canvasIndex") != following.get("canvasIndex")
            or float(following["time"]) <= float(selected["time"])
        ):
            items.append(_invalid_item(position))
            continue

        start_time = float(selected["time"])
        end_time = float(following["time"])
        start_value = float(selected["xPosition"])
        end_value = float(following["xPosition"])
        start_color = list(selected["color"])
        end_color = list(following["color"])
        canvas_index = int(selected["canvasIndex"])

        def set_ease(target: dict, value: int, line_index=line_index, point_index=point_index) -> bool:
            return setLinePoint(
                target,
                line_index,
                point_index,
                easetype=value,
            ) is not None

        def add_value(
            target: dict,
            time: float,
            value: float,
            value_ease: int,
            u: float,
            line_index=line_index,
            canvas_index=canvas_index,
            start_color=start_color,
            end_color=end_color,
        ) -> bool:
            color = _round_color(_lerp_value(start_color, end_color, u))
            return addLinePoint(
                target,
                time,
                value,
                canvas_index,
                value_ease,
                color,
                lineindex=line_index,
            ) is not None

        action = _position_action(
            start_time,
            end_time,
            start_value,
            end_value,
            ease,
            precision,
            inserttype,
            set_ease,
            add_value,
            lambda target, line_index=line_index: _line_point_times(target, line_index),
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setLinePointColorEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置引导线节点颜色缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _line_entries(chart, indexlist, getLinePoint)
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, line_index, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if (
            selected.get("canvasIndex") != following.get("canvasIndex")
            or float(following["time"]) <= float(selected["time"])
        ):
            items.append(_invalid_item(position))
            continue

        original_ease = selected.get("easeType")
        if not isinstance(original_ease, int) or isinstance(original_ease, bool):
            original_ease = 0
        action = _line_point_color_action(
            line_index,
            point_index,
            float(selected["time"]),
            float(following["time"]),
            list(selected["color"]),
            list(following["color"]),
            float(selected["xPosition"]),
            float(following["xPosition"]),
            original_ease,
            int(selected["canvasIndex"]),
            ease,
            precision,
            inserttype,
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setLinePointColorByList(
    chart: dict,
    lineindex: int,
    startpointindex: int,
    endpointindex: int,
    startcolor: str | list | None = None,
    endcolor: str | list | None = None,
    easetype: int | list = 0,
) -> list[int] | None:
    """按节点索引区间给已有线节点重新着色。

    区间包含 ``startpointindex`` 和 ``endpointindex``，不新增或删除节点。
    颜色按节点时间比例插值；若区间首尾时间相同，则退化为按节点索引比例
    插值。``startcolor`` / ``endcolor`` 为 ``None`` 时使用边界节点原色。
    成功返回空列表，失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not all(
        _is_int(value)
        for value in (lineindex, startpointindex, endpointindex)
    ):
        return None

    line_count = getLineCount(chart)
    if not _is_int(line_count) or line_count <= 0:
        return None
    line_index = lineindex + line_count if lineindex < 0 else lineindex
    if not 0 <= line_index < line_count:
        return None

    line = getLine(chart, line_index)
    if not isinstance(line, dict):
        return None
    points = line.get("linePoints")
    if not isinstance(points, list) or len(points) < 2:
        return None

    point_count = len(points)
    start = (
        startpointindex + point_count
        if startpointindex < 0
        else startpointindex
    )
    end = (
        endpointindex + point_count
        if endpointindex < 0
        else endpointindex
    )
    if not 0 <= start < end < point_count:
        return None

    ease = _parse_ease(easetype)
    if ease is None:
        return None

    start_point = points[start]
    end_point = points[end]
    if not isinstance(start_point, dict) or not isinstance(end_point, dict):
        return None

    start_time = start_point.get("time")
    end_time = end_point.get("time")
    if not _is_finite_number(start_time) or not _is_finite_number(end_time):
        return None

    def resolve_color(point: dict, override):
        color_value = point.get("color") if override is None else override
        spec = createLinePoint(
            point.get("time"),
            point.get("xPosition"),
            point.get("canvasIndex"),
            0,
            color_value,
        )
        if spec is None:
            return None
        return list(spec["color"])

    start_color = resolve_color(start_point, startcolor)
    end_color = resolve_color(end_point, endcolor)
    if start_color is None or end_color is None:
        return None

    duration = float(end_time) - float(start_time)
    span = end - start
    entries = []
    for point_index in range(start, end + 1):
        point = points[point_index]
        if not isinstance(point, dict):
            return None
        point_time = point.get("time")
        if not _is_finite_number(point_time):
            return None
        original_color = resolve_color(point, None)
        if original_color is None:
            return None

        if point_index == start:
            target_color = start_color
        elif point_index == end:
            target_color = end_color
        else:
            if duration > 0.0:
                ratio = (
                    float(point_time) - float(start_time)
                ) / duration
            else:
                ratio = (point_index - start) / float(span)
            eased = _ease_value(ease, ratio)
            if eased is None:
                return None
            target_color = _round_color(
                _lerp_value(start_color, end_color, eased)
            )
        entries.append((point_index, target_color, original_color))

    changed = []
    try:
        for point_index, target_color, original_color in entries:
            if setLinePoint(
                chart,
                line_index,
                point_index,
                color=target_color,
            ) is None:
                raise RuntimeError("line point color set failed")
            changed.append((point_index, original_color))
    except Exception:
        for point_index, original_color in reversed(changed):
            try:
                setLinePoint(
                    chart,
                    line_index,
                    point_index,
                    color=original_color,
                )
            except Exception:
                pass
        return None
    return []


def setRingColorEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置判定环颜色缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _line_entries(chart, indexlist, getRingPoint)
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, line_index, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue
        start_color = list(selected["startColor"])
        end_color = list(selected["endColor"])

        def set_end(target: dict, color: list, line_index=line_index, point_index=point_index) -> bool:
            return setRingPoint(
                target,
                line_index,
                point_index,
                endcolor=color,
            ) is not None

        def add_color(
            target: dict,
            time: float,
            start: list,
            end: list,
            line_index=line_index,
        ) -> bool:
            return addRingPoint(target, line_index, time, start, end) is not None

        action = _color_node_action(
            float(selected["time"]),
            float(following["time"]),
            start_color,
            end_color,
            ease,
            precision,
            inserttype,
            set_end,
            add_color,
            lambda target, line_index=line_index: _ring_times(target, line_index),
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setLineColorEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置引导线线色缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _line_entries(chart, indexlist, getLineColor)
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, line_index, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue
        start_color = list(selected["startColor"])
        end_color = list(selected["endColor"])

        def set_end(target: dict, color: list, line_index=line_index, point_index=point_index) -> bool:
            return setLineColor(
                target,
                line_index,
                point_index,
                endcolor=color,
            ) is not None

        def add_color(
            target: dict,
            time: float,
            start: list,
            end: list,
            line_index=line_index,
        ) -> bool:
            return addLineColor(target, line_index, time, start, end) is not None

        action = _color_node_action(
            float(selected["time"]),
            float(following["time"]),
            start_color,
            end_color,
            ease,
            precision,
            inserttype,
            set_end,
            add_color,
            lambda target, line_index=line_index: _line_color_times(target, line_index),
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setCanvasPositionEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置画布位置缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _canvas_entries(chart, indexlist, getCanvasPosition)
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, canvas_index, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue

        def set_ease(target: dict, value: int, canvas_index=canvas_index, point_index=point_index) -> bool:
            return setCanvasPosition(
                target,
                canvas_index,
                point_index,
                easetype=value,
            ) is not None

        def add_value(
            target: dict,
            time: float,
            value: float,
            value_ease: int,
            u: float,
            canvas_index=canvas_index,
        ) -> bool:
            return addCanvasPosition(
                target,
                canvas_index,
                time,
                value,
                value_ease,
            ) is not None

        action = _position_action(
            float(selected["time"]),
            float(following["time"]),
            float(selected["value"]),
            float(following["value"]),
            ease,
            precision,
            inserttype,
            set_ease,
            add_value,
            lambda target, canvas_index=canvas_index: _canvas_position_times(target, canvas_index),
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setCanvasSpeedEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置画布流速缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _canvas_entries(chart, indexlist, getCanvasSpeed)
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, canvas_index, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue

        def add_value(
            target: dict,
            time: float,
            value: float,
            canvas_index=canvas_index,
        ) -> bool:
            return addCanvasSpeed(target, canvas_index, time, value) is not None

        action = _step_action(
            float(selected["time"]),
            float(following["time"]),
            float(selected["value"]),
            float(following["value"]),
            ease,
            precision,
            inserttype,
            add_value,
            lambda target, canvas_index=canvas_index: _canvas_speed_times(target, canvas_index),
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setCameraPositionEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置相机位置缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _flat_entries(chart, indexlist, lambda target: getCameraPosition(target, 0, -1))
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue

        def set_ease(target: dict, value: int, point_index=point_index) -> bool:
            return setCameraPosition(target, point_index, easetype=value) is not None

        def add_value(
            target: dict,
            time: float,
            value: float,
            value_ease: int,
            u: float,
        ) -> bool:
            return addCameraPosition(target, time, value, value_ease) is not None

        action = _position_action(
            float(selected["time"]),
            float(following["time"]),
            float(selected["value"]),
            float(following["value"]),
            ease,
            precision,
            inserttype,
            set_ease,
            add_value,
            _camera_position_times,
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setCameraScaleEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置相机缩放缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _flat_entries(chart, indexlist, lambda target: getCameraScale(target, 0, -1))
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue

        def set_ease(target: dict, value: int, point_index=point_index) -> bool:
            return setCameraScale(target, point_index, easetype=value) is not None

        def add_value(
            target: dict,
            time: float,
            value: float,
            value_ease: int,
            u: float,
        ) -> bool:
            return addCameraScale(target, time, value, value_ease) is not None

        action = _position_action(
            float(selected["time"]),
            float(following["time"]),
            float(selected["value"]),
            float(following["value"]),
            ease,
            precision,
            inserttype,
            set_ease,
            add_value,
            _camera_scale_times,
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed)


def setBpmShiftEase(
    chart: dict,
    indexlist: object,
    easetype: object,
    precision: object = 1,
    inserttype: str = "uniform",
    isFailAddAllowed: bool = False,
) -> list[int]:
    """设置 BPM 缓动。"""

    if not isinstance(chart, dict):
        return [-1]
    ease = _parse_ease(easetype)
    if ease is None or not _validate_common(inserttype, precision):
        return [-1]
    entries = _flat_entries(chart, indexlist, lambda target: getBpmShift(target, 0, -1))
    if entries is None:
        return [-1]
    if not entries:
        return []

    items = []
    for entry in entries:
        position, point_index, selected, following = entry
        if selected is None or following is None:
            items.append(_invalid_item(position))
            continue
        if float(following["time"]) <= float(selected["time"]):
            items.append(_invalid_item(position))
            continue

        def add_value(target: dict, time: float, value: float) -> bool:
            return addBpmShift(
                target,
                value,
                time,
                isDelayCalculate=True,
                isMultiply=True,
            ) is not None

        action = _step_action(
            float(selected["time"]),
            float(following["time"]),
            float(selected["value"]),
            float(following["value"]),
            ease,
            precision,
            inserttype,
            add_value,
            _bpm_times,
        )
        items.append(([position], action))

    return _run_ease_items(chart, items, isFailAddAllowed, post=_refresh_all)
