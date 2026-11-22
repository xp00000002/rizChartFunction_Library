"""字体字形转闭合图形、绘制文字与细字骨架的组合工具。"""

from __future__ import annotations

import math
import os

from .advanced_draw import drawPolygon
from .base import refresh
from .chart import (
    addLine,
    createLinePoint,
    createRingPoint,
    deleteLine,
)
from .query import getCanvasCount

try:  # Optional font/geometry dependencies.
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon, box
    from shapely.ops import unary_union
    from shapely.validation import make_valid

    _FONT_DEPS = True
except ImportError:  # pragma: no cover - environment dependent
    BasePen = object
    TTFont = None
    instantiateVariableFont = None
    GeometryCollection = None
    MultiPolygon = None
    Point = None
    Polygon = None
    box = None
    unary_union = None
    make_valid = None
    _FONT_DEPS = False

try:  # Optional skeleton dependencies.
    import numpy as np
    from skimage.draw import polygon as _raster_polygon
    from skimage.morphology import skeletonize

    _SKELETON_DEPS = True
except ImportError:  # pragma: no cover - environment dependent
    np = None
    _raster_polygon = None
    skeletonize = None
    _SKELETON_DEPS = False

__all__ = ["drawText", "drawThinText"]

_EPS = 1e-9
_TRANSPARENT = [0, 0, 0, 0]


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


def _parse_color(value: object, canvas_index: int) -> list[int] | None:
    point = createLinePoint(0.0, 0.0, canvas_index, 0, value)
    if point is None:
        return None
    return list(point["color"])


def _point_line_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= _EPS:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(
        dx * (point[1] - start[1])
        - dy * (point[0] - start[0])
    ) / length


if _FONT_DEPS:

    class _FlattenPen(BasePen):
        """Flatten TrueType/OpenType curves into closed contours."""

        def __init__(self, glyph_set, tolerance: float):
            super().__init__(glyph_set)
            self.tolerance = float(tolerance)
            self.contours = []
            self.current = []

        def _flush(self, close: bool) -> None:
            if len(self.current) >= 2:
                if (
                    close
                    and (
                        abs(self.current[0][0] - self.current[-1][0]) > _EPS
                        or abs(self.current[0][1] - self.current[-1][1]) > _EPS
                    )
                ):
                    self.current.append(self.current[0])
                if len(self.current) >= 3:
                    self.contours.append(self.current)
            self.current = []

        def _moveTo(self, point) -> None:
            self._flush(False)
            self.current = [tuple(point)]

        def _lineTo(self, point) -> None:
            self.current.append(tuple(point))

        def _qCurveToOne(self, control, end) -> None:
            start = self._getCurrentPoint()
            self._flatten_quadratic(
                tuple(start),
                tuple(control),
                tuple(end),
                0,
            )

        def _curveToOne(self, control1, control2, end) -> None:
            start = self._getCurrentPoint()
            self._flatten_cubic(
                tuple(start),
                tuple(control1),
                tuple(control2),
                tuple(end),
                0,
            )

        def _closePath(self) -> None:
            self._flush(True)

        def _endPath(self) -> None:
            self._flush(True)

        def _flatten_quadratic(self, start, control, end, depth) -> None:
            if depth >= 14 or _point_line_distance(control, start, end) <= self.tolerance:
                self.current.append(end)
                return
            first = (
                (start[0] + control[0]) * 0.5,
                (start[1] + control[1]) * 0.5,
            )
            middle = (
                (control[0] + end[0]) * 0.5,
                (control[1] + end[1]) * 0.5,
            )
            center = (
                (first[0] + middle[0]) * 0.5,
                (first[1] + middle[1]) * 0.5,
            )
            self._flatten_quadratic(start, first, center, depth + 1)
            self._flatten_quadratic(center, middle, end, depth + 1)

        def _flatten_cubic(self, start, control1, control2, end, depth) -> None:
            if depth >= 14:
                self.current.append(end)
                return
            if (
                max(
                    _point_line_distance(control1, start, end),
                    _point_line_distance(control2, start, end),
                )
                <= self.tolerance
            ):
                self.current.append(end)
                return
            first = (
                (start[0] + control1[0]) * 0.5,
                (start[1] + control1[1]) * 0.5,
            )
            second = (
                (control1[0] + control2[0]) * 0.5,
                (control1[1] + control2[1]) * 0.5,
            )
            third = (
                (control2[0] + end[0]) * 0.5,
                (control2[1] + end[1]) * 0.5,
            )
            first_middle = (
                (first[0] + second[0]) * 0.5,
                (first[1] + second[1]) * 0.5,
            )
            second_middle = (
                (second[0] + third[0]) * 0.5,
                (second[1] + third[1]) * 0.5,
            )
            center = (
                (first_middle[0] + second_middle[0]) * 0.5,
                (first_middle[1] + second_middle[1]) * 0.5,
            )
            self._flatten_cubic(start, first, first_middle, center, depth + 1)
            self._flatten_cubic(center, second_middle, third, end, depth + 1)


