"""按几何形状绘制引导线的组合工具。"""

from __future__ import annotations

import copy
import math

from .base import refresh
from .chart import (
    addLine,
    createLinePoint,
    createRingPoint,
    deleteLine,
)
from .query import (
    getCanvasCount,
    getLine,
    getLineCount,
    getLinePosition,
)

__all__ = ["drawEllipse", "drawPolygon", "getClosedRegion"]

_EPS = 1e-9
_ANGLE_EPS = 1e-10
_RADIAL_JUMP_WIDTH = 1e-4
_RADIAL_SWITCH_INWARD_BIAS = 0.008


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _resolve_canvas(chart: dict, canvasindex: object) -> int | None:
    if not _is_int(canvasindex):
        return None
    count = getCanvasCount(chart)
    if not _is_int(count) or count <= 0:
        return None
    index = count + canvasindex if canvasindex < 0 else canvasindex
    if not 0 <= index < count:
        return None
    return index


def _normalize_color(color: object, canvas_index: int) -> list[int] | None:
    spec = createLinePoint(0.0, 0.0, canvas_index, 0, color)
    return None if spec is None else list(spec["color"])


def _round_color(values: list[float]) -> list[int]:
    return [
        max(0, min(255, int(math.floor(float(value) + 0.5))))
        for value in values
    ]


def _lerp_color(start: list[int], end: list[int], ratio: float) -> list[int]:
    return _round_color(
        [
            float(start[index])
            + (float(end[index]) - float(start[index])) * ratio
            for index in range(4)
        ]
    )


def _gradient_color(stops: list[tuple[float, list[int]]], value: float) -> list[int]:
    """按颜色节点采样；重复位置使用左端首个颜色，之后跳到右端颜色。"""

    value = max(0.0, min(1.0, float(value)))
    groups: list[tuple[float, list[list[int]]]] = []
    for position, color in stops:
        if groups and abs(position - groups[-1][0]) <= _ANGLE_EPS:
            groups[-1][1].append(color)
        else:
            groups.append((position, [color]))

    if value < groups[0][0] - _ANGLE_EPS:
        return list(groups[0][1][0])

    for index, (position, colors) in enumerate(groups):
        if abs(value - position) <= _ANGLE_EPS:
            return list(colors[0])
        if value < position:
            previous_position, previous_colors = groups[index - 1]
            span = position - previous_position
            ratio = 0.0 if span <= _ANGLE_EPS else (
                (value - previous_position) / span
            )
            return _lerp_color(previous_colors[-1], colors[0], ratio)

    return list(groups[-1][1][-1])


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _point_cross(origin: dict, left: dict, right: dict) -> float:
    return _cross(
        left["x"] - origin["x"],
        left["y"] - origin["y"],
        right["x"] - origin["x"],
        right["y"] - origin["y"],
    )


def _convex_hull(points: list[dict]) -> list[dict] | None:
    ordered = sorted(points, key=lambda point: (point["x"], point["y"]))
    if len(ordered) < 3:
        return None

    lower: list[dict] = []
    for point in ordered:
        while len(lower) >= 2 and _point_cross(lower[-2], lower[-1], point) <= _EPS:
            lower.pop()
        lower.append(point)

    upper: list[dict] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and _point_cross(upper[-2], upper[-1], point) <= _EPS:
            upper.pop()
        upper.append(point)

    hull = lower[:-1] + upper[:-1]
    return hull if len(hull) >= 3 else None


def _polygon_area(points: list[dict]) -> float:
    total = 0.0
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        total += point["x"] * following["y"] - following["x"] * point["y"]
    return total * 0.5


def _point_on_segment(
    start: tuple[float, float],
    end: tuple[float, float],
    point: tuple[float, float],
) -> bool:
    cross = _cross(
        end[0] - start[0],
        end[1] - start[1],
        point[0] - start[0],
        point[1] - start[1],
    )
    if abs(cross) > _EPS:
        return False
    return (
        min(start[0], end[0]) - _EPS <= point[0] <= max(start[0], end[0]) + _EPS
        and min(start[1], end[1]) - _EPS <= point[1] <= max(start[1], end[1]) + _EPS
    )


def _segments_intersect(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> bool:
    def orientation(a, b, c):
        return _cross(b[0] - a[0], b[1] - a[1], c[0] - a[0], c[1] - a[1])

    first = orientation(first_start, first_end, second_start)
    second = orientation(first_start, first_end, second_end)
    third = orientation(second_start, second_end, first_start)
    fourth = orientation(second_start, second_end, first_end)

    if (
        (first > _EPS and second < -_EPS) or (first < -_EPS and second > _EPS)
    ) and (
        (third > _EPS and fourth < -_EPS) or (third < -_EPS and fourth > _EPS)
    ):
        return True

    return (
        (abs(first) <= _EPS and _point_on_segment(first_start, first_end, second_start))
        or (abs(second) <= _EPS and _point_on_segment(first_start, first_end, second_end))
        or (abs(third) <= _EPS and _point_on_segment(second_start, second_end, first_start))
        or (abs(fourth) <= _EPS and _point_on_segment(second_start, second_end, first_end))
    )


def _is_simple_polygon(polygon: list[dict]) -> bool:
    count = len(polygon)
    if count < 3 or abs(_polygon_area(polygon)) <= _EPS:
        return False

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % count]
        if math.hypot(end["x"] - start["x"], end["y"] - start["y"]) <= _EPS:
            return False

    for first_index in range(count):
        first_start = (
            polygon[first_index]["x"],
            polygon[first_index]["y"],
        )
        first_end = (
            polygon[(first_index + 1) % count]["x"],
            polygon[(first_index + 1) % count]["y"],
        )
        for second_index in range(first_index + 1, count):
            if (
                second_index == first_index
                or second_index == (first_index + 1) % count
                or first_index == (second_index + 1) % count
            ):
                continue
            second_start = (
                polygon[second_index]["x"],
                polygon[second_index]["y"],
            )
            second_end = (
                polygon[(second_index + 1) % count]["x"],
                polygon[(second_index + 1) % count]["y"],
            )
            if _segments_intersect(first_start, first_end, second_start, second_end):
                return False
    return True


def _point_in_polygon(polygon: list[dict], point: dict) -> bool:
    return _point_in_polygon_with_boundary(polygon, point, True)


def _point_strictly_in_polygon(polygon: list[dict], point: dict) -> bool:
    return _point_in_polygon_with_boundary(polygon, point, False)


def _point_in_polygon_with_boundary(
    polygon: list[dict],
    point: dict,
    include_boundary: bool,
) -> bool:
    px = point["x"]
    py = point["y"]
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(
            (start["x"], start["y"]),
            (end["x"], end["y"]),
            (px, py),
        ):
            return include_boundary

    inside = False
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if (start["y"] > py) != (end["y"] > py):
            ratio = (py - start["y"]) / (end["y"] - start["y"])
            cross_x = start["x"] + (end["x"] - start["x"]) * ratio
            if cross_x > px:
                inside = not inside
    return inside


def _parse_polygon(pointlist: object, canvas_index: int) -> list[dict] | None:
    if not isinstance(pointlist, list) or len(pointlist) < 3:
        return None

    points = []
    seen = set()
    for item in pointlist:
        if not isinstance(item, dict):
            return None
        time = item.get("time")
        x_position = item.get("xPosition")
        if not _is_finite_number(time) or float(time) < 0.0:
            return None
        if not _is_finite_number(x_position):
            return None
        color_value = item.get("color")
        if isinstance(color_value, tuple):
            color_value = list(color_value)
        spec = createLinePoint(
            float(time),
            float(x_position),
            canvas_index,
            0,
            color_value,
        )
        if spec is None:
            return None
        key = (float(time), float(x_position))
        if key in seen:
            return None
        seen.add(key)
        points.append(
            {
                "x": float(x_position),
                "y": float(time),
                "color": list(spec["color"]),
            }
        )

    hull = _convex_hull(points)
    if hull is not None and len(hull) == len(points):
        if not _is_simple_polygon(hull):
            return None
        # Keep the caller's first vertex as the polygon start for boundary
        # sampling and stable border/fill ordering.
        anchor = (points[0]["x"], points[0]["y"])
        for index, point in enumerate(hull):
            if (point["x"], point["y"]) == anchor:
                hull = hull[index:] + hull[:index]
                break
        return hull

    # A concave polygon cannot be reconstructed from an unordered point set;
    # fall back to the caller's vertex order and require a simple polygon.
    if not _is_simple_polygon(points):
        return None
    return points


def _parse_color_entries(
    items: list,
    canvas_index: int,
) -> list[tuple[float, list[int]]] | None:
    if not items:
        return None

    pairs = []
    plain = []
    for item in items:
        if (
            isinstance(item, (list, tuple))
            and len(item) == 2
            and _is_finite_number(item[1])
            and isinstance(item[0], (str, list, tuple, dict))
        ):
            pairs.append((item[0], float(item[1])))
        else:
            plain.append(item)

    if pairs and plain:
        return None

    if pairs:
        stops = []
        previous = -math.inf
        for color_value, position in pairs:
            if not 0.0 <= position <= 1.0 or position < previous - _EPS:
                return None
            color = _normalize_color(
                list(color_value) if isinstance(color_value, tuple) else color_value,
                canvas_index,
            )
            if color is None:
                return None
            stops.append((position, color))
            previous = position
        return stops

    colors = []
    for value in plain:
        color = _normalize_color(
            list(value) if isinstance(value, tuple) else value,
            canvas_index,
        )
        if color is None:
            return None
        colors.append(color)

    if len(colors) == 1:
        return [(0.0, colors[0])]
    return [
        (index / (len(colors) - 1), color)
        for index, color in enumerate(colors)
    ]


def _border_layers(value: object) -> list[int] | None:
    if _is_int(value):
        if value >= 0:
            return list(range(0, value + 1))
        return list(range(value, 1))
    if isinstance(value, list):
        if not all(_is_int(item) for item in value):
            return None
        return sorted(set(value))
    return None


def _parse_angle(value: object) -> float | None:
    if not _is_finite_number(value):
        return None
    angle = float(value)
    if not 0.0 <= angle < 360.0:
        return None
    return angle


def _parse_center(x_value: object, y_value: object) -> dict | None:
    if not _is_finite_number(x_value) or not _is_finite_number(y_value):
        return None
    return {"x": float(x_value), "y": float(y_value)}


def _parse_fillerinfo(
    style: str,
    fillerinfo: object,
    canvas_index: int,
) -> dict | None:
    if not isinstance(fillerinfo, list):
        return None

    if style == "linear":
        if len(fillerinfo) < 2:
            return None
        angle = _parse_angle(fillerinfo[0])
        if angle is None:
            return None
        stops = _parse_color_entries(fillerinfo[1:], canvas_index)
        if stops is None:
            return None
        return {"style": style, "angle": angle, "stops": stops}

    if style in ("radial", "radialBorder"):
        if len(fillerinfo) < 3:
            return None
        center = _parse_center(fillerinfo[0], fillerinfo[1])
        if center is None:
            return None
        stops = _parse_color_entries(fillerinfo[2:], canvas_index)
        if stops is None:
            return None
        return {"style": style, "center": center, "stops": stops}

    if style in ("conic", "conicBorder"):
        if len(fillerinfo) < 4:
            return None
        center = _parse_center(fillerinfo[0], fillerinfo[1])
        angle = _parse_angle(fillerinfo[2])
        if center is None or angle is None:
            return None
        stops = _parse_color_entries(fillerinfo[3:], canvas_index)
        if stops is None:
            return None
        return {
            "style": style,
            "center": center,
            "angle": angle,
            "stops": stops,
        }

    return None


