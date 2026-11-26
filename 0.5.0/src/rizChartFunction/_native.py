"""Optional C++ geometry kernels with a pure-Python fallback."""

from __future__ import annotations

from typing import Iterable

try:
    from . import _rizchart_native as _native
except Exception as error:  # pragma: no cover - environment dependent
    _native = None
    _native_error = error
else:
    _native_error = None

__all__ = [
    "available",
    "native_error",
    "native_version",
    "is_simple_polygon",
    "line_intervals",
    "line_intervals_many",
    "point_in_polygon_many",
]


def available() -> bool:
    """Return whether the optional native extension is loaded."""
    return _native is not None


def native_error() -> Exception | None:
    """Return the import error for the native extension, if any."""
    return _native_error


def native_version() -> str | None:
    if _native is None:
        return None
    return str(getattr(_native, "__version__", ""))


def _point_xy(point: object) -> tuple[float, float]:
    if isinstance(point, dict):
        return float(point["x"]), float(point["y"])
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        return float(point[0]), float(point[1])
    raise TypeError("point must be a dict with x/y or a 2-element sequence")


def _point_list(points: Iterable[object]) -> list[tuple[float, float]]:
    return [_point_xy(point) for point in points]


def _flat_points(points: Iterable[object]) -> list[float]:
    result = []
    for x, y in _point_list(points):
        result.append(x)
        result.append(y)
    return result


def _dict_points(points: Iterable[object]) -> list[dict]:
    return [{"x": x, "y": y} for x, y in _point_list(points)]


def is_simple_polygon(points: Iterable[object]) -> bool:
    """Check whether the given polygon is simple.

    Uses the native extension when available; otherwise delegates to the
    existing Python geometry implementation.
    """
    points = _point_list(points)
    if len(points) < 3:
        return False
    if _native is not None:
        return bool(_native.is_simple_polygon(_flat_points(points)))

    from .advanced_draw import _is_simple_polygon

    return bool(_is_simple_polygon(_dict_points(points)))


def line_intervals(
    points: Iterable[object],
    origin: tuple[float, float],
    direction: tuple[float, float],
    start_t: float | None = None,
    end_t: float | None = None,
) -> list[tuple[float, float]]:
    """Return line/polygon intervals in the same form as advanced_draw."""
    points = _point_list(points)
    if len(points) < 3:
        return []
    if _native is not None:
        result = _native.line_intervals(
            _flat_points(points),
            float(origin[0]),
            float(origin[1]),
            float(direction[0]),
            float(direction[1]),
            start_t,
            end_t,
        )
        return [(float(left), float(right)) for left, right in result]

    from .advanced_draw import _line_intervals

    return _line_intervals(
        _dict_points(points),
        origin,
        direction,
        start_t,
        end_t,
    )


def line_intervals_many(
    points: Iterable[object],
    origins: Iterable[object],
    directions: Iterable[object],
    start_ts: Iterable[float] | None = None,
    end_ts: Iterable[float] | None = None,
) -> list[list[tuple[float, float]]]:
    """Return intervals for multiple rays against one polygon."""
    polygon = _point_list(points)
    if len(polygon) < 3:
        return []
    origins = _point_list(origins)
    directions = _point_list(directions)
    if len(origins) != len(directions):
        raise ValueError("origins and directions must have the same length")

    starts = None if start_ts is None else [float(value) for value in start_ts]
    ends = None if end_ts is None else [float(value) for value in end_ts]
    if starts is not None and len(starts) != len(origins):
        raise ValueError("start_ts must match the ray count")
    if ends is not None and len(ends) != len(origins):
        raise ValueError("end_ts must match the ray count")

    if _native is not None:
        result = _native.line_intervals_many(
            _flat_points(polygon),
            _flat_points(origins),
            _flat_points(directions),
            starts,
            ends,
        )
        return [
            [(float(left), float(right)) for left, right in intervals]
            for intervals in result
        ]

    from .advanced_draw import _line_intervals

    polygon_specs = _dict_points(polygon)
    return [
        _line_intervals(
            polygon_specs,
            origin,
            direction,
            None if starts is None else starts[index],
            None if ends is None else ends[index],
        )
        for index, (origin, direction) in enumerate(zip(origins, directions))
    ]


def point_in_polygon_many(
    points: Iterable[object],
    query_points: Iterable[object],
    include_boundary: bool = True,
) -> list[bool]:
    """Test multiple points against a polygon."""
    polygon = _point_list(points)
    query = _point_list(query_points)
    if len(polygon) < 3:
        return [False] * len(query)
    if _native is not None:
        return [
            bool(value)
            for value in _native.point_in_polygon_many(
                _flat_points(polygon),
                _flat_points(query),
                include_boundary,
            )
        ]

    from .advanced_draw import _point_in_polygon_with_boundary

    polygon_specs = _dict_points(polygon)
    return [
        bool(
            _point_in_polygon_with_boundary(
                polygon_specs,
                {"x": x, "y": y},
                include_boundary,
            )
        )
        for x, y in query
    ]