def _load_font(fontpath: object, weight: object):
    if not _FONT_DEPS:
        return None
    if not isinstance(fontpath, (str, os.PathLike)):
        return None
    try:
        font = TTFont(os.fspath(fontpath), fontNumber=0)
    except Exception:
        return None

    if weight is not None:
        if not _is_finite_number(weight):
            try:
                font.close()
            except Exception:
                pass
            return None
        fvar = font.get("fvar")
        if fvar is not None:
            axis = next(
                (
                    item
                    for item in fvar.axes
                    if getattr(item, "axisTag", None) == "wght"
                ),
                None,
            )
            if axis is not None:
                value = min(
                    float(axis.maxValue),
                    max(float(axis.minValue), float(weight)),
                )
                try:
                    instantiateVariableFont(
                        font,
                        {"wght": value},
                        inplace=True,
                    )
                except Exception:
                    pass
    return font


def _glyph_infos(font, text: str):
    try:
        units_per_em = float(font["head"].unitsPerEm)
        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        hmtx = font["hmtx"]
    except Exception:
        return None
    if not units_per_em or cmap is None:
        return None

    tolerance = max(0.01, units_per_em * 0.0005)
    infos = []
    for character in text:
        code = ord(character)
        glyph_name = cmap.get(code)
        if glyph_name is None:
            return None
        pen = _FlattenPen(glyph_set, tolerance)
        try:
            glyph_set[glyph_name].draw(pen)
            advance = float(hmtx[glyph_name][0])
        except Exception:
            return None
        infos.append(
            {
                "contours": pen.contours,
                "advance": advance,
            }
        )
    return infos


def _polygon_parts(geometry):
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    if geometry.geom_type == "GeometryCollection":
        result = []
        for item in geometry.geoms:
            result.extend(_polygon_parts(item))
        return result
    return []


def _clean_polygon(polygon):
    if polygon is None or polygon.is_empty:
        return []
    if not polygon.is_valid:
        try:
            polygon = make_valid(polygon)
        except Exception:
            return []
    return _polygon_parts(polygon)


def _rings_to_geometry(contours):
    rings = []
    for contour in contours:
        points = []
        for x_position, time in contour:
            if (
                not points
                or abs(points[-1][0] - x_position) > _EPS
                or abs(points[-1][1] - time) > _EPS
            ):
                points.append((float(x_position), float(time)))
        if len(points) > 1:
            if (
                abs(points[0][0] - points[-1][0]) <= _EPS
                and abs(points[0][1] - points[-1][1]) <= _EPS
            ):
                points.pop()
        if len(points) < 3:
            continue
        try:
            polygon = Polygon(points)
        except Exception:
            continue
        if polygon.is_empty or polygon.area <= _EPS * _EPS:
            continue
        cleaned = _clean_polygon(polygon)
        rings.extend(cleaned)

    if not rings:
        return None

    depths = []
    parents = {}
    for index, ring in enumerate(rings):
        boundary_point = Point(ring.exterior.coords[0])
        containers = [
            other_index
            for other_index, other in enumerate(rings)
            if other_index != index and other.contains(boundary_point)
        ]
        depths.append(len(containers))
        if containers:
            parents[index] = min(
                containers,
                key=lambda candidate: rings[candidate].area,
            )

    parts = []
    for index, ring in enumerate(rings):
        if depths[index] % 2 != 0:
            continue
        holes = [
            hole.exterior.coords[:-1]
            for hole_index, hole in enumerate(rings)
            if depths[hole_index] == depths[index] + 1
            and parents.get(hole_index) == index
        ]
        try:
            part = Polygon(ring.exterior.coords, holes)
        except Exception:
            continue
        if part.is_empty:
            continue
        if not part.is_valid:
            cleaned = _clean_polygon(part)
            parts.extend(cleaned)
        else:
            parts.append(part)

    if not parts:
        return None
    try:
        geometry = unary_union(parts)
    except Exception:
        return None
    if geometry.is_empty:
        return None
    if not geometry.is_valid:
        geometry = make_valid(geometry)
    return geometry