def _line_intersection(
    first_point: tuple[float, float],
    first_direction: tuple[float, float],
    second_point: tuple[float, float],
    second_direction: tuple[float, float],
) -> tuple[float, float] | None:
    denominator = _cross(
        first_direction[0],
        first_direction[1],
        second_direction[0],
        second_direction[1],
    )
    if abs(denominator) <= _EPS:
        return None
    dx = second_point[0] - first_point[0]
    dy = second_point[1] - first_point[1]
    ratio = _cross(dx, dy, second_direction[0], second_direction[1]) / denominator
    return (
        first_point[0] + first_direction[0] * ratio,
        first_point[1] + first_direction[1] * ratio,
    )


def _offset_polygon(polygon: list[dict], distance: float) -> list[tuple[float, float]] | None:
    if distance == 0.0:
        return [(point["x"], point["y"]) for point in polygon]

    area = _polygon_area(polygon)
    if abs(area) <= _EPS:
        return None

    offset_edges = []
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        dx = end["x"] - start["x"]
        dy = end["y"] - start["y"]
        length = math.hypot(dx, dy)
        if length <= _EPS:
            return None
        if area > 0.0:
            nx = dy / length
            ny = -dx / length
        else:
            nx = -dy / length
            ny = dx / length
        offset_edges.append(
            (
                (start["x"] + nx * distance, start["y"] + ny * distance),
                (dx, dy),
            )
        )

    result = []
    for index in range(len(offset_edges)):
        previous = offset_edges[index - 1]
        current = offset_edges[index]
        point = _line_intersection(
            previous[0],
            previous[1],
            current[0],
            current[1],
        )
        if point is None or not all(_is_finite_number(value) for value in point):
            return None
        result.append(point)

    result_points = [{"x": point[0], "y": point[1]} for point in result]
    original_area = _polygon_area(polygon)
    offset_area = _polygon_area(result_points)
    if abs(offset_area) <= _EPS:
        return None
    if (offset_area > 0.0) != (original_area > 0.0):
        return None
    if not _is_simple_polygon(result_points):
        return None
    return result


