"""高级批量插入、复制、缓动与绘图工具。

本模块及 ``advanced_copy`` / ``advanced_ease`` / ``advanced_draw`` 只调用
base / chart / query 暴露的公开函数，不直接修改谱面 dict。
批量函数统一返回失败元素的原始索引列表；默认 ``isFailAddAllowed=False``
为原子模式，任一失败会回退整批已修改内容。
"""

from __future__ import annotations

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
    createLinePoint,
    createNote,
    createRingPoint,
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
    setCanvasPosition,
    setCanvasSpeed,
)
from .query import (
    getCanvasCount,
    getCanvasPositionAt,
    getRiztime,
    getRiztimeCount,
)
from .advanced_copy import (
    copyBpmShift,
    copyCamera,
    copyCameraPosition,
    copyCameraScale,
    copyCanvas,
    copyCanvasPosition,
    copyCanvasSpeed,
    copyLine,
    copyLineColor,
    copyLinePoint,
    copyNote,
    copyRingPoint,
    copyRiztime,
)
from .advanced_ease import (
    setBpmShiftEase,
    setCameraPositionEase,
    setCameraScaleEase,
    setCanvasPositionEase,
    setCanvasSpeedEase,
    setLineColorEase,
    setLinePointColorByList,
    setLinePointColorEase,
    setLinePointPositionEase,
    setRingColorEase,
)
from .advanced_draw import drawEllipse, drawPolygon, getClosedRegion
from .advanced_font import drawText, drawThinText

__all__ = [
    "addLineByDict",
    "addLinePointByDict",
    "addRingPointByDict",
    "addNoteByDict",
    "addIsolatedNote",
    "addLineColorByDict",
    "addRiztimeByDict",
    "addBpmByDict",
    "addCanvasByDict",
    "addCanvasPositionByDict",
    "addCanvasSpeedByDict",
    "addCameraPositionByDict",
    "addCameraScaleByDict",
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
    "drawPolygon",
    "drawEllipse",
    "getClosedRegion",
    "drawText",
    "drawThinText",
]


_TRANSPARENT = [0, 0, 0, 0]
_ISOLATED_NOTE_STEP = 1.0 / 16.0


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _resolve_canvas_index(chart: dict, value: object) -> int | None:
    if not _is_int(value):
        return None
    count = getCanvasCount(chart)
    if not _is_int(count) or count <= 0:
        return None
    index = value + count if value < 0 else value
    if not 0 <= index < count:
        return None
    return index


def _as_indexed_specs(value: object) -> list[tuple[int, dict]] | None:
    """把单个 dict 或 dict 列表统一为（原始索引, 规格）列表。"""
    if isinstance(value, dict):
        return [(0, value)]
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return list(enumerate(value))
    return None


def _sorted_indexed_specs(
    specs: list[tuple[int, dict]],
    key: str,
    default: float | None = None,
) -> tuple[list[tuple[int, dict]], list[int]]:
    """按 key 稳定排序，同时收集缺少/键值非法的原始索引。"""
    valid = []
    invalid = []
    for original_index, spec in specs:
        value = spec.get(key, default)
        if not _is_finite_number(value):
            invalid.append(original_index)
        else:
            valid.append((original_index, spec))
    valid.sort(key=lambda item: item[1].get(key, default))
    return valid, invalid


def _take_parent(
    spec: dict,
    names: tuple[str, ...],
    default: int = -1,
) -> int | None:
    """取出并删除父索引字段；字段非法时返回 None。"""
    for name in names:
        if name not in spec:
            continue
        value = spec.pop(name)
        if not isinstance(value, int) or isinstance(value, bool):
            return None
        return value
    return default


def _rollback(actions: list) -> None:
    for action in reversed(actions):
        action()


def _handle_failure(
    actions: list,
    local_actions: list,
    original_index: int,
    isFailAddAllowed: bool,
    failures: list[int],
) -> bool:
    """处理一个失败规格；返回 True 表示应中止整个批次。"""
    if isFailAddAllowed:
        _rollback(local_actions)
        failures.append(original_index)
        return False
    _rollback(actions + local_actions)
    return True


def _add_line_point_spec(
    chart: dict,
    spec: dict,
    parent: int,
) -> int | None:
    return addLinePoint(
        chart,
        spec.get("time"),
        spec.get("xPosition"),
        spec.get("canvasIndex"),
        spec.get("easeType", 0),
        spec.get("color"),
        lineindex=parent,
    )