def _layout_text_geometry(
    font,
    text: str,
    position: float,
    time: float,
    fontsize: float,
    letterspacing: float,
    align: str,
    timemultiple: float,
    is_flip_x: bool,
):
    """把单行文字排版为谱面坐标下的闭合几何。"""
    try:
        units_per_em = float(font["head"].unitsPerEm)
    except Exception:
        return None
    if not units_per_em:
        return None

    glyph_infos = _glyph_infos(font, text)
    if glyph_infos is None:
        return None

    scale_x = float(fontsize) / units_per_em
    scale_y = scale_x * float(timemultiple)
    spacing = float(letterspacing) * float(fontsize)
    text_width = sum(
        info["advance"] * scale_x for info in glyph_infos
    ) + spacing * max(0, len(glyph_infos) - 1)

    if align == "left":
        start_x = float(position)
    elif align == "center":
        start_x = float(position) - text_width * 0.5
    else:
        start_x = float(position) - text_width

    all_points = []
    for info in glyph_infos:
        for contour in info["contours"]:
            all_points.extend(contour)

    result = {
        "glyph_infos": glyph_infos,
        "units_per_em": units_per_em,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "spacing": spacing,
        "text_width": text_width,
        "start_x": start_x,
        "text_center": start_x + text_width * 0.5,
        "minimum_y": None,
        "transformed_contours": [],
        "geometry": None,
    }
    if not all_points:
        return result

    minimum_y = min(point[1] for point in all_points)
    result["minimum_y"] = minimum_y
    transformed_contours = []
    cursor = 0.0
    for info in glyph_infos:
        origin_x = start_x + cursor
        for contour in info["contours"]:
            transformed = []
            for glyph_x, glyph_y in contour:
                x_position = origin_x + glyph_x * scale_x
                if is_flip_x:
                    x_position = result["text_center"] * 2.0 - x_position
                y_position = float(time) + (glyph_y - minimum_y) * scale_y
                transformed.append((x_position, y_position))
            transformed_contours.append(transformed)
        cursor += info["advance"] * scale_x + spacing

    result["transformed_contours"] = transformed_contours
    result["geometry"] = _rings_to_geometry(transformed_contours)
    return result


def _component_count(geometry):
    parts = _polygon_parts(geometry)
    holes = sum(len(part.interiors) for part in parts)
    return len(parts), holes


def _text_border_layers(value: object) -> list[int] | None:
    if value is None:
        return []
    if _is_int(value):
        if value >= 0:
            return list(range(0, value + 1))
        return list(range(value, 1))
    if isinstance(value, list):
        if not all(_is_int(item) for item in value):
            return None
        return sorted(set(value))
    return None


def _offset_text_geometry(geometry, offset: float):
    if abs(offset) <= _EPS:
        return geometry
    try:
        result = geometry.buffer(
            offset,
            quad_segs=16,
            cap_style=1,
            join_style=1,
        )
    except Exception:
        return None
    if result is None or result.is_empty or not result.is_valid:
        return None
    base_count = _component_count(geometry)
    result_count = _component_count(result)
    if result_count[0] < base_count[0]:
        return None
    if offset > 0.0 and result_count[1] < base_count[1]:
        return None
    return result


def _text_border_geometries(
    geometry,
    layers: list[int],
    precision: float,
) -> list[tuple[int, object]]:
    result = []
    negative = sorted((layer for layer in layers if layer < 0), reverse=True)
    for layer in negative:
        offset_geometry = _offset_text_geometry(
            geometry,
            float(layer) * precision,
        )
        if offset_geometry is None:
            break
        result.append((layer, offset_geometry))
    positive = sorted(layer for layer in layers if layer >= 0)
    for layer in positive:
        offset_geometry = _offset_text_geometry(
            geometry,
            float(layer) * precision,
        )
        if offset_geometry is None:
            break
        result.append((layer, offset_geometry))
    return sorted(result, key=lambda item: item[0])