def _clip_line(
    polygon: list[dict],
    normal: tuple[float, float],
    direction: tuple[float, float],
    offset: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    origin = (normal[0] * offset, normal[1] * offset)
    hits = []
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        edge = (end["x"] - start["x"], end["y"] - start["y"])
        denominator = _cross(direction[0], direction[1], edge[0], edge[1])
        start_offset = (
            (start["x"] - origin[0]) * normal[0]
            + (start["y"] - origin[1]) * normal[1]
        )
        end_offset = (
            (end["x"] - origin[0]) * normal[0]
            + (end["y"] - origin[1]) * normal[1]
        )
        if abs(denominator) <= _EPS:
            if abs(start_offset) <= _EPS:
                hits.append((start["x"], start["y"]))
                hits.append((end["x"], end["y"]))
            continue
        ratio = -start_offset / (end_offset - start_offset)
        if -_EPS <= ratio <= 1.0 + _EPS:
            hits.append(
                (
                    start["x"] + edge[0] * ratio,
                    start["y"] + edge[1] * ratio,
                )
            )

    unique = []
    for point in hits:
        if all(
            (point[0] - other[0]) ** 2 + (point[1] - other[1]) ** 2 > _EPS * _EPS
            for other in unique
        ):
            unique.append(point)
    if len(unique) < 2:
        return None

    projections = [
        (point[0] * direction[0] + point[1] * direction[1], point)
        for point in unique
    ]
    projections.sort(key=lambda item: item[0])
    start = projections[0][1]
    end = projections[-1][1]
    if math.hypot(end[0] - start[0], end[1] - start[1]) <= _EPS:
        return None
    return start, end


def _line_intervals(
    polygon: list[dict],
    origin: tuple[float, float],
    direction: tuple[float, float],
    start_t: float | None = None,
    end_t: float | None = None,
) -> list[tuple[float, float]]:
    events = []
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        edge = (end["x"] - start["x"], end["y"] - start["y"])
        ax = start["x"] - origin[0]
        ay = start["y"] - origin[1]
        denominator = _cross(direction[0], direction[1], edge[0], edge[1])
        if abs(denominator) <= _EPS:
            if abs(_cross(ax, ay, direction[0], direction[1])) <= _EPS:
                events.append(ax * direction[0] + ay * direction[1])
                events.append(
                    (end["x"] - origin[0]) * direction[0]
                    + (end["y"] - origin[1]) * direction[1]
                )
            continue
        distance = _cross(ax, ay, edge[0], edge[1]) / denominator
        edge_ratio = _cross(ax, ay, direction[0], direction[1]) / denominator
        if -_EPS <= edge_ratio <= 1.0 + _EPS:
            events.append(distance)

    if start_t is not None:
        events.append(start_t)
    if end_t is not None:
        events.append(end_t)

    events.sort()
    unique = []
    for value in events:
        if not unique or abs(value - unique[-1]) > _EPS:
            unique.append(value)

    intervals = []
    for left, right in zip(unique, unique[1:]):
        if right - left <= _EPS:
            continue
        if start_t is not None and right <= start_t + _EPS:
            continue
        if end_t is not None and left >= end_t - _EPS:
            continue
        middle = (left + right) * 0.5
        point = {
            "x": origin[0] + direction[0] * middle,
            "y": origin[1] + direction[1] * middle,
        }
        if _point_in_polygon(polygon, point):
            intervals.append((left, right))
    return intervals


def _transparent_color(color: list[int]) -> list[int]:
    return [color[0], color[1], color[2], 0]


def _build_gapped_line(
    canvas_index: int,
    origin: tuple[float, float],
    direction: tuple[float, float],
    intervals: list[tuple[float, float]],
    color_at,
    extra_positions: list[float] | None = None,
) -> list[dict] | None:
    if not intervals:
        return None

    records = []
    for index, (start, end) in enumerate(intervals):
        if end - start <= _EPS:
            continue
        records.append((start, color_at(start)))
        if extra_positions:
            for position in extra_positions:
                if start + _EPS < position < end - _EPS:
                    records.append((position, color_at(position)))
        records.append((end, color_at(end)))
        if index + 1 < len(intervals):
            next_start = intervals[index + 1][0]
            if next_start - end > _EPS:
                records.append((end, _transparent_color(color_at(end))))
                records.append(
                    (next_start, _transparent_color(color_at(next_start)))
                )

    # addLine() performs a stable sort by time. If the line runs toward
    # decreasing time, build the records in time order ourselves so that
    # same-time visible/transparent pairs are not left in the wrong order.
    if direction[1] < -_EPS:
        records.reverse()

    points = []
    for distance, color in records:
        point = _make_point(
            canvas_index,
            origin[1] + direction[1] * distance,
            origin[0] + direction[0] * distance,
            color,
        )
        if point is None:
            return None
        points.append(point)
    return points if len(points) >= 2 else None


def _ray_boundary(
    polygon: list[dict],
    origin: tuple[float, float],
    direction: tuple[float, float],
) -> tuple[float, float] | None:
    best = None
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        edge = (end["x"] - start["x"], end["y"] - start["y"])
        denominator = _cross(direction[0], direction[1], edge[0], edge[1])
        if abs(denominator) <= _EPS:
            continue
        ax = start["x"] - origin[0]
        ay = start["y"] - origin[1]
        distance = _cross(ax, ay, edge[0], edge[1]) / denominator
        edge_ratio = _cross(ax, ay, direction[0], direction[1]) / denominator
        if distance > _EPS and -_EPS <= edge_ratio <= 1.0 + _EPS:
            point = (
                origin[0] + direction[0] * distance,
                origin[1] + direction[1] * distance,
            )
            if best is None or distance > best[0]:
                best = (distance, point)
    return None if best is None else best[1]


def _make_point(
    canvas_index: int,
    time: float,
    x_position: float,
    color: list[int],
) -> dict | None:
    return createLinePoint(
        float(time),
        float(x_position),
        canvas_index,
        0,
        color,
    )


def _build_fill_linear(
    polygon: list[dict],
    canvas_index: int,
    angle: float,
    stops: list[tuple[float, list[int]]],
    precision: float,
) -> list[list[dict]] | None:
    theta = math.radians(angle)
    normal = (math.cos(theta), math.sin(theta))
    direction = (-math.sin(theta), math.cos(theta))
    projections = [
        point["x"] * normal[0] + point["y"] * normal[1]
        for point in polygon
    ]
    minimum = min(projections)
    maximum = max(projections)
    span = maximum - minimum
    if span <= _EPS:
        return []

    lines = []
    offset = minimum
    while offset <= maximum + _EPS:
        origin = (normal[0] * offset, normal[1] * offset)
        intervals = _line_intervals(polygon, origin, direction)
        if intervals:
            ratio = (offset - minimum) / span
            color = _gradient_color(stops, ratio)
            points = _build_gapped_line(
                canvas_index,
                origin,
                direction,
                intervals,
                lambda distance, color=color: color,
            )
            if points is None:
                return None
            lines.append(points)
        offset += precision
    return lines


def _perimeter(polygon: list[dict]) -> float:
    total = 0.0
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        total += math.hypot(end["x"] - start["x"], end["y"] - start["y"])
    return total


def _boundary_at_distance(
    polygon: list[dict],
    distance: float,
) -> tuple[float, float]:
    remaining = float(distance)
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        length = math.hypot(end["x"] - start["x"], end["y"] - start["y"])
        if length <= _EPS:
            continue
        if remaining <= length + _EPS:
            ratio = max(0.0, min(1.0, remaining / length))
            return (
                start["x"] + (end["x"] - start["x"]) * ratio,
                start["y"] + (end["y"] - start["y"]) * ratio,
            )
        remaining -= length
    first = polygon[0]
    return first["x"], first["y"]


def _boundary_samples(
    polygon: list[dict],
    precision: float,
) -> list[tuple[float, float]]:
    total = _perimeter(polygon)
    if total <= _EPS:
        return []
    first = polygon[0]
    samples = [(first["x"], first["y"])]
    distance = 0.0
    while distance + precision < total - _EPS:
        distance += precision
        samples.append(_boundary_at_distance(polygon, distance))
    return samples


def _scaled_distance(
    dx: float,
    dy: float,
    timemultiple: float,
) -> float:
    """按 timemultiple 缩放时间方向后计算视觉距离。"""
    return math.hypot(dx, dy * timemultiple)


def _angle_from_center(
    center: tuple[float, float],
    point: tuple[float, float],
    timemultiple: float = 1.0,
) -> float:
    angle = math.atan2(
        point[0] - center[0],
        -(point[1] - center[1]) * timemultiple,
    )
    return angle % (2.0 * math.pi)


def _radial_points(
    center: tuple[float, float],
    boundary: tuple[float, float],
    max_distance: float,
    max_scaled_distance: float,
    stops: list[tuple[float, list[int]]],
    timemultiple: float = 1.0,
) -> list[dict] | None:
    dx = boundary[0] - center[0]
    dy = boundary[1] - center[1]
    distance = math.hypot(dx, dy)
    scaled_distance = _scaled_distance(dx, dy, timemultiple)
    if (
        distance <= _EPS
        or max_distance <= _EPS
        or max_scaled_distance <= _EPS
    ):
        return None
    distance_scale = scaled_distance / distance
    boundary_value = min(1.0, distance / max_distance)

    def color_at_position(position: float) -> list[int]:
        normalized = min(
            1.0,
            max(
                0.0,
                position * max_distance * distance_scale
                / max_scaled_distance,
            ),
        )
        return _gradient_color(stops, normalized)

    groups: list[tuple[float, list[list[int]]]] = []
    for position, color in stops:
        if groups and abs(position - groups[-1][0]) <= _ANGLE_EPS:
            groups[-1][1].append(list(color))
        else:
            groups.append((position, [list(color)]))

    nodes = [(0.0, center[0], center[1], _gradient_color(stops, 0.0))]
    for position, colors in groups:
        if 0.0 < position < boundary_value - _ANGLE_EPS:
            count = len(colors)
            center_position = position
            if count > 1 and boundary[1] < center[1] - _ANGLE_EPS:
                # 同一位置的颜色节点如果完全重合，addLine() 按 time 排序后，
                # 射线朝时间减小的方向时颜色切换点会偏到一侧。只对这一侧
                # 把重复颜色展开到极小的径向区间、保持第一个颜色靠近中心，
                # 并补偿编辑器/游戏渲染中突变点向外约 0.008 的偏移。
                center_position -= _RADIAL_SWITCH_INWARD_BIAS / max_distance
                if not 0.0 < center_position < boundary_value:
                    continue
                offsets = [
                    (index - (count - 1) * 0.5) * _RADIAL_JUMP_WIDTH
                    for index in range(count)
                ]
            else:
                offsets = [0.0] * count
            for _, offset in zip(colors, offsets):
                node_position = center_position + offset
                if not 0.0 < node_position < boundary_value:
                    continue
                ratio = node_position / boundary_value
                # 几何节点位置保持原坐标；timemultiple 只改变颜色采样。
                nodes.append(
                    (
                        node_position,
                        center[0] + dx * ratio,
                        center[1] + dy * ratio,
                        color_at_position(node_position),
                    )
                )
    nodes.append(
        (
            boundary_value,
            boundary[0],
            boundary[1],
            color_at_position(boundary_value),
        )
    )
    nodes.sort(key=lambda item: item[0])
    return [
        {"time": y, "xPosition": x, "color": color}
        for _, x, y, color in nodes
    ]


def _build_fill_radial_conic(
    polygon: list[dict],
    canvas_index: int,
    filler: dict,
    precision: float,
    timemultiple: float = 1.0,
) -> list[list[dict]] | None:
    center = (filler["center"]["x"], filler["center"]["y"])
    if not _point_in_polygon(polygon, {"x": center[0], "y": center[1]}):
        return None
    max_distance = max(
        math.hypot(point["x"] - center[0], point["y"] - center[1])
        for point in polygon
    )
    max_scaled_distance = max(
        _scaled_distance(
            point["x"] - center[0],
            point["y"] - center[1],
            timemultiple,
        )
        for point in polygon
    )
    if (
        max_distance <= _EPS
        or max_scaled_distance <= _EPS
        or not math.isfinite(max_scaled_distance)
    ):
        return None

    style = filler["style"]
    is_radial = style in ("radial", "radialBorder")
    is_border_sampled = style in ("radialBorder", "conicBorder")
    base_angle = (
        math.radians(filler["angle"])
        if style in ("conic", "conicBorder")
        else 0.0
    )

    boundaries: list[tuple[float, float]] = []
    if is_border_sampled:
        boundaries = _boundary_samples(polygon, precision)
    else:
        step = 2.0 * math.pi * precision
        count = max(1, int(math.ceil((2.0 * math.pi - _ANGLE_EPS) / step)))
        for index in range(count):
            angle = base_angle + index * step
            direction = (math.sin(angle), -math.cos(angle))
            boundary = _ray_boundary(polygon, center, direction)
            if boundary is not None:
                boundaries.append(boundary)

    lines = []
    for boundary in boundaries:
        dx = boundary[0] - center[0]
        dy = boundary[1] - center[1]
        distance = math.hypot(dx, dy)
        if distance <= _EPS:
            continue
        direction = (dx / distance, dy / distance)
        intervals = _line_intervals(
            polygon,
            center,
            direction,
            start_t=0.0,
            end_t=distance,
        )
        if not intervals:
            continue

        if is_radial:
            if len(intervals) == 1:
                raw_points = _radial_points(
                    center,
                    boundary,
                    max_distance,
                    max_scaled_distance,
                    filler["stops"],
                    timemultiple,
                )
                if raw_points is None:
                    continue
                points = []
                for item in raw_points:
                    point = _make_point(
                        canvas_index,
                        item["time"],
                        item["xPosition"],
                        item["color"],
                    )
                    if point is None:
                        return None
                    points.append(point)
            else:
                distance_scale = _scaled_distance(
                    direction[0],
                    direction[1],
                    timemultiple,
                )
                if distance_scale <= _EPS:
                    continue

                def radial_color(distance_value: float) -> list[int]:
                    return _gradient_color(
                        filler["stops"],
                        min(
                            1.0,
                            max(
                                0.0,
                                distance_value * distance_scale
                                / max_scaled_distance,
                            ),
                        ),
                    )

                extra_positions = [
                    position * max_distance
                    for position, _ in filler["stops"]
                ]
                points = _build_gapped_line(
                    canvas_index,
                    center,
                    direction,
                    intervals,
                    radial_color,
                    extra_positions,
                )
                if points is None:
                    return None
        else:
            angle = _angle_from_center(center, boundary, timemultiple)
            fraction = ((angle - base_angle) % (2.0 * math.pi)) / (2.0 * math.pi)
            color = _gradient_color(filler["stops"], fraction)
            points = _build_gapped_line(
                canvas_index,
                center,
                direction,
                intervals,
                lambda distance_value, color=color: color,
            )
            if points is None:
                return None

        if len(points) >= 2:
            lines.append(points)
    return lines


def _build_border(
    polygon: list[dict],
    canvas_index: int,
    layers: list[int],
    precision: float,
) -> list[list[dict]] | None:
    requested = set(layers)
    if not requested:
        return []

    layer_points_map: dict[int, list[tuple[float, float]]] = {}
    if 0 in requested:
        layer_points_map[0] = [
            (point["x"], point["y"])
            for point in polygon
        ]

    # 从靠近原边界的层开始向两侧处理；某一层退化后，跳过同方向更远的层。
    negative_layers = sorted(
        (layer for layer in requested if layer < 0),
        reverse=True,
    )
    for layer in negative_layers:
        layer_points = _offset_polygon(polygon, layer * precision)
        if layer_points is None:
            break
        layer_points_map[layer] = layer_points

    positive_layers = sorted(layer for layer in requested if layer > 0)
    for layer in positive_layers:
        layer_points = _offset_polygon(polygon, layer * precision)
        if layer_points is None:
            break
        if any(point[1] < -_EPS for point in layer_points):
            break
        layer_points_map[layer] = layer_points

    lines = []
    for layer in sorted(layer_points_map):
        layer_points = layer_points_map[layer]
        for index, start in enumerate(layer_points):
            end = layer_points[(index + 1) % len(layer_points)]
            start_color = polygon[index]["color"]
            end_color = polygon[(index + 1) % len(polygon)]["color"]
            start_spec = _make_point(
                canvas_index,
                start[1],
                start[0],
                start_color,
            )
            end_spec = _make_point(
                canvas_index,
                end[1],
                end[0],
                end_color,
            )
            if start_spec is None or end_spec is None:
                return None
            if (
                abs(start[0] - end[0]) <= _EPS
                and abs(start[1] - end[1]) <= _EPS
            ):
                return None
            lines.append([start_spec, end_spec])
    return lines


def _add_lines(
    chart: dict,
    line_groups: list[list[dict]],
    ring: dict,
) -> list[int] | None:
    created = []
    for points in line_groups:
        index = addLine(
            chart,
            points,
            ring,
            isDelayCalculate=True,
        )
        if index is None:
            _delete_created(chart, created)
            return None
        created.append(index)
    return created


def _delete_created(chart: dict, indexes: list[int]) -> None:
    for index in reversed(indexes):
        deleteLine(chart, index)


def _commit(chart: dict, line_groups: list[list[dict]]) -> list[int] | None:
    ring = createRingPoint(0.0, "#00000000")
    if ring is None:
        return None

    work = copy.deepcopy(chart)
    if _add_lines(work, line_groups, ring) is None:
        return None
    if refresh(work, mode="all", type="all") is None:
        return None

    created = _add_lines(chart, line_groups, ring)
    if created is None:
        return None
    if refresh(chart, mode="all", type="all") is None:
        _delete_created(chart, created)
        return None
    return created


def drawPolygon(
    chart: dict,
    canvasindex: int,
    pointlist: list,
    isDrawBorder: bool,
    isFillGraph: bool,
    precision: float = 0.005,
    bordersize: int | list = [1],
    fillerstyle: str = "linear",
    fillerinfo: list | None = None,
    holelist: list | None = None,
    holecolor: list | str = [0, 0, 0, 0],
    timemultiple: float = 1.65,
) -> list[int] | None:
    """在指定画布绘制凸多边形或简单凹多边形，可带填充孔洞，返回新线索引。"""

    if not isinstance(chart, dict):
        return None
    if not isinstance(isDrawBorder, bool) or not isinstance(isFillGraph, bool):
        return None
    if not _is_finite_number(precision) or float(precision) <= 0.0:
        return None
    if not _is_finite_number(timemultiple) or float(timemultiple) <= 0.0:
        return None
    border_layers = _border_layers(bordersize)
    if border_layers is None:
        return None
    canvas_index = _resolve_canvas(chart, canvasindex)
    if canvas_index is None:
        return None
    polygon = _parse_polygon(pointlist, canvas_index)
    if polygon is None:
        return None

    if not isDrawBorder and not isFillGraph:
        return []

    line_groups = []
    if isFillGraph:
        if fillerstyle not in (
            "linear",
            "radial",
            "conic",
            "radialBorder",
            "conicBorder",
        ):
            return None
        if fillerinfo is None:
            return None
        filler = _parse_fillerinfo(
            fillerstyle,
            fillerinfo,
            canvas_index,
        )
        if filler is None:
            return None
        holes = _parse_holelist(holelist, canvas_index)
        if holes is None:
            return None
        hole_color = None
        if holes:
            hole_color = _normalize_color(holecolor, canvas_index)
            if hole_color is None:
                return None

        if fillerstyle == "linear":
            fill_lines = _build_fill_linear(
                polygon,
                canvas_index,
                filler["angle"],
                filler["stops"],
                float(precision),
            )
        else:
            if not _point_in_polygon(
                polygon,
                {
                    "x": filler["center"]["x"],
                    "y": filler["center"]["y"],
                },
            ):
                return None
            fill_lines = _build_fill_radial_conic(
                polygon,
                canvas_index,
                filler,
                float(precision),
                float(timemultiple),
            )
        if fill_lines is None:
            return None
        if holes:
            fill_lines = _mask_fill_lines(
                fill_lines,
                holes,
                hole_color,
                canvas_index,
            )
            if fill_lines is None:
                return None
        line_groups.extend(fill_lines)

    if isDrawBorder and border_layers:
        border_lines = _build_border(
            polygon,
            canvas_index,
            border_layers,
            float(precision),
        )
        if border_lines is None:
            return None
        line_groups.extend(border_lines)

    if not line_groups:
        return []
    return _commit(chart, line_groups)


def _make_point_ease(
    canvas_index: int,
    time: float,
    x_position: float,
    ease_type: int,
    color: list[int],
) -> dict | None:
    return createLinePoint(
        float(time),
        float(x_position),
        canvas_index,
        ease_type,
        color,
    )


def _rotate_xy(x: float, y: float, angle: float) -> tuple[float, float]:
    radians = math.radians(angle)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    return (
        x * cosine + y * sine,
        -x * sine + y * cosine,
    )


def _ellipse_point(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
    parameter: float,
) -> tuple[float, float]:
    x = x_length * math.cos(parameter)
    y = y_length * math.sin(parameter)
    dx, dy = _rotate_xy(x, y, angle)
    return center[0] + dx, center[1] + dy


def _ellipse_vertices(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
) -> list[dict]:
    local = [
        ("top", 0.0, y_length),
        ("right", x_length, 0.0),
        ("bottom", 0.0, -y_length),
        ("left", -x_length, 0.0),
    ]
    result = []
    for label, x, y in local:
        dx, dy = _rotate_xy(x, y, angle)
        result.append(
            {
                "label": label,
                "x": center[0] + dx,
                "y": center[1] + dy,
            }
        )
    return result


def _ellipse_color(colors: list[list[int]], parameter: float) -> list[int]:
    value = ((math.pi * 0.5 - parameter) % (2.0 * math.pi)) / (2.0 * math.pi)
    stops = [
        (0.0, colors[0]),
        (0.25, colors[1]),
        (0.5, colors[2]),
        (0.75, colors[3]),
        (1.0, colors[0]),
    ]
    return _gradient_color(stops, value)


def _ellipse_low_high(a: float, b: float, angle: float) -> tuple[float, float]:
    radians = math.radians(angle)
    sine = math.sin(radians)
    cosine = math.cos(radians)
    phase = math.atan2(-a * sine, b * cosine)
    low = (1.5 * math.pi - phase) % (2.0 * math.pi)
    high = (0.5 * math.pi - phase) % (2.0 * math.pi)
    return low, high


def _ellipse_arcs(a: float, b: float, angle: float) -> list[tuple[float, float]]:
    low, high = _ellipse_low_high(a, b, angle)
    if high > low:
        return [(low, high), (low, high - 2.0 * math.pi)]
    return [(low, high + 2.0 * math.pi), (low, high)]


def _ellipse_arc_s(
    parameter: float,
    start: float,
    end: float,
) -> float | None:
    low = min(start, end)
    high = max(start, end)
    for offset in range(-2, 3):
        candidate = parameter + 2.0 * math.pi * offset
        if low - _EPS <= candidate <= high + _EPS:
            return (candidate - start) / (end - start)
    return None


def _ellipse_count_samples(
    target: int,
    point_function,
    mode: str,
) -> list[float]:
    if target <= 1:
        return [0.5]
    if target == 2:
        return [0.0, 1.0]
    if mode == "uniform" or point_function is None:
        return [index / (target - 1) for index in range(target)]

    steps = 512
    points = [point_function(index / steps) for index in range(steps + 1)]
    if mode == "arc":
        weights = [
            math.hypot(
                points[index][0] - points[index - 1][0],
                points[index][1] - points[index - 1][1],
            )
            for index in range(1, len(points))
        ]
    else:
        weights = [0.0] * len(points)
        for index in range(1, len(points) - 1):
            second_x = (
                points[index - 1][0]
                - 2.0 * points[index][0]
                + points[index + 1][0]
            )
            second_y = (
                points[index - 1][1]
                - 2.0 * points[index][1]
                + points[index + 1][1]
            )
            weights[index] = math.hypot(second_x, second_y)

    cumulative = [0.0]
    for weight in weights[1:]:
        cumulative.append(cumulative[-1] + weight)
    total = cumulative[-1]
    if total <= _EPS:
        return [index / (target - 1) for index in range(target)]

    result = []
    cursor = 0
    for index in range(target):
        fraction = index / (target - 1)
        goal = total * fraction
        while cursor + 1 < len(cumulative) and cumulative[cursor + 1] < goal:
            cursor += 1
        before = cumulative[cursor]
        after = cumulative[cursor + 1] if cursor + 1 < len(cumulative) else before
        if after - before <= _EPS:
            value = cursor / (len(cumulative) - 1)
        else:
            ratio = (goal - before) / (after - before)
            value = (cursor + ratio) / (len(cumulative) - 1)
        result.append(max(0.0, min(1.0, value)))
    return result


def _ellipse_force_mandatory(
    values: list[float],
    mandatory: list[float],
    target: int,
) -> list[float]:
    selected = []
    for value in sorted(values):
        if not selected or abs(value - selected[-1]) > _EPS:
            selected.append(float(value))
    required = []
    for value in sorted(mandatory):
        if not required or abs(value - required[-1]) > _EPS:
            required.append(float(value))
    if len(required) >= target:
        return required
    for value in required:
        if any(abs(value - item) <= _EPS for item in selected):
            continue
        replace_index = None
        replace_distance = math.inf
        for index, item in enumerate(selected):
            if any(abs(item - required_value) <= _EPS for required_value in required):
                continue
            distance = abs(item - value)
            if distance < replace_distance:
                replace_distance = distance
                replace_index = index
        if replace_index is None:
            selected.append(value)
        else:
            selected[replace_index] = value
    selected = sorted(set(selected))
    while len(selected) < target:
        extended = [0.0] + selected + [1.0]
        best_gap = -1.0
        best_middle = 0.0
        for left, right in zip(extended, extended[1:]):
            gap = right - left
            if gap > best_gap:
                best_gap = gap
                best_middle = (left + right) * 0.5
        if best_gap <= _EPS:
            break
        selected.append(best_middle)
        selected.sort()
    return selected


def _sample_arc_s(
    inserttype: str,
    precision: object,
    mandatory: list[float],
    point_function=None,
) -> list[float] | None:
    values = []
    for value in sorted(mandatory):
        if not values or abs(value - values[-1]) > _EPS:
            values.append(float(value))
    if inserttype in ("uniform", "arc", "curvature"):
        target = int(precision)
        sampled = _ellipse_count_samples(target, point_function, inserttype)
        return _ellipse_force_mandatory(sampled, values, target)
    return None


def _ellipse_arc_mandatory(
    start: float,
    end: float,
    vertex_params: list[float],
) -> list[float]:
    values = [0.0, 1.0]
    for parameter in vertex_params:
        value = _ellipse_arc_s(parameter, start, end)
        if value is not None:
            if value < _EPS:
                value = 0.0
            elif value > 1.0 - _EPS:
                value = 1.0
            values.append(float(value))
    unique = []
    for value in sorted(values):
        if not unique or abs(value - unique[-1]) > _EPS:
            unique.append(value)
    return unique


def _ellipse_adaptive_s(
    start: float,
    end: float,
    point_function,
    tolerance: float,
    mandatory: list[float],
) -> list[float]:
    values = list(sorted(set(float(item) for item in mandatory)))
    insertions = [0]

    def subdivide(left: float, right: float, depth: int) -> None:
        if depth >= 14 or insertions[0] >= 4096:
            return
        middle = (left + right) * 0.5
        left_point = point_function(left)
        right_point = point_function(right)
        middle_point = point_function(middle)
        chord = math.hypot(
            right_point[0] - left_point[0],
            right_point[1] - left_point[1],
        )
        if chord <= _EPS:
            return
        cross_value = abs(
            (right_point[0] - left_point[0])
            * (middle_point[1] - left_point[1])
            - (right_point[1] - left_point[1])
            * (middle_point[0] - left_point[0])
        )
        if cross_value / chord <= tolerance:
            return
        subdivide(left, middle, depth + 1)
        if insertions[0] >= 4096:
            return
        values.append(middle)
        insertions[0] += 1
        subdivide(middle, right, depth + 1)

    for left, right in zip(values[:], values[1:]):
        subdivide(left, right, 0)
    return sorted(set(values))


def _ellipse_tick_values(value: float) -> list[int]:
    tick = int(math.floor(value))
    result = [tick]
    if value == float(tick) and tick > 0:
        result.append(tick - 1)
    return result


def _ellipse_limit_tick(
    parameters: list[float],
    point_function,
    mandatory_s: list[float],
) -> list[float]:
    counts: dict[int, int] = {}
    mandatory = set(mandatory_s)
    result = []
    for value in sorted(mandatory):
        point = point_function(value)
        for tick in _ellipse_tick_values(point[1]):
            counts[tick] = counts.get(tick, 0) + 1
        result.append(value)
    for value in sorted(parameters):
        if value in mandatory:
            continue
        point = point_function(value)
        ticks = _ellipse_tick_values(point[1])
        if all(counts.get(tick, 0) < 48 for tick in ticks):
            result.append(value)
            for tick in ticks:
                counts[tick] = counts.get(tick, 0) + 1
    return sorted(set(result))


def _ellipse_border_layers_valid(
    x_length: float,
    y_length: float,
    layers: list[int],
    precision: float,
) -> list[tuple[int, float, float]]:
    result = []
    negative = sorted((layer for layer in layers if layer < 0), reverse=True)
    for layer in negative:
        a = x_length + layer * precision
        b = y_length + layer * precision
        if a <= _EPS or b <= _EPS:
            break
        result.append((layer, a, b))
    for layer in sorted(layer for layer in layers if layer >= 0):
        a = x_length + layer * precision
        b = y_length + layer * precision
        if a <= _EPS or b <= _EPS:
            break
        result.append((layer, a, b))
    return sorted(result, key=lambda item: item[0])


def _build_ellipse_border_90(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
    layers: list[int],
    precision: float,
    canvas_index: int,
    colors: list[list[int]],
) -> list[list[dict]] | None:
    color_by_label = {
        "top": colors[0],
        "right": colors[1],
        "bottom": colors[2],
        "left": colors[3],
    }
    lines = []
    for _, a, b in _ellipse_border_layers_valid(
        x_length,
        y_length,
        layers,
        precision,
    ):
        vertices = _ellipse_vertices(center, a, b, angle)
        ordered = sorted(vertices, key=lambda item: (item["y"], item["x"]))
        low = ordered[0]
        high = ordered[-1]
        middle = sorted(ordered[1:-1], key=lambda item: item["x"])
        for item in middle:
            specs = []
            for point in (low, item):
                spec = _make_point_ease(
                    canvas_index,
                    point["y"],
                    point["x"],
                    16,
                    color_by_label[point["label"]],
                )
                if spec is None:
                    return None
                specs.append(spec)
            lines.append(specs)
        for item in middle:
            specs = []
            for point in (item, high):
                spec = _make_point_ease(
                    canvas_index,
                    point["y"],
                    point["x"],
                    15,
                    color_by_label[point["label"]],
                )
                if spec is None:
                    return None
                specs.append(spec)
            lines.append(specs)
    return lines


def _build_ellipse_border_curved(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
    layers: list[int],
    precision: float,
    canvas_index: int,
    colors: list[list[int]],
    inserttype: str,
    insertprecision: object,
) -> list[list[dict]] | None:
    vertex_params = [
        math.pi * 0.5,
        0.0,
        1.5 * math.pi,
        math.pi,
    ]
    lines = []
    for _, a, b in _ellipse_border_layers_valid(
        x_length,
        y_length,
        layers,
        precision,
    ):
        arcs = _ellipse_arcs(a, b, angle)
        arcs.sort(
            key=lambda arc: _ellipse_point(
                center,
                a,
                b,
                angle,
                (arc[0] + arc[1]) * 0.5,
            )[0]
        )
        for start, end in arcs:
            def point_at(value: float, start=start, end=end, a=a, b=b):
                return _ellipse_point(
                    center,
                    a,
                    b,
                    angle,
                    start + (end - start) * value,
                )

            mandatory = _ellipse_arc_mandatory(start, end, vertex_params)
            parameters = _sample_arc_s(
                inserttype,
                insertprecision,
                mandatory,
                point_at,
            )
            if parameters is None:
                parameters = _ellipse_adaptive_s(
                    start,
                    end,
                    point_at,
                    float(insertprecision),
                    mandatory,
                )
                parameters = _ellipse_limit_tick(parameters, point_at, mandatory)
            specs = []
            for value in parameters:
                parameter = start + (end - start) * value
                x_position, time = point_at(value)
                spec = _make_point(
                    canvas_index,
                    time,
                    x_position,
                    _ellipse_color(colors, parameter),
                )
                if spec is None:
                    return None
                specs.append(spec)
            if len(specs) < 2:
                return None
            lines.append(specs)
    return lines


def _ellipse_polygon(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
    start_parameter: float = 0.0,
    count: int = 2048,
    reverse: bool = False,
) -> list[dict]:
    points = []
    direction = -1.0 if reverse else 1.0
    for index in range(count):
        parameter = (
            start_parameter
            + direction * 2.0 * math.pi * index / count
        )
        x_position, time = _ellipse_point(
            center,
            x_length,
            y_length,
            angle,
            parameter,
        )
        points.append({"x": x_position, "y": time})
    return points


def _ellipse_ray_parameter(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
    origin: tuple[float, float],
    direction: tuple[float, float],
) -> float | None:
    ox = origin[0] - center[0]
    oy = origin[1] - center[1]
    ox, oy = _rotate_xy(ox, oy, -angle)
    dx, dy = _rotate_xy(direction[0], direction[1], -angle)

    qa = (dx * dx) / (x_length * x_length) + (dy * dy) / (y_length * y_length)
    qb = 2.0 * (
        ox * dx / (x_length * x_length)
        + oy * dy / (y_length * y_length)
    )
    qc = (
        ox * ox / (x_length * x_length)
        + oy * oy / (y_length * y_length)
        - 1.0
    )
    if qa <= _EPS:
        return None
    discriminant = qb * qb - 4.0 * qa * qc
    if discriminant < -_EPS:
        return None
    discriminant = max(0.0, discriminant)
    root = math.sqrt(discriminant)
    candidates = [
        (-qb - root) / (2.0 * qa),
        (-qb + root) / (2.0 * qa),
    ]
    positive = [value for value in candidates if value > _EPS]
    if positive:
        distance = min(positive)
    else:
        positive = [value for value in candidates if value >= -_EPS]
        if not positive:
            return None
        distance = max(positive)
    px = ox + dx * distance
    py = oy + dy * distance
    return math.atan2(py / y_length, px / x_length) % (2.0 * math.pi)


def _build_ellipse_conic_border_fill(
    polygon: list[dict],
    canvas_index: int,
    center: tuple[float, float],
    base_angle: float,
    stops: list[tuple[float, list[int]]],
    precision: float,
) -> list[list[dict]] | None:
    boundaries = _boundary_samples(polygon, precision)
    lines = []
    for boundary in boundaries:
        dx = boundary[0] - center[0]
        dy = boundary[1] - center[1]
        distance = math.hypot(dx, dy)
        if distance <= _EPS:
            continue
        direction = (dx / distance, dy / distance)
        intervals = _line_intervals(
            polygon,
            center,
            direction,
            start_t=0.0,
            end_t=distance,
        )
        if not intervals:
            continue
        angle_value = math.atan2(dx, dy) % (2.0 * math.pi)
        fraction = (
            (angle_value - base_angle) % (2.0 * math.pi)
        ) / (2.0 * math.pi)
        color = _gradient_color(stops, fraction)
        points = _build_gapped_line(
            canvas_index,
            center,
            direction,
            intervals,
            lambda distance_value, color=color: color,
        )
        if points is None:
            return None
        if len(points) >= 2:
            lines.append(points)
    return lines


def _build_ellipse_fill(
    center: tuple[float, float],
    x_length: float,
    y_length: float,
    angle: float,
    canvas_index: int,
    precision: float,
    fillerstyle: str,
    filler: dict,
) -> list[list[dict]] | None:
    start_parameter = 0.0
    if fillerstyle in ("radialBorder", "conicBorder"):
        if fillerstyle == "radialBorder":
            direction = (0.0, 1.0)
        else:
            angle_value = math.radians(filler["angle"])
            direction = (math.sin(angle_value), math.cos(angle_value))
        value = _ellipse_ray_parameter(
            center,
            x_length,
            y_length,
            angle,
            (filler["center"]["x"], filler["center"]["y"]),
            direction,
        )
        if value is None:
            return None
        start_parameter = value

    polygon = _ellipse_polygon(
        center,
        x_length,
        y_length,
        angle,
        start_parameter,
        reverse=fillerstyle in ("radialBorder", "conicBorder"),
    )
    if fillerstyle == "linear":
        return _build_fill_linear(
            polygon,
            canvas_index,
            filler["angle"],
            filler["stops"],
            precision,
        )
    if not _point_in_polygon(
        polygon,
        {"x": filler["center"]["x"], "y": filler["center"]["y"]},
    ):
        return None
    if fillerstyle == "conicBorder":
        return _build_ellipse_conic_border_fill(
            polygon,
            canvas_index,
            (filler["center"]["x"], filler["center"]["y"]),
            math.radians(filler["angle"]),
            filler["stops"],
            precision,
        )
    return _build_fill_radial_conic(
        polygon,
        canvas_index,
        filler,
        precision,
    )


def _parse_ellipse_colors(
    value: object,
    canvas_index: int,
) -> list[list[int]] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    colors = []
    for item in value:
        if isinstance(item, tuple):
            item = list(item)
        color = _normalize_color(item, canvas_index)
        if color is None:
            return None
        colors.append(color)
    return colors


def drawEllipse(
    chart: dict,
    canvasindex: int,
    centerpoint: dict,
    xLength: float,
    yLength: float,
    isDrawBorder: bool,
    isFillGraph: bool,
    angle: float = 0.0,
    lineprecision: float = 0.005,
    colorList: list | None = None,
    bordersize: int | list = [1],
    fillerstyle: str | None = None,
    fillerinfo: list | None = None,
    inserttype: str | None = None,
    insertprecision: object = None,
    timemultiple: float = 1.65,
) -> list[int] | None:
    """在指定画布绘制椭圆，返回新建线的索引列表。"""

    if not isinstance(chart, dict):
        return None
    if not isinstance(isDrawBorder, bool) or not isinstance(isFillGraph, bool):
        return None
    if not isinstance(centerpoint, dict):
        return None
    center_x = centerpoint.get("xPosition")
    center_y = centerpoint.get("time")
    if not _is_finite_number(center_x) or not _is_finite_number(center_y):
        return None
    if not _is_finite_number(xLength) or float(xLength) <= 0.0:
        return None
    if not _is_finite_number(yLength) or float(yLength) <= 0.0:
        return None
    if not _is_finite_number(angle):
        return None
    if not _is_finite_number(lineprecision) or float(lineprecision) <= 0.0:
        return None
    if not _is_finite_number(timemultiple) or float(timemultiple) <= 0.0:
        return None
    border_layers = _border_layers(bordersize)
    if border_layers is None:
        return None
    canvas_index = _resolve_canvas(chart, canvasindex)
    if canvas_index is None:
        return None
    if not isDrawBorder and not isFillGraph:
        return []

    angle_value = float(angle) % 360.0
    quarter_turn = any(
        abs(angle_value - target) <= 1e-7
        for target in (0.0, 90.0, 180.0, 270.0)
    )
    center = (float(center_x), float(center_y))
    x_value = float(xLength)
    y_value = float(yLength) * float(timemultiple)
    if not math.isfinite(y_value) or y_value <= 0.0:
        return None
    precision = float(lineprecision)

    colors = None
    if isDrawBorder:
        colors = _parse_ellipse_colors(colorList, canvas_index)
        if colors is None:
            return None
        if not quarter_turn:
            if inserttype not in (
                "uniform",
                "arc",
                "curvature",
                "recursion",
                "priority",
            ):
                return None
            if inserttype in ("uniform", "arc", "curvature"):
                if not _is_int(insertprecision) or int(insertprecision) <= 0:
                    return None
            elif (
                not _is_finite_number(insertprecision)
                or float(insertprecision) <= 0.0
            ):
                return None

    line_groups = []
    if isFillGraph:
        if fillerstyle not in (
            "linear",
            "radial",
            "conic",
            "radialBorder",
            "conicBorder",
        ):
            return None
        if fillerinfo is None:
            return None
        filler = _parse_fillerinfo(
            fillerstyle,
            fillerinfo,
            canvas_index,
        )
        if filler is None:
            return None
        fill_lines = _build_ellipse_fill(
            center,
            x_value,
            y_value,
            angle_value,
            canvas_index,
            precision,
            fillerstyle,
            filler,
        )
        if fill_lines is None:
            return None
        line_groups.extend(fill_lines)

    if isDrawBorder and border_layers:
        if quarter_turn:
            border_lines = _build_ellipse_border_90(
                center,
                x_value,
                y_value,
                angle_value,
                border_layers,
                precision,
                canvas_index,
                colors,
            )
        else:
            border_lines = _build_ellipse_border_curved(
                center,
                x_value,
                y_value,
                angle_value,
                border_layers,
                precision,
                canvas_index,
                colors,
                inserttype,
                insertprecision,
            )
        if border_lines is None:
            return None
        line_groups.extend(border_lines)

    if not line_groups:
        return []
    return _commit(chart, line_groups)


_REGION_EPS = 1e-6
_REGION_ANGLE_EPS = 1e-10
_REGION_CURVE_SAMPLES = 96


def _region_line_data(
    chart: dict,
    canvas_index: int,
    lineindexlist: object,
) -> list[dict] | None:
    if not isinstance(lineindexlist, list) or not lineindexlist:
        return None
    line_count = getLineCount(chart)
    if not _is_int(line_count) or line_count <= 0:
        return None

    result = []
    seen = set()
    for value in lineindexlist:
        if not _is_int(value):
            return None
        line_index = value + line_count if value < 0 else value
        if not 0 <= line_index < line_count:
            return None
        if line_index in seen:
            continue
        seen.add(line_index)
        line_spec = getLine(chart, line_index)
        if not isinstance(line_spec, dict):
            return None
        points = line_spec.get("linePoints")
        if not isinstance(points, list) or len(points) < 2:
            return None
        if any(
            point.get("canvasIndex") != canvas_index
            for point in points
        ):
            return None
        result.append(
            {
                "chart": chart,
                "index": line_index,
                "order": len(result),
                "points": points,
            }
        )
    return result


def _region_segment(
    line: dict,
    segment_index: int,
) -> dict:
    points = line["points"]
    first = points[segment_index]
    second = points[segment_index + 1]
    return {
        "chart": line["chart"],
        "line": line,
        "segment_index": segment_index,
        "first": first,
        "second": second,
        "curved": (
            first.get("easeType") != 0
            and second["time"] > first["time"]
        ),
    }


def _region_segment_eval(
    segment: dict,
    value: float,
    use_ease: bool,
) -> tuple[float, float]:
    first = segment["first"]
    second = segment["second"]
    ratio = max(0.0, min(1.0, float(value)))
    time = first["time"] + (second["time"] - first["time"]) * ratio
    if (
        use_ease
        and segment["curved"]
        and second["time"] > first["time"]
    ):
        position = getLinePosition(
            segment["chart"],
            segment["line"]["index"],
            time,
        )
        if position is not None:
            return float(position), float(time)
    position = (
        first["xPosition"]
        + (second["xPosition"] - first["xPosition"]) * ratio
    )
    return float(position), float(time)


def _region_segment_samples(
    segment: dict,
    use_ease: bool,
) -> list[tuple[float, float, float]]:
    if not use_ease or not segment["curved"]:
        first = segment["first"]
        second = segment["second"]
        return [
            (0.0, first["xPosition"], first["time"]),
            (1.0, second["xPosition"], second["time"]),
        ]
    if "samples" not in segment:
        samples = []
        for index in range(_REGION_CURVE_SAMPLES + 1):
            value = index / _REGION_CURVE_SAMPLES
            x_position, time = _region_segment_eval(segment, value, True)
            samples.append((value, x_position, time))
        segment["samples"] = samples
    return segment["samples"]


def _region_straight_intersection(
    first_a: tuple[float, float],
    first_b: tuple[float, float],
    second_a: tuple[float, float],
    second_b: tuple[float, float],
):
    rx = first_b[0] - first_a[0]
    ry = first_b[1] - first_a[1]
    sx = second_b[0] - second_a[0]
    sy = second_b[1] - second_a[1]
    denominator = _cross(rx, ry, sx, sy)
    qx = second_a[0] - first_a[0]
    qy = second_a[1] - first_a[1]

    if abs(denominator) > _REGION_EPS:
        first_ratio = _cross(qx, qy, sx, sy) / denominator
        second_ratio = _cross(qx, qy, rx, ry) / denominator
        if (
            -_REGION_EPS <= first_ratio <= 1.0 + _REGION_EPS
            and -_REGION_EPS <= second_ratio <= 1.0 + _REGION_EPS
        ):
            return (
                max(0.0, min(1.0, first_ratio)),
                max(0.0, min(1.0, second_ratio)),
                (
                    first_a[0] + rx * first_ratio,
                    first_a[1] + ry * first_ratio,
                ),
            )
        return None

    if abs(_cross(qx, qy, rx, ry)) > _REGION_EPS:
        return None
    length_squared = rx * rx + ry * ry
    if length_squared <= _REGION_EPS:
        return None
    first_start = (qx * rx + qy * ry) / length_squared
    first_end = (
        (second_b[0] - first_a[0]) * rx
        + (second_b[1] - first_a[1]) * ry
    ) / length_squared
    low = max(0.0, min(first_start, first_end))
    high = min(1.0, max(first_start, first_end))
    if high < low - _REGION_EPS:
        return None
    if high - low > _REGION_EPS:
        return "overlap"
    second_length_squared = sx * sx + sy * sy
    if second_length_squared <= _REGION_EPS:
        return None
    second_ratio = (
        (first_a[0] + rx * low - second_a[0]) * sx
        + (first_a[1] + ry * low - second_a[1]) * sy
    ) / second_length_squared
    return (
        low,
        max(0.0, min(1.0, second_ratio)),
        (first_a[0] + rx * low, first_a[1] + ry * low),
    )


def _region_segment_hits(
    first: dict,
    second: dict,
    use_ease: bool,
) -> list[tuple[float, float, tuple[float, float]]] | None:
    first_samples = _region_segment_samples(first, use_ease)
    second_samples = _region_segment_samples(second, use_ease)
    hits = []
    for first_index in range(len(first_samples) - 1):
        first_start = first_samples[first_index]
        first_end = first_samples[first_index + 1]
        for second_index in range(len(second_samples) - 1):
            second_start = second_samples[second_index]
            second_end = second_samples[second_index + 1]
            result = _region_straight_intersection(
                (first_start[1], first_start[2]),
                (first_end[1], first_end[2]),
                (second_start[1], second_start[2]),
                (second_end[1], second_end[2]),
            )
            if result == "overlap":
                return None
            if result is None:
                continue
            first_ratio, second_ratio, point = result
            value_a = (
                first_start[0]
                + (first_end[0] - first_start[0]) * first_ratio
            )
            value_b = (
                second_start[0]
                + (second_end[0] - second_start[0]) * second_ratio
            )
            hits.append((value_a, value_b, point))
    return hits


def _region_collect_intersections(
    segments: list[dict],
    use_ease: bool,
) -> list[list[tuple[float, float]]] | None:
    keys = [[(0.0, None), (1.0, None)] for _ in segments]

    def bbox(segment: dict):
        samples = _region_segment_samples(segment, use_ease)
        xs = [item[1] for item in samples]
        ys = [item[2] for item in samples]
        return min(xs), max(xs), min(ys), max(ys)

    boxes = [bbox(segment) for segment in segments]
    for first_index in range(len(segments)):
        first_box = boxes[first_index]
        for second_index in range(first_index + 1, len(segments)):
            second_box = boxes[second_index]
            if (
                first_box[1] < second_box[0] - _REGION_EPS
                or second_box[1] < first_box[0] - _REGION_EPS
                or first_box[3] < second_box[2] - _REGION_EPS
                or second_box[3] < first_box[2] - _REGION_EPS
            ):
                continue
            hits = _region_segment_hits(
                segments[first_index],
                segments[second_index],
                use_ease,
            )
            if hits is None:
                return None
            for value_a, value_b, point in hits:
                keys[first_index].append((value_a, point))
                keys[second_index].append((value_b, point))
    return [
        [
            (float(value), point)
            for value, point in sorted(values, key=lambda item: item[0])
        ]
        for values in keys
    ]


def _region_find_or_add_vertex(
    vertices: list[dict],
    x_position: float,
    time: float,
) -> int:
    for index, vertex in enumerate(vertices):
        if (
            abs(vertex["x"] - x_position) <= _REGION_EPS
            and abs(vertex["y"] - time) <= _REGION_EPS
        ):
            return index
    vertices.append(
        {
            "x": float(x_position),
            "y": float(time),
            "lines": set(),
            "params": [],
            "out": [],
        }
    )
    return len(vertices) - 1


def _region_build_graph(
    lines: list[dict],
    use_ease: bool,
) -> tuple[list[dict], list[dict], list[dict]] | None:
    segments = []
    for line in lines:
        for index in range(len(line["points"]) - 1):
            segment = _region_segment(line, index)
            first = segment["first"]
            second = segment["second"]
            if (
                abs(first["xPosition"] - second["xPosition"]) <= _REGION_EPS
                and abs(first["time"] - second["time"]) <= _REGION_EPS
            ):
                continue
            segments.append(segment)
    if not segments:
        return None

    keys = _region_collect_intersections(segments, use_ease)
    if keys is None:
        return None

    vertices: list[dict] = []
    edges: list[dict] = []
    for segment, values in zip(segments, keys):
        unique = []
        for value, _ in values:
            value = max(0.0, min(1.0, float(value)))
            if not unique or abs(value - unique[-1][0]) > _REGION_EPS:
                unique.append((value, None))
        for first_value, second_value in zip(unique, unique[1:]):
            if second_value[0] - first_value[0] <= _REGION_EPS:
                continue
            start_x, start_y = _region_segment_eval(
                segment,
                first_value[0],
                use_ease,
            )
            end_x, end_y = _region_segment_eval(
                segment,
                second_value[0],
                use_ease,
            )
            start = _region_find_or_add_vertex(vertices, start_x, start_y)
            end = _region_find_or_add_vertex(vertices, end_x, end_y)
            if start == end:
                continue
            param_start = segment["segment_index"] + first_value[0]
            param_end = segment["segment_index"] + second_value[0]
            line = segment["line"]
            edge_index = len(edges)
            edges.append(
                {
                    "segment": segment,
                    "line": line,
                    "u0": first_value[0],
                    "u1": second_value[0],
                    "param0": param_start,
                    "param1": param_end,
                    "start": start,
                    "end": end,
                    "use_ease": use_ease,
                }
            )
            vertices[start]["lines"].add(line["index"])
            vertices[end]["lines"].add(line["index"])
            vertices[start]["params"].append(
                (line["order"], line, param_start)
            )
            vertices[end]["params"].append(
                (line["order"], line, param_end)
            )
    if not edges:
        return None
    return edges, vertices, segments


def _region_half_direction(
    half_edge: dict,
    vertices: list[dict],
) -> tuple[float, float]:
    edge = half_edge["edge"]
    segment = edge["segment"]
    if half_edge["direction"] > 0:
        start_u = edge["u0"]
        end_u = edge["u1"]
    else:
        start_u = edge["u1"]
        end_u = edge["u0"]
    span = end_u - start_u
    near = start_u + span * 0.01
    x_position, time = _region_segment_eval(
        segment,
        near,
        edge["use_ease"],
    )
    vertex = vertices[half_edge["from"]]
    dx = x_position - vertex["x"]
    dy = time - vertex["y"]
    if abs(dx) <= _REGION_ANGLE_EPS and abs(dy) <= _REGION_ANGLE_EPS:
        other = vertices[half_edge["to"]]
        dx = other["x"] - vertex["x"]
        dy = other["y"] - vertex["y"]
    return dx, dy


def _region_face_cycles(
    edges: list[dict],
    vertices: list[dict],
) -> tuple[list[list[int]], list[dict]] | None:
    half_edges = []
    for edge_index, edge in enumerate(edges):
        for direction, start, end in (
            (1, edge["start"], edge["end"]),
            (-1, edge["end"], edge["start"]),
        ):
            half_edges.append(
                {
                    "edge": edge,
                    "direction": direction,
                    "from": start,
                    "to": end,
                }
            )
            vertices[start]["out"].append(len(half_edges) - 1)

    for vertex in vertices:
        vertex["out"].sort(
            key=lambda index: math.atan2(
                _region_half_direction(half_edges[index], vertices)[1],
                _region_half_direction(half_edges[index], vertices)[0],
            )
        )

    visited = [False] * len(half_edges)
    cycles = []
    for start in range(len(half_edges)):
        if visited[start]:
            continue
        current = start
        cycle = []
        while not visited[current]:
            visited[current] = True
            cycle.append(current)
            reverse = current ^ 1
            outgoing = vertices[half_edges[current]["to"]]["out"]
            try:
                position = outgoing.index(reverse)
            except ValueError:
                return None
            if not outgoing:
                return None
            current = outgoing[(position + 1) % len(outgoing)]
        if current != start:
            continue
        if len(cycle) >= 3:
            cycles.append(cycle)
    return cycles, half_edges


def _region_cycle_vertices(
    cycle: list[int],
    half_edges: list[dict],
) -> list[int]:
    return [half_edges[index]["from"] for index in cycle]


def _region_cycle_area(
    vertex_ids: list[int],
    vertices: list[dict],
) -> float:
    if len(vertex_ids) < 3:
        return 0.0
    total = 0.0
    for index, vertex_id in enumerate(vertex_ids):
        next_id = vertex_ids[(index + 1) % len(vertex_ids)]
        first = vertices[vertex_id]
        second = vertices[next_id]
        total += first["x"] * second["y"] - second["x"] * first["y"]
    return total * 0.5


def _region_exact_node(
    lines: list[dict],
    x_position: float,
    time: float,
) -> tuple[dict, int, dict] | None:
    best = None
    for line in lines:
        for index, point in enumerate(line["points"]):
            if (
                abs(point["xPosition"] - x_position) <= _REGION_EPS
                and abs(point["time"] - time) <= _REGION_EPS
            ):
                if best is None or line["order"] < best[0]["order"]:
                    best = (line, index, point)
    return best


def _region_line_color_at_param(line: dict, parameter: float) -> list[int]:
    points = line["points"]
    if parameter <= 0.0:
        return list(points[0]["color"])
    if parameter >= len(points) - 1:
        return list(points[-1]["color"])
    index = int(math.floor(parameter))
    ratio = parameter - index
    return _lerp_color(
        points[index]["color"],
        points[index + 1]["color"],
        ratio,
    )


def _region_meta_from_node(
    line: dict,
    point_index: int,
    parameter: float,
    lines: list[dict],
) -> dict:
    point = line["points"][point_index]
    exact = _region_exact_node(lines, point["xPosition"], point["time"])
    color = point["color"] if exact is None else exact[2]["color"]
    return {
        "x": point["xPosition"],
        "y": point["time"],
        "color": list(color),
        "line": line,
        "param": float(parameter),
    }


def _region_meta_from_coordinate(
    line: dict,
    x_position: float,
    time: float,
    parameter: float,
    lines: list[dict],
) -> dict:
    exact = _region_exact_node(lines, x_position, time)
    if exact is not None:
        color = exact[2]["color"]
    else:
        color = _region_line_color_at_param(line, parameter)
    return {
        "x": float(x_position),
        "y": float(time),
        "color": list(color),
        "line": line,
        "param": float(parameter),
    }


def _region_vertex_meta(
    vertex: dict,
    line: dict,
    parameter: float,
    lines: list[dict],
) -> dict:
    exact = _region_exact_node(lines, vertex["x"], vertex["y"])
    if exact is not None:
        color = exact[2]["color"]
    else:
        choices = sorted(
            vertex["params"],
            key=lambda item: (item[0], item[2]),
        )
        if choices:
            color = _region_line_color_at_param(choices[0][1], choices[0][2])
        else:
            color = _region_line_color_at_param(line, parameter)
    return {
        "x": float(vertex["x"]),
        "y": float(vertex["y"]),
        "color": list(color),
        "line": line,
        "param": float(parameter),
    }


def _region_curve_fractions(
    point_function,
    count: int,
    mode: str,
) -> list[float]:
    if count <= 0:
        return []
    if mode == "uniform":
        return [(index + 1) / (count + 1) for index in range(count)]
    steps = 256
    points = [point_function(index / steps) for index in range(steps + 1)]
    if mode == "arc":
        weights = [
            math.hypot(
                points[index][0] - points[index - 1][0],
                points[index][1] - points[index - 1][1],
            )
            for index in range(1, len(points))
        ]
    else:
        weights = [0.0] * len(points)
        for index in range(1, len(points) - 1):
            second_x = (
                points[index - 1][0]
                - 2.0 * points[index][0]
                + points[index + 1][0]
            )
            second_y = (
                points[index - 1][1]
                - 2.0 * points[index][1]
                + points[index + 1][1]
            )
            weights[index] = math.hypot(second_x, second_y)
    cumulative = [0.0]
    for weight in weights[1:]:
        cumulative.append(cumulative[-1] + weight)
    total = cumulative[-1]
    if total <= _REGION_EPS:
        return [(index + 1) / (count + 1) for index in range(count)]
    fractions = []
    cursor = 0
    for index in range(count):
        goal = total * (index + 1) / (count + 1)
        while cursor + 1 < len(cumulative) and cumulative[cursor + 1] < goal:
            cursor += 1
        before = cumulative[cursor]
        after = cumulative[cursor + 1] if cursor + 1 < len(cumulative) else before
        if after - before <= _REGION_EPS:
            value = cursor / (len(cumulative) - 1)
        else:
            value = (
                cursor + (goal - before) / (after - before)
            ) / (len(cumulative) - 1)
        fractions.append(max(0.0, min(1.0, value)))
    return fractions


def _region_adaptive_fractions(point_function, threshold: float) -> list[float]:
    result = []
    insertions = [0]

    def subdivide(left: float, right: float, depth: int) -> None:
        if depth >= 14 or insertions[0] >= 4096:
            return
        middle = (left + right) * 0.5
        first = point_function(left)
        second = point_function(right)
        middle_point = point_function(middle)
        chord = math.hypot(second[0] - first[0], second[1] - first[1])
        if chord <= _REGION_EPS:
            return
        distance = abs(
            (second[0] - first[0]) * (middle_point[1] - first[1])
            - (second[1] - first[1]) * (middle_point[0] - first[0])
        ) / chord
        if distance <= threshold:
            return
        subdivide(left, middle, depth + 1)
        if insertions[0] < 4096:
            result.append(middle)
            insertions[0] += 1
        subdivide(middle, right, depth + 1)

    subdivide(0.0, 1.0, 0)
    return sorted(result)


def _region_insert_fractions(
    segment: dict,
    inserttype: str,
    precision: object,
) -> list[float]:
    if not segment["curved"]:
        return []
    if inserttype in ("uniform", "arc", "curvature"):
        return _region_curve_fractions(
            lambda value, segment=segment: _region_segment_eval(
                segment,
                value,
                True,
            ),
            int(precision),
            inserttype,
        )
    return _region_adaptive_fractions(
        lambda value, segment=segment: _region_segment_eval(
            segment,
            value,
            True,
        ),
        float(precision),
    )


def _region_insert_between(
    line: dict,
    first: dict,
    second: dict,
    inserttype: str,
    precision: object,
    lines: list[dict],
) -> list[dict] | None:
    if first["line"] is not second["line"]:
        return []
    if abs(first["param"] - second["param"]) <= _REGION_EPS:
        return []
    direction = 1.0 if second["param"] > first["param"] else -1.0
    low = min(first["param"], second["param"])
    high = max(first["param"], second["param"])
    result = []
    start_index = max(0, int(math.floor(low)))
    end_index = min(len(line["points"]) - 2, int(math.ceil(high)) - 1)
    for segment_index in range(start_index, end_index + 1):
        segment = _region_segment(line, segment_index)
        fractions = _region_insert_fractions(segment, inserttype, precision)
        if not fractions:
            continue
        local_low = max(0.0, low - segment_index)
        local_high = min(1.0, high - segment_index)
        for value in fractions:
            if not local_low + _REGION_EPS < value < local_high - _REGION_EPS:
                continue
            x_position, time = _region_segment_eval(segment, value, True)
            color = _lerp_color(
                segment["first"]["color"],
                segment["second"]["color"],
                value,
            )
            result.append(
                {
                    "x": float(x_position),
                    "y": float(time),
                    "color": list(color),
                    "line": line,
                    "param": float(segment_index + value),
                }
            )
    result.sort(key=lambda item: item["param"])
    if direction < 0:
        result.reverse()
    return result


def _region_expand_metas(
    metas: list[dict],
    inserttype: str,
    precision: object,
    lines: list[dict],
    is_insert: bool,
) -> list[dict] | None:
    if not metas:
        return []
    if not is_insert:
        return metas
    result = []
    for index, meta in enumerate(metas):
        result.append(meta)
        if index + 1 >= len(metas):
            continue
        next_meta = metas[index + 1]
        inserted = _region_insert_between(
            meta["line"],
            meta,
            next_meta,
            inserttype,
            precision,
            lines,
        )
        if inserted is None:
            return None
        result.extend(inserted)
    return result


def _region_half_params(half_edge: dict) -> tuple[float, float]:
    edge = half_edge["edge"]
    if half_edge["direction"] > 0:
        return edge["param0"], edge["param1"]
    return edge["param1"], edge["param0"]


def _region_group_runs(
    cycle: list[int],
    half_edges: list[dict],
    vertices: list[dict],
) -> list[dict]:
    runs = []
    for half_index in cycle:
        half = half_edges[half_index]
        line = half["edge"]["line"]
        if runs:
            previous = runs[-1]
            shared = previous["end"] == half["from"]
            vertex = vertices[half["from"]]
            plain = len(vertex["lines"]) == 1 and len(vertex["out"]) == 2
            if shared and previous["line"] is line and plain:
                previous["halfs"].append(half_index)
                previous["end"] = half["to"]
                previous["param_end"] = _region_half_params(half)[1]
                continue
        start_param, end_param = _region_half_params(half)
        runs.append(
            {
                "line": line,
                "halfs": [half_index],
                "start": half["from"],
                "end": half["to"],
                "param_start": start_param,
                "param_end": end_param,
            }
        )
    if len(runs) > 1:
        first = runs[0]
        last = runs[-1]
        shared = first["start"] == last["end"]
        vertex = vertices[first["start"]]
        plain = len(vertex["lines"]) == 1 and len(vertex["out"]) == 2
        if shared and first["line"] is last["line"] and plain:
            merged = {
                "line": last["line"],
                "halfs": last["halfs"] + first["halfs"],
                "start": last["start"],
                "end": first["end"],
                "param_start": last["param_start"],
                "param_end": first["param_end"],
            }
            runs = [merged] + runs[1:-1]
    return runs


def _region_external_node(
    line: dict,
    parameter: float,
    use_before: bool,
) -> dict | None:
    points = line["points"]
    if use_before:
        index = int(math.floor(parameter - _REGION_EPS))
        if 0 <= index < len(points):
            return {"line": line, "index": index, "param": float(index)}
    else:
        index = int(math.ceil(parameter + _REGION_EPS))
        if 0 <= index < len(points):
            return {"line": line, "index": index, "param": float(index)}
    return None


def _region_false_run(
    run: dict,
    vertices: list[dict],
    lines: list[dict],
    inserttype: str,
    precision: object,
    is_insert: bool,
) -> list[dict] | None:
    line = run["line"]
    points = line["points"]
    start_vertex = vertices[run["start"]]
    end_vertex = vertices[run["end"]]
    start = run["param_start"]
    end = run["param_end"]
    exact_start = _region_exact_node(
        lines,
        start_vertex["x"],
        start_vertex["y"],
    )
    exact_end = _region_exact_node(
        lines,
        end_vertex["x"],
        end_vertex["y"],
    )

    low = min(start, end)
    high = max(start, end)
    internal_indices = [
        index
        for index in range(len(points))
        if low + _REGION_EPS < index < high - _REGION_EPS
    ]
    if start > end:
        internal_indices.reverse()

    metas = []
    if internal_indices:
        if exact_start is not None:
            metas.append(
                _region_meta_from_coordinate(
                    line,
                    start_vertex["x"],
                    start_vertex["y"],
                    start,
                    lines,
                )
            )
        for index in internal_indices:
            metas.append(
                _region_meta_from_node(
                    line,
                    index,
                    float(index),
                    lines,
                )
            )
        if exact_end is not None:
            metas.append(
                _region_meta_from_coordinate(
                    line,
                    end_vertex["x"],
                    end_vertex["y"],
                    end,
                    lines,
                )
            )
    else:
        forward = end > start
        if exact_start is not None:
            start_meta = _region_meta_from_coordinate(
                line,
                start_vertex["x"],
                start_vertex["y"],
                start,
                lines,
            )
        else:
            external = _region_external_node(
                line,
                start,
                use_before=forward,
            )
            if external is None:
                start_meta = _region_meta_from_coordinate(
                    line,
                    start_vertex["x"],
                    start_vertex["y"],
                    start,
                    lines,
                )
            else:
                start_meta = _region_meta_from_node(
                    line,
                    external["index"],
                    external["param"],
                    lines,
                )
        if exact_end is not None:
            end_meta = _region_meta_from_coordinate(
                line,
                end_vertex["x"],
                end_vertex["y"],
                end,
                lines,
            )
        else:
            external = _region_external_node(
                line,
                end,
                use_before=not forward,
            )
            if external is None:
                end_meta = _region_meta_from_coordinate(
                    line,
                    end_vertex["x"],
                    end_vertex["y"],
                    end,
                    lines,
                )
            else:
                end_meta = _region_meta_from_node(
                    line,
                    external["index"],
                    external["param"],
                    lines,
                )
        metas = [start_meta, end_meta]

    unique = []
    for meta in metas:
        if (
            not unique
            or abs(unique[-1]["x"] - meta["x"]) > _REGION_EPS
            or abs(unique[-1]["y"] - meta["y"]) > _REGION_EPS
        ):
            unique.append(meta)
    if len(unique) < 2:
        return unique
    return _region_expand_metas(
        unique,
        inserttype,
        precision,
        lines,
        is_insert,
    )


def _region_true_run(
    run: dict,
    half_edges: list[dict],
    vertices: list[dict],
    lines: list[dict],
    inserttype: str,
    precision: object,
    is_insert: bool,
) -> list[dict] | None:
    line = run["line"]
    metas = []
    start_half = half_edges[run["halfs"][0]]
    start_param = _region_half_params(start_half)[0]
    metas.append(
        _region_vertex_meta(
            vertices[run["start"]],
            line,
            start_param,
            lines,
        )
    )
    for half_index in run["halfs"]:
        half = half_edges[half_index]
        end_param = _region_half_params(half)[1]
        metas.append(
            _region_vertex_meta(
                vertices[half["to"]],
                line,
                end_param,
                lines,
            )
        )
    unique = []
    for meta in metas:
        if (
            not unique
            or abs(unique[-1]["x"] - meta["x"]) > _REGION_EPS
            or abs(unique[-1]["y"] - meta["y"]) > _REGION_EPS
        ):
            unique.append(meta)
    return _region_expand_metas(
        unique,
        inserttype,
        precision,
        lines,
        is_insert,
    )


def _region_append_metas(target: list[dict], values: list[dict]) -> None:
    for meta in values:
        if (
            target
            and abs(target[-1]["x"] - meta["x"]) <= _REGION_EPS
            and abs(target[-1]["y"] - meta["y"]) <= _REGION_EPS
        ):
            continue
        target.append(meta)


def _region_face_center(
    cycle: list[int],
    half_edges: list[dict],
    vertices: list[dict],
) -> tuple[float, float]:
    ids = _region_cycle_vertices(cycle, half_edges)
    if not ids:
        return 0.0, 0.0
    x_position = sum(vertices[index]["x"] for index in ids) / len(ids)
    time = sum(vertices[index]["y"] for index in ids) / len(ids)
    return x_position, time


def _region_cycle_metas(
    cycle: list[int],
    half_edges: list[dict],
    vertices: list[dict],
    lines: list[dict],
    is_create_cross_point: bool,
    inserttype: str,
    precision: object,
    is_insert: bool,
) -> list[dict] | None:
    runs = _region_group_runs(cycle, half_edges, vertices)
    result = []
    for run in runs:
        if is_create_cross_point:
            metas = _region_true_run(
                run,
                half_edges,
                vertices,
                lines,
                inserttype,
                precision,
                is_insert,
            )
        else:
            metas = _region_false_run(
                run,
                vertices,
                lines,
                inserttype,
                precision,
                is_insert,
            )
        if metas is None:
            return None
        _region_append_metas(result, metas)
    return result


def _region_polygon_area(metas: list[dict]) -> float:
    total = 0.0
    for index, meta in enumerate(metas):
        next_meta = metas[(index + 1) % len(metas)]
        total += meta["x"] * next_meta["y"] - next_meta["x"] * meta["y"]
    return total * 0.5


def _region_finish_metas(
    metas: list[dict],
    center: tuple[float, float],
    canvas_index: int,
    allow_angular_fallback: bool,
) -> list[dict] | None:
    unique = []
    for meta in metas:
        if (
            not unique
            or abs(unique[-1]["x"] - meta["x"]) > _REGION_EPS
            or abs(unique[-1]["y"] - meta["y"]) > _REGION_EPS
        ):
            unique.append(meta)
    if (
        len(unique) > 1
        and abs(unique[0]["x"] - unique[-1]["x"]) <= _REGION_EPS
        and abs(unique[0]["y"] - unique[-1]["y"]) <= _REGION_EPS
    ):
        unique.pop()
    if len(unique) < 3:
        return None

    def as_polygon(values: list[dict]) -> list[dict]:
        return [{"x": item["x"], "y": item["y"]} for item in values]

    if not _is_simple_polygon(as_polygon(unique)):
        if not allow_angular_fallback:
            return None
        reduced = []
        for meta in unique:
            if any(
                abs(meta["x"] - item["x"]) <= _REGION_EPS
                and abs(meta["y"] - item["y"]) <= _REGION_EPS
                for item in reduced
            ):
                continue
            reduced.append(meta)
        if len(reduced) < 3:
            return None
        reduced.sort(
            key=lambda item: math.atan2(
                item["y"] - center[1],
                item["x"] - center[0],
            ),
            reverse=True,
        )
        unique = reduced
        if not _is_simple_polygon(as_polygon(unique)):
            return None

    area = _region_polygon_area(unique)
    if abs(area) <= _REGION_EPS:
        return None
    if area > 0.0:
        unique.reverse()

    first_line_index = None
    for index, meta in enumerate(unique):
        if meta["line"]["order"] == 0:
            if first_line_index is None:
                first_line_index = index
            elif meta["param"] < unique[first_line_index]["param"]:
                first_line_index = index
    if first_line_index is not None and first_line_index != 0:
        unique = unique[first_line_index:] + unique[:first_line_index]

    result = []
    for meta in unique:
        point = createLinePoint(
            float(meta["y"]),
            float(meta["x"]),
            canvas_index,
            0,
            list(meta["color"]),
        )
        if point is None:
            return None
        result.append(point)
    return result


def getClosedRegion(
    chart: dict,
    canvasindex: int,
    lineindexlist: list,
    isCreateCrossPoint: bool = True,
    isInsertPoint: bool = True,
    precision: int | float = 1,
    inserttype: str = "uniform",
) -> list[list[dict]] | None:
    """计算所选引导线围成的所有闭合区域，返回按顺时针排列的线节点规格列表。"""

    if not isinstance(chart, dict):
        return None
    if not isinstance(isCreateCrossPoint, bool):
        return None
    if not isinstance(isInsertPoint, bool):
        return None
    if not isinstance(lineindexlist, list) or not lineindexlist:
        return None
    canvas_index = _resolve_canvas(chart, canvasindex)
    if canvas_index is None:
        return None

    if isInsertPoint:
        if inserttype not in (
            "uniform",
            "arc",
            "curvature",
            "recursion",
            "priority",
        ):
            return None
        if inserttype in ("uniform", "arc", "curvature"):
            if not _is_int(precision) or int(precision) <= 0:
                return None
        elif not _is_finite_number(precision) or float(precision) <= 0.0:
            return None

    lines = _region_line_data(chart, canvas_index, lineindexlist)
    if lines is None:
        return None
    graph = _region_build_graph(lines, isInsertPoint)
    if graph is None:
        return None
    edges, vertices, _ = graph
    face_result = _region_face_cycles(edges, vertices)
    if face_result is None:
        return None
    cycles, half_edges = face_result

    regions = []
    for cycle in cycles:
        vertex_ids = _region_cycle_vertices(cycle, half_edges)
        area = _region_cycle_area(vertex_ids, vertices)
        if area >= -_REGION_EPS:
            continue
        center = _region_face_center(cycle, half_edges, vertices)
        metas = _region_cycle_metas(
            cycle,
            half_edges,
            vertices,
            lines,
            isCreateCrossPoint,
            inserttype,
            precision,
            isInsertPoint,
        )
        if metas is None:
            return None
        region = _region_finish_metas(
            metas,
            center,
            canvas_index,
            not isCreateCrossPoint,
        )
        if region is None:
            return None
        regions.append(region)
    return regions if regions else None


def _parse_holelist(
    holelist: object,
    canvas_index: int,
) -> list[list[dict]] | None:
    if holelist is None:
        return []
    if not isinstance(holelist, list):
        return None
    result = []
    for item in holelist:
        hole = _parse_polygon(item, canvas_index)
        if hole is None:
            return None
        result.append(hole)
    return result


def _merge_line_ranges(
    ranges: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    clipped = []
    for start, end in ranges:
        start = max(0.0, min(1.0, float(start)))
        end = max(0.0, min(1.0, float(end)))
        if end - start > _EPS:
            clipped.append((start, end))
    clipped.sort()
    merged = []
    for start, end in clipped:
        if not merged or start > merged[-1][1] + _EPS:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _hole_segment_ranges(
    first: dict,
    second: dict,
    holes: list[list[dict]],
) -> list[tuple[float, float]]:
    origin = (first["xPosition"], first["time"])
    direction = (
        second["xPosition"] - first["xPosition"],
        second["time"] - first["time"],
    )
    if (
        abs(direction[0]) <= _EPS
        and abs(direction[1]) <= _EPS
    ):
        return []
    midpoint = {
        "x": (first["xPosition"] + second["xPosition"]) * 0.5,
        "y": (first["time"] + second["time"]) * 0.5,
    }
    ranges = []
    for hole in holes:
        intervals = _line_intervals(hole, origin, direction)
        if not intervals and _point_strictly_in_polygon(hole, midpoint):
            ranges.append((0.0, 1.0))
            continue
        ranges.extend(intervals)
    return _merge_line_ranges(ranges)


def _mask_fill_line(
    line: list[dict],
    holes: list[list[dict]],
    holecolor: list[int],
    canvas_index: int,
) -> list[dict] | None:
    if len(line) < 2:
        return line
    points = list(line)
    if points[-1]["time"] < points[0]["time"]:
        points.reverse()

    records = []

    def append_point(x_position: float, time: float, color: list[int]) -> None:
        if (
            records
            and abs(records[-1][0] - x_position) <= _EPS
            and abs(records[-1][1] - time) <= _EPS
            and records[-1][2] == color
        ):
            return
        records.append((float(x_position), float(time), list(color)))

    for first, second in zip(points, points[1:]):
        start_x = first["xPosition"]
        start_y = first["time"]
        end_x = second["xPosition"]
        end_y = second["time"]
        first_color = first["color"]
        second_color = second["color"]
        ranges = _hole_segment_ranges(first, second, holes)
        if not ranges:
            append_point(start_x, start_y, first_color)
            append_point(end_x, end_y, second_color)
            continue

        bounds = [0.0, 1.0]
        for start, end in ranges:
            bounds.extend((start, end))
        unique_bounds = []
        for value in sorted(bounds):
            if not unique_bounds or value > unique_bounds[-1] + _EPS:
                unique_bounds.append(value)
        pieces = []
        for start, end in zip(unique_bounds, unique_bounds[1:]):
            if end - start <= _EPS:
                continue
            middle = (start + end) * 0.5
            inside = any(
                low - _EPS <= middle <= high + _EPS
                for low, high in ranges
            )
            pieces.append((start, end, inside))

        def point_at(value: float) -> tuple[float, float]:
            return (
                start_x + (end_x - start_x) * value,
                start_y + (end_y - start_y) * value,
            )

        def color_at(value: float, inside: bool) -> list[int]:
            if inside:
                return holecolor
            return _lerp_color(first_color, second_color, value)

        if not pieces:
            append_point(start_x, start_y, first_color)
            append_point(end_x, end_y, second_color)
            continue

        previous_inside = pieces[0][2]
        x_position, time = point_at(0.0)
        append_point(x_position, time, color_at(0.0, previous_inside))
        for index, (start, end, inside) in enumerate(pieces):
            if index > 0 and inside != previous_inside:
                x_position, time = point_at(start)
                append_point(x_position, time, color_at(start, inside))
            x_position, time = point_at(end)
            append_point(x_position, time, color_at(end, inside))
            previous_inside = inside

    result = []
    for x_position, time, color in records:
        point = _make_point(canvas_index, time, x_position, color)
        if point is None:
            return None
        result.append(point)
    return result if len(result) >= 2 else None


def _mask_fill_lines(
    fill_lines: list[list[dict]],
    holes: list[list[dict]],
    holecolor: list[int],
    canvas_index: int,
) -> list[list[dict]] | None:
    if not holes:
        return fill_lines
    result = []
    for line in fill_lines:
        masked = _mask_fill_line(line, holes, holecolor, canvas_index)
        if masked is None:
            return None
        result.append(masked)
    return result