def _add_color_spec(
    chart: dict,
    spec: dict,
    parent: int,
    adder,
) -> int | None:
    return adder(
        chart,
        parent,
        spec.get("time"),
        spec.get("startColor"),
        spec.get("endColor"),
    )


def addLineByDict(
    chart: dict,
    dictlist: dict | list,
    index: int | None = -1,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按引导线规格 Dict 插入一条或多条引导线。

    每个 Dict 使用 ``linePoints`` / ``notes`` / ``judgeRingColor`` /
    ``lineColor``。``index=-1`` 表示追加到末尾；其他索引传给 ``addLine()``。
    批量插入时保持列表顺序。

    ``isFailAddAllowed=False`` 时整批原子执行，任一规格失败会撤销本批
    已插入的线并返回该规格的原始索引；``True`` 时跳过失败规格，继续插入
    其余规格，并返回所有失败规格的原始索引。全部成功返回 ``[]``。
    整体输入非法时返回 ``[-1]``。
    """
    if not isinstance(chart, dict):
        return [-1]
    specs = _as_indexed_specs(dictlist)
    if specs is None:
        return [-1]
    if index is not None and (
        not isinstance(index, int) or isinstance(index, bool)
    ):
        return [-1]
    if not specs:
        return []

    effective_index = None if index in (None, -1) else index
    ordered = specs if effective_index is None else list(reversed(specs))
    actions = []
    failures = []
    for original_index, spec in ordered:
        line_points = spec.get("linePoints")
        ring_points = spec.get("judgeRingColor")
        notes = spec.get("notes")
        line_colors = spec.get("lineColor")
        if not isinstance(line_points, list):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        if not isinstance(ring_points, (list, dict)):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        if notes is not None and not isinstance(notes, list):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        if line_colors is not None and not isinstance(line_colors, list):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue

        inserted = addLine(
            chart,
            line_points,
            ring_points,
            index=effective_index,
            notes=notes,
            linecolors=line_colors,
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(lambda i=inserted: deleteLine(chart, i))
    return sorted(failures)


def addLinePointByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按线节点规格 Dict 添加一个或多个线节点。

    Dict 可额外包含 ``lineindex`` / ``lineIndex``；缺省为 ``-1``（最后一条线）。
    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        data = dict(spec)
        parent = _take_parent(data, ("lineindex", "lineIndex", "line_index"))
        if parent is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        inserted = _add_line_point_spec(chart, data, parent)
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(
            lambda p=parent, i=inserted: deleteLinePoint(chart, p, i)
        )
    return sorted(failures)


def addRingPointByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按判定环颜色规格 Dict 添加一个或多个判定环节点。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        data = dict(spec)
        parent = _take_parent(data, ("lineindex", "lineIndex", "line_index"))
        if parent is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        inserted = _add_color_spec(chart, data, parent, addRingPoint)
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(
            lambda p=parent, i=inserted: deleteRingPoint(chart, p, i)
        )
    return sorted(failures)


def addNoteByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按 Note 规格 Dict 添加一个或多个 Note。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        data = dict(spec)
        parent = _take_parent(data, ("lineindex", "lineIndex", "line_index"))
        if parent is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        inserted = addNote(
            chart,
            parent,
            data.get("time"),
            data.get("type"),
            data.get("endtime", 0.0),
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(
            lambda p=parent, i=inserted: deleteNote(chart, p, i)
        )
    return sorted(failures)


def addIsolatedNote(
    chart: dict,
    canvasindex: int,
    time: float,
    position: float,
    type: int | str,
    endtime: float | None = None,
    endposition: float | None = None,
    endcanvasindex: int | None = None,
    isRealTime: bool = False,
    isRealEndTime: bool = False,
    isAbsolutePosition: bool = False,
    isAbsoluteEndPosition: bool = False,
) -> int | None:
    """创建一条只服务于单个 Note 的独立透明引导线。

    Note 的类型、头部时间和 Hold 尾部时间分别由 ``type`` / ``time`` /
    ``endtime`` 决定。Tap / Drag 会在头节点上方 ``1/16`` 节拍处追加一个
    线节点；Hold 会在 ``endcanvasindex`` 上放置尾部节点。成功返回新线
    索引，失败返回 ``None``。
    """
    if not isinstance(chart, dict):
        return None
    if not _is_finite_number(time) or float(time) < 0.0:
        return None
    if not _is_finite_number(position):
        return None
    if not isinstance(isRealTime, bool) or not isinstance(
        isAbsolutePosition,
        bool,
    ):
        return None

    head_canvas = _resolve_canvas_index(chart, canvasindex)
    if head_canvas is None:
        return None

    note_spec = createNote(
        time,
        type,
        endtime if endtime is not None else 0.0,
        isRealTime=isRealTime,
        isRealEndTime=isRealEndTime,
        chart=chart,
    )
    if note_spec is None:
        return None
    head_time = note_spec.get("time")
    note_type = note_spec.get("type")
    if not _is_finite_number(head_time) or note_type not in (0, 1, 2):
        return None

    def to_relative(value, tick, canvas_index):
        canvas_x = getCanvasPositionAt(
            chart,
            tick,
            index=canvas_index,
        )
        if canvas_x is None:
            return None
        return float(value) - float(canvas_x)

    head_x = float(position)
    if isAbsolutePosition:
        head_x = to_relative(position, head_time, head_canvas)
        if head_x is None:
            return None

    transparent = list(_TRANSPARENT)
    head_point = createLinePoint(
        head_time,
        head_x,
        head_canvas,
        0,
        transparent,
    )
    if head_point is None:
        return None
    line_points = [head_point]

    if note_type == 2:
        if not isinstance(isRealEndTime, bool) or not isinstance(
            isAbsoluteEndPosition,
            bool,
        ):
            return None
        end_time = note_spec.get("endtime")
        if not _is_finite_number(end_time):
            return None
        if endposition is not None and not _is_finite_number(endposition):
            return None
        if endcanvasindex is None:
            end_canvas = head_canvas
        else:
            end_canvas = _resolve_canvas_index(chart, endcanvasindex)
            if end_canvas is None:
                return None
        if endposition is None:
            if isAbsolutePosition:
                end_x = to_relative(position, end_time, end_canvas)
                if end_x is None:
                    return None
            else:
                end_x = head_x
        else:
            end_x = float(endposition)
            if isAbsoluteEndPosition:
                end_x = to_relative(end_x, end_time, end_canvas)
                if end_x is None:
                    return None

        if end_canvas != head_canvas:
            duration = float(end_time) - float(head_time)
            if duration <= 0.0:
                return None
            pre_tail_time = float(end_time) - min(1e-6, duration * 0.5)
            if not (
                float(head_time) < pre_tail_time < float(end_time)
            ):
                pre_tail_time = float(head_time) + duration * 0.5
            if not (
                float(head_time) < pre_tail_time < float(end_time)
            ):
                return None
            pre_tail_point = createLinePoint(
                pre_tail_time,
                end_x,
                end_canvas,
                0,
                transparent,
            )
            if pre_tail_point is None:
                return None
            line_points.append(pre_tail_point)

        end_point = createLinePoint(
            end_time,
            end_x,
            end_canvas,
            0,
            transparent,
        )
        if end_point is None:
            return None
        line_points.append(end_point)
    else:
        next_time = float(head_time) + _ISOLATED_NOTE_STEP
        next_x = head_x
        if isAbsolutePosition:
            next_x = to_relative(position, next_time, head_canvas)
            if next_x is None:
                return None
        next_point = createLinePoint(
            next_time,
            next_x,
            head_canvas,
            0,
            transparent,
        )
        if next_point is None:
            return None
        line_points.append(next_point)

    ring_point = createRingPoint(0.0, transparent)
    if ring_point is None:
        return None
    return addLine(
        chart,
        line_points,
        ring_point,
        notes=[note_spec],
    )


def addLineColorByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按线色覆盖规格 Dict 添加一个或多个线色节点。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        data = dict(spec)
        parent = _take_parent(data, ("lineindex", "lineIndex", "line_index"))
        if parent is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        inserted = _add_color_spec(chart, data, parent, addLineColor)
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(
            lambda p=parent, i=inserted: deleteLineColor(chart, p, i)
        )
    return sorted(failures)


def _riztime_spec(spec: dict) -> tuple[list, float, float, float, float] | None:
    colors = spec.get("colorsList")
    if not isinstance(colors, list) or len(colors) != 3:
        return None
    start = spec.get("start", 0.0)
    end = spec.get("end", 0.0)
    transtime = spec.get("transTime", spec.get("transtime", 0.5))
    checkpoint = spec.get("checkPoint", spec.get("checkpoint", 0.0))
    return colors, start, end, transtime, checkpoint


def _restore_riztime_placeholder(chart: dict, spec: dict) -> None:
    parsed = _riztime_spec(spec)
    if parsed is None:
        return
    colors, start, end, transtime, checkpoint = parsed
    addRiztime(
        chart,
        colors[0],
        colors[1],
        colors[2],
        start=start,
        end=end,
        transtime=transtime,
        checkpoint=checkpoint,
    )


def addRiztimeByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按 Riztime 规格 Dict 添加一个或多个 Riztime。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "start", 0.0)
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)

    placeholder_spec = None
    if getRiztimeCount(chart) == 1:
        candidate = getRiztime(chart, 0)
        if (
            isinstance(candidate, dict)
            and _is_finite_number(candidate.get("start"))
            and candidate.get("start") == candidate.get("end")
        ):
            placeholder_spec = candidate
    placeholder_replaced = False

    actions = []
    for original_index, spec in specs:
        parsed = _riztime_spec(spec)
        if parsed is None:
            if isFailAddAllowed:
                failures.append(original_index)
                continue
            _rollback(actions)
            if placeholder_replaced:
                _restore_riztime_placeholder(chart, placeholder_spec)
            return [original_index]
        colors, start, end, transtime, checkpoint = parsed
        inserted = addRiztime(
            chart,
            colors[0],
            colors[1],
            colors[2],
            start=start,
            end=end,
            transtime=transtime,
            checkpoint=checkpoint,
        )
        if inserted is None:
            if isFailAddAllowed:
                failures.append(original_index)
                continue
            _rollback(actions)
            if placeholder_replaced:
                _restore_riztime_placeholder(chart, placeholder_spec)
            return [original_index]
        # addRiztime() 返回 challengeTimes 的 0 基索引；setRiztime() /
        # deleteRiztime() 使用从 1 开始的 Riztime 索引，因此这里加 1。
        actions.append(lambda i=inserted: deleteRiztime(chart, i + 1))
        if placeholder_spec is not None:
            placeholder_replaced = True
    return sorted(failures)


def addBpmByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按 BPM 节点规格 Dict 添加一个或多个 BPM 变化节点。

    规格使用 ``getBpmShift()`` 的 ``{time, value, easeType}`` 格式：
    ``value`` 默认是相对基准 BPM 的倍率（``bpmShifts[].value``），
    ``easeType`` 会被忽略。可额外提供 ``isMultiply`` / ``isRealtime``
    覆盖默认行为。

    批内使用延迟计算写入节点，结束后调用一次全谱 ``refresh()``，重算所有
    受 BPM 影响的 ``floorPosition``。返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)

    checked = []
    for original_index, spec in specs:
        value = spec.get("value")
        if not _is_finite_number(value) or value <= 0:
            if isFailAddAllowed:
                failures.append(original_index)
                continue
            return [original_index]
        checked.append((original_index, spec))

    actions = []
    for original_index, spec in checked:
        inserted = addBpmShift(
            chart,
            spec.get("value"),
            spec.get("time"),
            isDelayCalculate=True,
            isRealtime=spec.get("isRealtime", False),
            isMultiply=spec.get("isMultiply", True),
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(lambda i=inserted: deleteBpmShift(chart, i))

    if actions:
        status = refresh(chart, mode="all", type="all")
        if status is None:
            if not isFailAddAllowed:
                _rollback(actions)
            return [-1]
    return sorted(failures)


def _add_canvas_positions(
    chart: dict,
    canvas_index: int,
    points: list,
) -> bool:
    indexed = _as_indexed_specs(points)
    if indexed is None:
        return False
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid:
        return False
    first = True
    for _, point in specs:
        time = point.get("time")
        value = point.get("value")
        ease = point.get("easeType", 0)
        if time == 0.0 and first:
            if setCanvasPosition(
                chart,
                canvas_index,
                0,
                time=0.0,
                position=value,
                easetype=ease,
            ) is None:
                return False
            first = False
            continue
        if addCanvasPosition(
            chart,
            canvas_index,
            time,
            position=value,
            easetype=ease,
        ) is None:
            return False
    return True


def _add_canvas_speeds(
    chart: dict,
    canvas_index: int,
    points: list,
) -> bool:
    indexed = _as_indexed_specs(points)
    if indexed is None:
        return False
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid:
        return False
    first = True
    for _, point in specs:
        time = point.get("time")
        value = point.get("value")
        if time == 0.0 and first:
            if setCanvasSpeed(
                chart,
                canvas_index,
                0,
                time=0.0,
                speed=value,
                isChangeZeroSpeed=False,
            ) is None:
                return False
            first = False
            continue
        if addCanvasSpeed(
            chart,
            canvas_index,
            time,
            speed=value,
            isChangeZeroSpeed=False,
        ) is None:
            return False
    return True


def addCanvasByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按画布规格 Dict 添加一个或多个画布。

    画布规格可包含 ``xPositionKeyPoints`` 与 ``speedKeyPoints``；它们会按
    ``time`` 排序后写入。画布本身追加到末尾，规格中的 ``index`` 会被忽略。
    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    specs = _as_indexed_specs(dictlist)
    if specs is None:
        return [-1]
    failures = []
    actions = []
    for original_index, spec in specs:
        x_points = spec.get("xPositionKeyPoints")
        speed_points = spec.get("speedKeyPoints")
        if x_points is not None and (
            not isinstance(x_points, list) or not x_points
        ):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        if speed_points is not None and (
            not isinstance(speed_points, list) or not speed_points
        ):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue

        canvas_index = addCanvas(chart)
        if not isinstance(canvas_index, int):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        local_actions = [lambda i=canvas_index: deleteCanvas(chart, i)]

        if x_points is not None and not _add_canvas_positions(
            chart,
            canvas_index,
            x_points,
        ):
            if _handle_failure(
                actions,
                local_actions,
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        if speed_points is not None and not _add_canvas_speeds(
            chart,
            canvas_index,
            speed_points,
        ):
            if _handle_failure(
                actions,
                local_actions,
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.extend(local_actions)
    return sorted(failures)


def addCanvasPositionByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按画布横向移动节点规格 Dict 添加节点。

    每个 Dict 可包含 ``canvasindex`` / ``canvasIndex``；缺省为最后一条画布。
    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        data = dict(spec)
        parent = _take_parent(
            data,
            ("canvasindex", "canvasIndex", "canvas_index"),
        )
        if parent is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        inserted = addCanvasPosition(
            chart,
            parent,
            data.get("time"),
            position=data.get("value"),
            easetype=data.get("easeType", 0),
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(
            lambda p=parent, i=inserted: deleteCanvasPosition(chart, p, i)
        )
    return sorted(failures)


def addCanvasSpeedByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按画布速度节点规格 Dict 添加节点。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        data = dict(spec)
        parent = _take_parent(
            data,
            ("canvasindex", "canvasIndex", "canvas_index"),
        )
        if parent is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        inserted = addCanvasSpeed(
            chart,
            parent,
            data.get("time"),
            speed=data.get("value"),
            isChangeZeroSpeed=False,
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(
            lambda p=parent, i=inserted: deleteCanvasSpeed(chart, p, i)
        )
    return sorted(failures)


def addCameraPositionByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按摄像机横向移动节点规格 Dict 添加节点。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        inserted = addCameraPosition(
            chart,
            spec.get("time"),
            position=spec.get("value"),
            easetype=spec.get("easeType", 0),
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(lambda i=inserted: deleteCameraPosition(chart, i))
    return sorted(failures)


def addCameraScaleByDict(
    chart: dict,
    dictlist: dict | list,
    isFailAddAllowed: bool = False,
) -> list[int]:
    """按摄像机缩放节点规格 Dict 添加节点。

    返回值规则与 :func:`addLineByDict` 相同。
    """
    if not isinstance(chart, dict):
        return [-1]
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return [-1]
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return [invalid[0]]
    failures = list(invalid)
    actions = []
    for original_index, spec in specs:
        inserted = addCameraScale(
            chart,
            spec.get("time"),
            scale=spec.get("value"),
            easetype=spec.get("easeType", 0),
        )
        if inserted is None:
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return [original_index]
            continue
        actions.append(lambda i=inserted: deleteCameraScale(chart, i))
    return sorted(failures)