def _outline_edges(geometry, color: list[int], canvas_index: int):
    result = []
    for polygon in _polygon_parts(geometry):
        rings = [polygon.exterior]
        rings.extend(polygon.interiors)
        for ring in rings:
            coordinates = list(ring.coords)
            if len(coordinates) > 1 and coordinates[0] == coordinates[-1]:
                coordinates = coordinates[:-1]
            if len(coordinates) < 3:
                continue
            for index, first in enumerate(coordinates):
                second = coordinates[(index + 1) % len(coordinates)]
                if (
                    abs(first[0] - second[0]) <= _EPS
                    and abs(first[1] - second[1]) <= _EPS
                ):
                    continue
                first_spec = _point_specs([first], color, canvas_index)
                second_spec = _point_specs([second], color, canvas_index)
                if first_spec is None or second_spec is None:
                    return None
                result.append((first_spec[0], second_spec[0]))
    return result


def _geometry_parts_for_draw(geometry, color: list[int], canvas_index: int):
    parts = []
    for polygon in _polygon_parts(geometry):
        if polygon.is_empty:
            continue
        outer = list(polygon.exterior.coords)
        if len(outer) > 1 and outer[0] == outer[-1]:
            outer = outer[:-1]
        if len(outer) < 3:
            continue
        outer_specs = _point_specs(outer, color, canvas_index)
        if outer_specs is None:
            return None
        holes = []
        for interior in polygon.interiors:
            hole = list(interior.coords)
            if len(hole) > 1 and hole[0] == hole[-1]:
                hole = hole[:-1]
            hole_specs = _point_specs(hole, color, canvas_index)
            if hole_specs is None:
                return None
            holes.append(hole_specs)
        parts.append((outer_specs, holes))
    return parts


def _point_specs(points, color, canvas_index):
    specs = []
    for x_position, time in points:
        if not _is_finite_number(time) or time < -_EPS:
            return None
        point = createLinePoint(
            float(time),
            float(x_position),
            canvas_index,
            0,
            color,
        )
        if point is None:
            return None
        specs.append(point)
    return specs


def _draw_parts(
    chart: dict,
    canvas_index: int,
    geometry,
    color: list[int],
    holecolor: list[int],
    precision: float,
    created: list[int],
) -> bool:
    parts = _geometry_parts_for_draw(geometry, color, canvas_index)
    if parts is None:
        return False
    for outer, holes in parts:
        indexes = drawPolygon(
            chart,
            canvas_index,
            outer,
            isDrawBorder=False,
            isFillGraph=True,
            precision=precision,
            bordersize=[],
            fillerstyle="linear",
            fillerinfo=[0, color],
            holelist=holes or None,
            holecolor=holecolor,
        )
        if indexes is None:
            return False
        created.extend(indexes)
    return True


def _draw_outline(
    chart: dict,
    canvas_index: int,
    border_geometries: list[tuple[int, object]],
    color: list[int],
    created: list[int],
) -> bool:
    ring = createRingPoint(0.0, "#00000000")
    if ring is None:
        return False
    for _, geometry in border_geometries:
        edges = _outline_edges(geometry, color, canvas_index)
        if edges is None:
            return False
        for first, second in edges:
            line_index = addLine(
                chart,
                [first, second],
                ring,
                isDelayCalculate=True,
            )
            if line_index is None:
                return False
            created.append(line_index)
    return True


_THIN_RASTER_SAMPLES = 192.0
_THIN_MAX_RASTER = 2048
_THIN_DIRECTIONS = (
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
)


def _dedupe_points(points):
    result = []
    for point in points:
        if (
            not result
            or abs(result[-1][0] - point[0]) > _EPS
            or abs(result[-1][1] - point[1]) > _EPS
        ):
            result.append((float(point[0]), float(point[1])))
    return result


def _rasterize_geometry(geometry, pixel_size: float):
    """把闭合几何按方形象素栅格化，返回 mask 和坐标偏移。"""
    try:
        min_x, min_y, max_x, max_y = geometry.bounds
        width = max(2, int(math.ceil((max_x - min_x) / pixel_size)) + 3)
        height = max(2, int(math.ceil((max_y - min_y) / pixel_size)) + 3)
        offset_x = min_x - pixel_size
        offset_y = min_y - pixel_size
        mask = np.zeros((height, width), dtype=bool)
        for polygon in _polygon_parts(geometry):
            if polygon.is_empty:
                continue
            local = np.zeros_like(mask)
            coordinates = np.asarray(polygon.exterior.coords, dtype=float)
            columns = (coordinates[:, 0] - offset_x) / pixel_size
            rows = (coordinates[:, 1] - offset_y) / pixel_size
            rr, cc = _raster_polygon(
                rows,
                columns,
                shape=(height, width),
            )
            local[rr, cc] = True
            for interior in polygon.interiors:
                coordinates = np.asarray(interior.coords, dtype=float)
                columns = (coordinates[:, 0] - offset_x) / pixel_size
                rows = (coordinates[:, 1] - offset_y) / pixel_size
                rr, cc = _raster_polygon(
                    rows,
                    columns,
                    shape=(height, width),
                )
                local[rr, cc] = False
            mask |= local
    except Exception:
        return None
    return mask, offset_x, offset_y


def _skeleton_neighbors(point, pixels):
    row, column = point
    result = []
    for row_delta, column_delta in _THIN_DIRECTIONS:
        other = (row + row_delta, column + column_delta)
        if other not in pixels:
            continue
        # Avoid redundant diagonal edges when an orthogonal two-step path exists.
        if row_delta != 0 and column_delta != 0:
            if (
                (row + row_delta, column) in pixels
                or (row, column + column_delta) in pixels
            ):
                continue
        result.append(other)
    return result


def _skeleton_pixel_paths(pixels):
    """把八连通骨架像素拆成端点/交叉点之间的路径。"""
    if not pixels:
        return []
    neighbors = {
        point: _skeleton_neighbors(point, pixels)
        for point in pixels
    }
    nodes = {
        point
        for point in pixels
        if len(neighbors[point]) != 2
    }
    visited = set()
    paths = []

    def edge(first, second):
        return (
            (first, second)
            if first <= second
            else (second, first)
        )

    def trace(start, first, stop_at_start: bool):
        path = [start, first]
        visited.add(edge(start, first))
        previous, current = start, first
        while True:
            if stop_at_start:
                if current == start:
                    break
            elif current in nodes:
                break
            candidates = [
                point
                for point in neighbors[current]
                if point != previous
            ]
            if not candidates:
                break
            following = candidates[0]
            if following == start:
                visited.add(edge(current, following))
                path.append(following)
                break
            following_edge = edge(current, following)
            if following_edge in visited:
                break
            visited.add(following_edge)
            path.append(following)
            previous, current = current, following
        return path

    for start in sorted(nodes):
        for first in neighbors[start]:
            if edge(start, first) in visited:
                continue
            path = trace(start, first, False)
            if len(path) >= 2:
                paths.append(path)

    # Closed skeleton components have no degree-1/degree-3 nodes.
    for start in sorted(pixels):
        for first in neighbors[start]:
            if edge(start, first) in visited:
                continue
            path = trace(start, first, True)
            if len(path) >= 2:
                paths.append(path)
    return paths


def _simplify_path(points, tolerance: float):
    """用迭代 RDP 简化开放折线，保留首尾。"""
    if len(points) <= 2:
        return list(points)
    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        maximum = -1.0
        index = -1
        for point_index in range(start + 1, end):
            distance = _point_line_distance(
                points[point_index],
                points[start],
                points[end],
            )
            if distance > maximum:
                maximum = distance
                index = point_index
        if maximum > tolerance:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [
        point
        for point_index, point in enumerate(points)
        if keep[point_index]
    ]


def _simplify_closed_path(points, tolerance: float):
    """简化闭环，避免首尾重合导致 RDP 退化。"""
    if len(points) <= 3:
        return list(points)
    closed_points = list(points)
    if (
        abs(closed_points[0][0] - closed_points[-1][0]) <= _EPS
        and abs(closed_points[0][1] - closed_points[-1][1]) <= _EPS
    ):
        closed_points = closed_points[:-1]
    if len(closed_points) <= 2:
        return list(points)
    start = closed_points[0]
    anchor = max(
        range(1, len(closed_points)),
        key=lambda index: math.hypot(
            closed_points[index][0] - start[0],
            closed_points[index][1] - start[1],
        ),
    )
    first_half = _simplify_path(
        closed_points[: anchor + 1],
        tolerance,
    )
    second_half = _simplify_path(
        closed_points[anchor:] + [start],
        tolerance,
    )
    simplified = first_half[:-1] + second_half
    if len(simplified) >= 2:
        simplified.append(simplified[0])
    return simplified


def _smooth_path(points, passes: int):
    if passes <= 0 or len(points) < 3:
        return list(points)
    result = list(points)
    for _ in range(passes):
        if len(result) < 3:
            break
        smoothed = [result[0]]
        for index in range(1, len(result) - 1):
            previous = result[index - 1]
            current = result[index]
            following = result[index + 1]
            smoothed.append(
                (
                    previous[0] * 0.25
                    + current[0] * 0.5
                    + following[0] * 0.25,
                    previous[1] * 0.25
                    + current[1] * 0.5
                    + following[1] * 0.25,
                )
            )
        smoothed.append(result[-1])
        result = smoothed
    return result


def _split_monotonic(points, jitter: float):
    """把折线拆成 time 单调的线，下降段反转后写入。"""
    if len(points) < 2:
        return []
    runs = []
    current = [points[0]]
    direction = 0
    for point in points[1:]:
        previous = current[-1]
        delta = point[1] - previous[1]
        if abs(delta) <= jitter:
            current.append((point[0], previous[1]))
            continue

        new_direction = 1 if delta > 0.0 else -1
        if direction == 0:
            direction = new_direction
            current.append(point)
        elif new_direction == direction:
            current.append(point)
        else:
            if len(current) >= 2:
                runs.append((direction, current))
            current = [previous, point]
            direction = new_direction
    if len(current) >= 2:
        runs.append((direction, current))

    result = []
    for run_direction, run in runs:
        cleaned = [run[0]]
        for point in run[1:]:
            previous = cleaned[-1]
            if run_direction < 0:
                y_position = min(point[1], previous[1])
            elif run_direction > 0:
                y_position = max(point[1], previous[1])
            else:
                y_position = previous[1]
            cleaned.append((point[0], y_position))
        if run_direction < 0:
            cleaned.reverse()
        cleaned = _dedupe_points(cleaned)
        if len(cleaned) >= 2:
            result.append(cleaned)
    return result


def _thin_text_segments(geometry, fontsize: float, smoothness: float):
    """栅格化字形、提取骨架，并返回可写入的折线。"""
    if (
        not _SKELETON_DEPS
        or geometry is None
        or geometry.is_empty
    ):
        return []
    try:
        min_x, min_y, max_x, max_y = geometry.bounds
    except Exception:
        return None
    span = max(max_x - min_x, max_y - min_y)
    pixel_size = max(float(fontsize) / _THIN_RASTER_SAMPLES, 1e-9)
    if span > 0.0 and span / pixel_size > _THIN_MAX_RASTER:
        pixel_size = span / _THIN_MAX_RASTER

    raster = _rasterize_geometry(geometry, pixel_size)
    if raster is None:
        return None
    mask, offset_x, offset_y = raster
    if not bool(mask.any()):
        return []

    try:
        skeleton = skeletonize(mask)
    except Exception:
        return None
    if not bool(skeleton.any()):
        return []
    pixels = {
        (int(point[0]), int(point[1]))
        for point in np.argwhere(skeleton)
    }
    raw_paths = _skeleton_pixel_paths(pixels)
    covered = set()
    for path in raw_paths:
        covered.update(path)
    isolated = sorted(pixels - covered)

    tolerance = max(
        pixel_size * 0.5,
        float(fontsize) * (0.001 + 0.014 * float(smoothness)),
    )
    passes = int(round(2.0 * float(smoothness)))
    paths = []
    for path in raw_paths:
        points = _dedupe_points(
            [
                (
                    offset_x + column * pixel_size,
                    offset_y + row * pixel_size,
                )
                for row, column in path
            ]
        )
        if len(points) < 2:
            continue
        closed = (
            abs(points[0][0] - points[-1][0]) <= _EPS
            and abs(points[0][1] - points[-1][1]) <= _EPS
        )
        if closed:
            simplified = _simplify_closed_path(points, tolerance)
        else:
            simplified = _simplify_path(points, tolerance)
        if len(simplified) < 2:
            continue
        paths.append(_smooth_path(simplified, passes))

    # A dot or a very small component may skeletonize to one pixel.
    half = max(pixel_size, float(fontsize) * 0.01) * 0.5
    for row, column in isolated:
        x_position = offset_x + column * pixel_size
        y_position = offset_y + row * pixel_size
        paths.append(
            [
                (x_position - half, y_position),
                (x_position + half, y_position),
            ]
        )

    if not paths:
        return []
    minimum_y = min(
        point[1]
        for path in paths
        for point in path
    )
    shifted = [
        [
            (point[0], point[1] - minimum_y)
            for point in path
        ]
        for path in paths
    ]

    jitter = max(pixel_size * 0.75, float(fontsize) * 0.0005)
    segments = []
    for path in shifted:
        if (
            len(path) >= 2
            and path[-1][1] < path[0][1] - _EPS
        ):
            path = list(reversed(path))
        segments.extend(_split_monotonic(path, jitter))
    return segments


def _draw_thin_segments(
    chart: dict,
    canvas_index: int,
    segments,
    color: list[int],
    created: list[int],
) -> bool:
    ring = createRingPoint(0.0, "#00000000")
    if ring is None:
        return False
    for segment in segments:
        point_specs = _point_specs(segment, color, canvas_index)
        if point_specs is None:
            return False
        line_index = addLine(
            chart,
            point_specs,
            ring,
            isDelayCalculate=True,
        )
        if line_index is None:
            return False
        created.append(line_index)
    return True


def drawText(
    chart: dict,
    canvasindex: int,
    fontpath: object,
    text: str,
    position: float,
    time: float,
    fontsize: float,
    color: list | str = "#000000",
    weight: int | float | None = None,
    letterspacing: float = 0.0,
    align: str = "left",
    bordersize: int | list | None = None,
    bordercolor: list | str = "#000000",
    isFillGraph: bool = True,
    background: bool = False,
    backgroundcolor: list | str = "#000000",
    padding: float = 0.0,
    timemultiple: float = 1.65,
    isFlipX: bool = False,
    precision: float | None = None,
) -> list[int] | None:
    """使用字体文件绘制单行文字，返回新建线的索引列表。"""

    if not _FONT_DEPS:
        return None
    if not isinstance(chart, dict):
        return None
    if not isinstance(text, str):
        return None
    if "\n" in text or "\r" in text:
        return None
    if not _is_finite_number(position) or not _is_finite_number(time):
        return None
    if not _is_finite_number(fontsize) or float(fontsize) <= 0.0:
        return None
    if not _is_finite_number(timemultiple) or float(timemultiple) <= 0.0:
        return None
    if not _is_finite_number(letterspacing):
        return None
    if precision is not None:
        if not _is_finite_number(precision) or float(precision) <= 0.0:
            return None
    if not isinstance(isFillGraph, bool):
        return None
    if not isinstance(background, bool) or not isinstance(isFlipX, bool):
        return None
    if align not in ("left", "center", "right"):
        return None
    border_layers = _text_border_layers(bordersize)
    if border_layers is None:
        return None
    canvas_index = _resolve_canvas(chart, canvasindex)
    if canvas_index is None:
        return None
    if not text:
        return []
    if not isFillGraph and not border_layers:
        return []

    fill_color = None
    if isFillGraph:
        fill_color = _parse_color(color, canvas_index)
        if fill_color is None:
            return None

    border_color = None
    if border_layers:
        border_color = _parse_color(bordercolor, canvas_index)
        if border_color is None:
            return None

    background_color = None
    if isFillGraph and background:
        if not _is_finite_number(padding) or float(padding) < 0.0:
            return None
        background_color = _parse_color(backgroundcolor, canvas_index)
        if background_color is None:
            return None

    font = _load_font(fontpath, weight)
    if font is None:
        return None
    try:
        layout = _layout_text_geometry(
            font,
            text,
            float(position),
            float(time),
            float(fontsize),
            float(letterspacing),
            align,
            float(timemultiple),
            isFlipX,
        )
        if layout is None:
            return None
        geometry = layout["geometry"]
        if geometry is None or geometry.is_empty:
            return []

        fill_precision = (
            float(precision)
            if precision is not None
            else max(0.001, float(fontsize) * 0.01)
        )
        border_geometries = _text_border_geometries(
            geometry,
            border_layers,
            fill_precision,
        )

        created = []
        try:
            if isFillGraph and background:
                min_x, min_y, max_x, max_y = geometry.bounds
                for _, border_geometry in border_geometries:
                    border_min_x, border_min_y, border_max_x, border_max_y = (
                        border_geometry.bounds
                    )
                    min_x = min(min_x, border_min_x)
                    min_y = min(min_y, border_min_y)
                    max_x = max(max_x, border_max_x)
                    max_y = max(max_y, border_max_y)
                background_geometry = box(
                    min_x - float(padding),
                    min_y - float(padding),
                    max_x + float(padding),
                    max_y + float(padding),
                ).difference(geometry)
                if not background_geometry.is_empty:
                    if not _draw_parts(
                        chart,
                        canvas_index,
                        background_geometry,
                        background_color,
                        _TRANSPARENT,
                        fill_precision,
                        created,
                    ):
                        raise RuntimeError("background draw failed")

            if isFillGraph:
                text_hole_color = (
                    background_color if background else _TRANSPARENT
                )
                if not _draw_parts(
                    chart,
                    canvas_index,
                    geometry,
                    fill_color,
                    text_hole_color,
                    fill_precision,
                    created,
                ):
                    raise RuntimeError("text draw failed")

            if border_geometries:
                if not _draw_outline(
                    chart,
                    canvas_index,
                    border_geometries,
                    border_color,
                    created,
                ):
                    raise RuntimeError("border draw failed")
                if refresh(chart, mode="all", type="all") is None:
                    raise RuntimeError("refresh failed")
        except Exception:
            for index in reversed(created):
                deleteLine(chart, index)
            return None
        return created
    finally:
        try:
            font.close()
        except Exception:
            pass


def drawThinText(
    chart: dict,
    canvasindex: int,
    fontpath: object,
    text: str,
    position: float,
    time: float,
    fontsize: float,
    color: list | str = "#000000",
    weight: int | float | None = None,
    letterspacing: float = 0.0,
    align: str = "left",
    timemultiple: float = 1.65,
    isFlipX: bool = False,
    smoothness: float = 0.5,
) -> list[int] | None:
    """使用字体骨架绘制单行细字，返回新建线的索引列表。"""

    if not _FONT_DEPS or not _SKELETON_DEPS:
        return None
    if not isinstance(chart, dict):
        return None
    if not isinstance(text, str):
        return None
    if "\n" in text or "\r" in text:
        return None
    if not _is_finite_number(position) or not _is_finite_number(time):
        return None
    if float(time) < 0.0:
        return None
    if not _is_finite_number(fontsize) or float(fontsize) <= 0.0:
        return None
    if not _is_finite_number(timemultiple) or float(timemultiple) <= 0.0:
        return None
    if not _is_finite_number(letterspacing):
        return None
    if (
        not _is_finite_number(smoothness)
        or float(smoothness) < 0.0
        or float(smoothness) > 1.0
    ):
        return None
    if not isinstance(isFlipX, bool):
        return None
    if align not in ("left", "center", "right"):
        return None

    canvas_index = _resolve_canvas(chart, canvasindex)
    if canvas_index is None:
        return None
    if not text:
        return []

    line_color = _parse_color(color, canvas_index)
    if line_color is None:
        return None

    font = _load_font(fontpath, weight)
    if font is None:
        return None
    try:
        layout = _layout_text_geometry(
            font,
            text,
            float(position),
            float(time),
            float(fontsize),
            float(letterspacing),
            align,
            float(timemultiple),
            isFlipX,
        )
        if layout is None:
            return None
        geometry = layout["geometry"]
        if geometry is None or geometry.is_empty:
            return []

        segments = _thin_text_segments(
            geometry,
            float(fontsize),
            float(smoothness),
        )
        if segments is None:
            return None
        if not segments:
            return []

        shifted_segments = [
            [
                (point[0], point[1] + float(time))
                for point in segment
            ]
            for segment in segments
        ]
        created = []
        try:
            if not _draw_thin_segments(
                chart,
                canvas_index,
                shifted_segments,
                line_color,
                created,
            ):
                raise RuntimeError("thin text draw failed")
            if refresh(chart, mode="all", type="all") is None:
                raise RuntimeError("refresh failed")
        except Exception:
            for index in reversed(created):
                deleteLine(chart, index)
            return None
        return created
    finally:
        try:
            font.close()
        except Exception:
            pass
