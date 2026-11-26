"""高级批量插入、复制、缓动、颜色替换与绘图工具。

本模块及 ``advanced_copy`` / ``advanced_ease`` / ``advanced_draw`` 只调用
base / chart / query 暴露的公开函数，不直接修改谱面 dict。
批量函数统一返回失败元素的原始索引列表；默认 ``isFailAddAllowed=False``
为原子模式，任一失败会回退整批已修改内容。
"""

from __future__ import annotations

from ._exception_wrapper import install_exception_api
from ._failure import fail, last_failure

import math

from .base import refresh
from .chart import (
    _chart_failure,
    _index_failure,
    _structure_failure,
    _type_failure,
    _value_failure,
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
    setLineColor,
    setLinePoint,
    setNormalTheme,
    setRingPoint,
    setRiztime,
)
from .query import (
    getCanvasCount,
    getCanvasPositionAt,
    getLine,
    getLineCount,
    getRiztime,
    getRiztimeCount,
    getTheme,
    getTickAt,
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
from .advanced_mirror import xMirrorLine

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
    "xMirrorLine",
    "transColor",
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
        return _type_failure([-1], "chart", chart, "dict")
    specs = _as_indexed_specs(dictlist)
    if specs is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "线规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是线规格 dict 或 dict 列表",
        )
    if index is not None and (
        not isinstance(index, int) or isinstance(index, bool)
    ):
        return _type_failure([-1], "index", index, "int 或 None")
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
                return fail(
                    [original_index],
                    f"第 {original_index} 条线规格的 linePoints 必须是 list",
                    parameter="dictlist",
                    actual=line_points,
                    expected="linePoints 为 list",
                    path=["dictlist", original_index, "linePoints"],
                    failed_indices=[original_index],
                )
            continue
        if not isinstance(ring_points, (list, dict)):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return fail(
                    [original_index],
                    f"第 {original_index} 条线规格的 judgeRingColor 必须是 dict 或 list",
                    parameter="dictlist",
                    actual=ring_points,
                    expected="judgeRingColor 为 dict 或 list",
                    path=["dictlist", original_index, "judgeRingColor"],
                    failed_indices=[original_index],
                )
            continue
        if notes is not None and not isinstance(notes, list):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return fail(
                    [original_index],
                    f"第 {original_index} 条线规格的 notes 必须是 list 或 None",
                    parameter="dictlist",
                    actual=notes,
                    expected="notes 为 list 或 None",
                    path=["dictlist", original_index, "notes"],
                    failed_indices=[original_index],
                )
            continue
        if line_colors is not None and not isinstance(line_colors, list):
            if _handle_failure(
                actions,
                [],
                original_index,
                isFailAddAllowed,
                failures,
            ):
                return fail(
                    [original_index],
                    f"第 {original_index} 条线规格的 lineColor 必须是 list 或 None",
                    parameter="dictlist",
                    actual=line_colors,
                    expected="lineColor 为 list 或 None",
                    path=["dictlist", original_index, "lineColor"],
                    failed_indices=[original_index],
                )
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
                if last_failure() is None:
                    return fail(
                        [original_index],
                        f"第 {original_index} 条线规格插入失败",
                        parameter="dictlist",
                        actual=spec,
                        expected="符合 addLine 要求的线规格",
                        path=["dictlist", original_index],
                        failed_indices=[original_index],
                    )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 项规格缺少有效的 lineindex/lineIndex",
                    parameter="dictlist",
                    actual=spec,
                    expected="包含有效整数 lineindex/lineIndex 的规格",
                    path=["dictlist", original_index],
                    failed_indices=[original_index],
                )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 项规格缺少有效的 lineindex/lineIndex",
                    parameter="dictlist",
                    actual=spec,
                    expected="包含有效整数 lineindex/lineIndex 的规格",
                    path=["dictlist", original_index],
                    failed_indices=[original_index],
                )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 项规格缺少有效的 lineindex/lineIndex",
                    parameter="dictlist",
                    actual=spec,
                    expected="包含有效整数 lineindex/lineIndex 的规格",
                    path=["dictlist", original_index],
                    failed_indices=[original_index],
                )
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
        return _chart_failure()
    if not _is_finite_number(time) or float(time) < 0.0:
        return _value_failure(None, "time", time, "有限数且 >= 0")
    if not _is_finite_number(position):
        return _type_failure(None, "position", position, "有限数")
    if not isinstance(isRealTime, bool):
        return _type_failure(None, "isRealTime", isRealTime, "bool")
    if not isinstance(isAbsolutePosition, bool):
        return _type_failure(
            None,
            "isAbsolutePosition",
            isAbsolutePosition,
            "bool",
        )

    head_canvas = _resolve_canvas_index(chart, canvasindex)
    if head_canvas is None:
        return fail(
            None,
            f"画布索引 canvasindex={canvasindex!r} 不存在",
            code="canvas.not_found",
            parameter="canvasindex",
            actual=canvasindex,
            expected="有效的画布索引",
            path=["canvasMoves"],
        )

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
        return _structure_failure(
            None,
            ["notes"],
            "有效 time 与 type 的 Note 规格",
            actual=note_spec,
            message="createNote 返回的 Note 规格缺少有效 time/type",
        )

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
            return fail(
                None,
                "无法把绝对头部位置换算为相对画布中线的 x",
                code="canvas.position_unavailable",
                parameter="position",
                actual=position,
                expected="目标画布在头部时间有有效位置",
                path=["canvasMoves", head_canvas, "xPositionKeyPoints"],
            )

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
        if not isinstance(isRealEndTime, bool):
            return _type_failure(None, "isRealEndTime", isRealEndTime, "bool")
        if not isinstance(isAbsoluteEndPosition, bool):
            return _type_failure(
                None,
                "isAbsoluteEndPosition",
                isAbsoluteEndPosition,
                "bool",
            )
        end_time = note_spec.get("endtime")
        if not _is_finite_number(end_time):
            return _structure_failure(
                None,
                ["notes", "endtime"],
                "Hold 的有效 endtime",
                actual=end_time,
            )
        if endposition is not None and not _is_finite_number(endposition):
            return _type_failure(None, "endposition", endposition, "有限数或 None")
        if endcanvasindex is None:
            end_canvas = head_canvas
        else:
            end_canvas = _resolve_canvas_index(chart, endcanvasindex)
            if end_canvas is None:
                return fail(
                    None,
                    f"尾部画布索引 endcanvasindex={endcanvasindex!r} 不存在",
                    code="canvas.not_found",
                    parameter="endcanvasindex",
                    actual=endcanvasindex,
                    expected="有效的画布索引",
                    path=["canvasMoves"],
                )
        if endposition is None:
            if isAbsolutePosition:
                end_x = to_relative(position, end_time, end_canvas)
                if end_x is None:
                    return fail(
                        None,
                        "无法把绝对尾部位置换算为相对画布中线的 x",
                        code="canvas.position_unavailable",
                        parameter="endposition",
                        actual=endposition,
                        expected="目标画布在尾部时间有有效位置",
                        path=["canvasMoves", end_canvas, "xPositionKeyPoints"],
                    )
            else:
                end_x = head_x
        else:
            end_x = float(endposition)
            if isAbsoluteEndPosition:
                end_x = to_relative(end_x, end_time, end_canvas)
                if end_x is None:
                    return fail(
                        None,
                        "无法把绝对尾部 endposition 换算为相对画布中线的 x",
                        code="canvas.position_unavailable",
                        parameter="endposition",
                        actual=endposition,
                        expected="目标画布在尾部时间有有效位置",
                        path=["canvasMoves", end_canvas, "xPositionKeyPoints"],
                    )

        if end_canvas != head_canvas:
            duration = float(end_time) - float(head_time)
            if duration <= 0.0:
                return _value_failure(
                    None,
                    "endtime",
                    end_time,
                    f"> head time（{head_time!r}）",
                    message=(
                        f"Hold 尾部时间 {end_time!r} 必须大于头部时间 "
                        f"{head_time!r}"
                    ),
                    path=["notes", "endtime"],
                    code="time.out_of_range",
                )
            pre_tail_time = float(end_time) - min(1e-6, duration * 0.5)
            if not (
                float(head_time) < pre_tail_time < float(end_time)
            ):
                pre_tail_time = float(head_time) + duration * 0.5
            if not (
                float(head_time) < pre_tail_time < float(end_time)
            ):
                return fail(
                    None,
                    "无法在 Hold 头尾之间构造有效的预尾节点时间",
                    code="time.invalid",
                    actual={
                        "head_time": head_time,
                        "pre_tail_time": pre_tail_time,
                        "end_time": end_time,
                    },
                    expected="head_time < pre_tail_time < end_time",
                    path=["linePoints"],
                )
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
                return fail(
                    None,
                    "无法把绝对头部位置换算为下一节点的相对 x",
                    code="canvas.position_unavailable",
                    parameter="position",
                    actual=position,
                    expected="目标画布在下一节点时间有有效位置",
                    path=["canvasMoves", head_canvas, "xPositionKeyPoints"],
                )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 项规格缺少有效的 lineindex/lineIndex",
                    parameter="dictlist",
                    actual=spec,
                    expected="包含有效整数 lineindex/lineIndex 的规格",
                    path=["dictlist", original_index],
                    failed_indices=[original_index],
                )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "start", 0.0)
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项 Riztime 规格缺少有效的 start",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 start 的 Riztime 规格",
            path=["dictlist", invalid[0], "start"],
            failed_indices=[invalid[0]],
        )
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
            return fail(
                [original_index],
                f"第 {original_index} 项 Riztime 规格的 colorsList 或时间字段非法",
                parameter="dictlist",
                actual=spec,
                expected="包含 3 色 colorsList 和有效 start/end/transTime/checkPoint",
                path=["dictlist", original_index],
                failed_indices=[original_index],
            )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
    failures = list(invalid)

    checked = []
    for original_index, spec in specs:
        value = spec.get("value")
        if not _is_finite_number(value) or value <= 0:
            if isFailAddAllowed:
                failures.append(original_index)
                continue
            return fail(
                [original_index],
                f"第 {original_index} 项 BPM 规格的 value={value!r} 不是有限正数",
                parameter="dictlist",
                actual=value,
                expected="有限数且 > 0",
                path=["dictlist", original_index, "value"],
                failed_indices=[original_index],
            )
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
            return fail(
                [-1],
                "批量添加 BPM 节点后 refresh 失败，已回退",
                parameter="dictlist",
                actual=len(actions),
                expected="可重算 floorPosition 的谱面结构",
                path=["bpmShifts", "canvasMoves", "lines"],
                failed_indices=[-1],
            )
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
        return _type_failure([-1], "chart", chart, "dict")
    specs = _as_indexed_specs(dictlist)
    if specs is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "画布规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是画布规格 dict 或 dict 列表",
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 个画布规格的 xPositionKeyPoints 必须是非空 list",
                    parameter="dictlist",
                    actual=x_points,
                    expected="非空关键点列表或 None",
                    path=["dictlist", original_index, "xPositionKeyPoints"],
                    failed_indices=[original_index],
                )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 个画布规格的 speedKeyPoints 必须是非空 list",
                    parameter="dictlist",
                    actual=speed_points,
                    expected="非空关键点列表或 None",
                    path=["dictlist", original_index, "speedKeyPoints"],
                    failed_indices=[original_index],
                )
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
                if last_failure() is None:
                    return fail(
                        [original_index],
                        f"第 {original_index} 个画布规格添加画布失败",
                        parameter="dictlist",
                        actual=spec,
                        expected="可添加的画布",
                        path=["canvasMoves"],
                        failed_indices=[original_index],
                    )
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
                if last_failure() is None:
                    return fail(
                        [original_index],
                        f"第 {original_index} 个画布规格的 xPositionKeyPoints 写入失败",
                        parameter="dictlist",
                        actual=x_points,
                        expected="有效且 time 非递减的 xPositionKeyPoints",
                        path=["dictlist", original_index, "xPositionKeyPoints"],
                        failed_indices=[original_index],
                    )
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
                if last_failure() is None:
                    return fail(
                        [original_index],
                        f"第 {original_index} 个画布规格的 speedKeyPoints 写入失败",
                        parameter="dictlist",
                        actual=speed_points,
                        expected="有效且 time 非递减的 speedKeyPoints",
                        path=["dictlist", original_index, "speedKeyPoints"],
                        failed_indices=[original_index],
                    )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 项规格缺少有效的 canvasindex/canvasIndex",
                    parameter="dictlist",
                    actual=spec,
                    expected="包含有效整数 canvasindex/canvasIndex 的规格",
                    path=["dictlist", original_index],
                    failed_indices=[original_index],
                )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
                return fail(
                    [original_index],
                    f"第 {original_index} 项规格缺少有效的 canvasindex/canvasIndex",
                    parameter="dictlist",
                    actual=spec,
                    expected="包含有效整数 canvasindex/canvasIndex 的规格",
                    path=["dictlist", original_index],
                    failed_indices=[original_index],
                )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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
        return _type_failure([-1], "chart", chart, "dict")
    indexed = _as_indexed_specs(dictlist)
    if indexed is None:
        return _structure_failure(
            [-1],
            ["dictlist"],
            "规格 dict 或 dict 列表",
            actual=type(dictlist).__name__,
            message="参数 dictlist 必须是规格 dict 或 dict 列表",
        )
    specs, invalid = _sorted_indexed_specs(indexed, "time")
    if invalid and not isFailAddAllowed:
        return fail(
            [invalid[0]],
            f"第 {invalid[0]} 项规格缺少有效的 time",
            parameter="dictlist",
            actual=indexed[invalid[0]][1] if invalid[0] < len(indexed) else None,
            expected="包含有限数 time 的规格 dict",
            path=["dictlist", invalid[0], "time"],
            failed_indices=[invalid[0]],
        )
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


_TRANS_LINE_TYPES = ("linePoint", "lineColor", "ringColor")
_TRANS_THEME_TYPES = ("normalTheme", "riztimeTheme")
_TRANS_TYPES = (_TRANS_LINE_TYPES + _TRANS_THEME_TYPES)


def _parse_trans_color(value: object) -> tuple[int, int, int, int] | None:
    """用现有公开构造函数解析一个颜色，返回规范化 RGBA。"""
    spec = createLinePoint(0.0, 0.0, 0, 0, value)
    if not isinstance(spec, dict):
        return None
    color = spec.get("color")
    if not isinstance(color, list) or len(color) != 4:
        return None
    return tuple(color)


def _parse_trans_color_list(value: object) -> list[tuple[int, int, int, int]] | None:
    """解析单个颜色或颜色列表。"""
    if isinstance(value, str):
        parsed = _parse_trans_color(value)
        return [parsed] if parsed is not None else None
    if not isinstance(value, list) or not value:
        return None

    single = _parse_trans_color(value)
    if single is not None:
        return [single]

    result = []
    for item in value:
        parsed = _parse_trans_color(item)
        if parsed is None:
            return None
        result.append(parsed)
    return result


def _parse_trans_types(value: object) -> list[str] | None:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list) and value and all(
        isinstance(item, str) for item in value
    ):
        values = list(value)
    else:
        return None

    result = []
    for item in values:
        if item not in _TRANS_TYPES:
            return None
        if item not in result:
            result.append(item)
    return result


def _trans_time_range(
    chart: dict,
    starttime: object,
    endtime: object,
    isRealStartTime: object,
    isRealEndTime: object,
) -> tuple[float, float | None] | None:
    if not isinstance(isRealStartTime, bool) or not isinstance(isRealEndTime, bool):
        return None
    if not _is_finite_number(starttime) or float(starttime) < 0.0:
        return None
    if endtime is not None and (
        not _is_finite_number(endtime) or float(endtime) < 0.0
    ):
        return None

    if isRealStartTime:
        start = getTickAt(chart, float(starttime))
    else:
        start = float(starttime)
    if start is None:
        return None

    if endtime is None:
        return (start, None)

    if isRealEndTime:
        end = getTickAt(chart, float(endtime))
    else:
        end = float(endtime)
    if end is None or end < start:
        return None
    return (start, end)


def _trans_time_match(time: float, start: float, end: float | None) -> bool:
    return time >= start and (end is None or time <= end)


def _trans_color_pair(
    start_color: object,
    end_color: object,
    color_map: dict,
) -> tuple[tuple, tuple, bool]:
    start = tuple(start_color)
    end = tuple(end_color)
    new_start = color_map.get(start, start)
    new_end = color_map.get(end, end)
    return new_start, new_end, (new_start != start or new_end != end)


def _trans_line_color_changes(
    chart: dict,
    selected_types: list[str],
    color_map: dict,
    start: float,
    end: float | None,
) -> tuple[list[tuple], dict[str, set]] | None:
    line_count = getLineCount(chart)
    if not _is_int(line_count):
        return None

    plans = []
    indexes = {kind: set() for kind in _TRANS_LINE_TYPES if kind in selected_types}

    for line_index in range(line_count):
        line = getLine(chart, line_index)
        if not isinstance(line, dict):
            return None

        if "linePoint" in indexes:
            points = line.get("linePoints")
            if not isinstance(points, list):
                return None
            for point_index, point in enumerate(points):
                if not isinstance(point, dict):
                    return None
                point_time = point.get("time")
                if not _is_finite_number(point_time):
                    return None
                if not _trans_time_match(float(point_time), start, end):
                    continue
                old_color = tuple(point.get("color", []))
                if len(old_color) != 4:
                    return None
                new_color = color_map.get(old_color)
                if new_color is None or new_color == old_color:
                    continue
                plans.append(
                    ("linePoint", line_index, point_index, old_color, new_color)
                )
                indexes["linePoint"].add((line_index, point_index))

        if "lineColor" in indexes:
            color_nodes = line.get("lineColor")
            if not isinstance(color_nodes, list):
                return None
            for color_index, node in enumerate(color_nodes):
                if not isinstance(node, dict):
                    return None
                node_time = node.get("time")
                if not _is_finite_number(node_time):
                    return None
                if not _trans_time_match(float(node_time), start, end):
                    continue
                old_start = node.get("startColor")
                old_end = node.get("endColor")
                if not isinstance(old_start, list) or not isinstance(old_end, list):
                    return None
                new_start, new_end, changed = _trans_color_pair(
                    old_start,
                    old_end,
                    color_map,
                )
                if not changed:
                    continue
                plans.append(
                    (
                        "lineColor",
                        line_index,
                        color_index,
                        tuple(old_start),
                        tuple(old_end),
                        new_start,
                        new_end,
                    )
                )
                indexes["lineColor"].add((line_index, color_index))

        if "ringColor" in indexes:
            ring_nodes = line.get("judgeRingColor")
            if not isinstance(ring_nodes, list):
                return None
            for ring_index, node in enumerate(ring_nodes):
                if not isinstance(node, dict):
                    return None
                node_time = node.get("time")
                if not _is_finite_number(node_time):
                    return None
                if not _trans_time_match(float(node_time), start, end):
                    continue
                old_start = node.get("startColor")
                old_end = node.get("endColor")
                if not isinstance(old_start, list) or not isinstance(old_end, list):
                    return None
                new_start, new_end, changed = _trans_color_pair(
                    old_start,
                    old_end,
                    color_map,
                )
                if not changed:
                    continue
                plans.append(
                    (
                        "ringColor",
                        line_index,
                        ring_index,
                        tuple(old_start),
                        tuple(old_end),
                        new_start,
                        new_end,
                    )
                )
                indexes["ringColor"].add((line_index, ring_index))

    return plans, indexes


def _map_theme_colors(
    colors: object,
    color_map: dict,
) -> tuple[list[tuple], list[int]] | None:
    if not isinstance(colors, list) or len(colors) != 3:
        return None
    result = []
    changed = []
    for color_index, color in enumerate(colors):
        if not isinstance(color, list) or len(color) != 4:
            return None
        old_color = tuple(color)
        new_color = color_map.get(old_color, old_color)
        result.append(new_color)
        if new_color != old_color:
            changed.append(color_index)
    return result, changed


def _trans_theme_color_changes(
    chart: dict,
    selected_types: list[str],
    color_map: dict,
    start: float,
    end: float | None,
) -> tuple[list[tuple], set[tuple[int, int]]] | None:
    plans = []
    indexes: set[tuple[int, int]] = set()

    if "normalTheme" in selected_types:
        themes = getTheme(chart, 0, -1)
        if not isinstance(themes, list) or not themes:
            return None
        colors = themes[0].get("colorsList") if isinstance(themes[0], dict) else None
        mapped = _map_theme_colors(colors, color_map)
        if mapped is None:
            return None
        new_colors, changed = mapped
        if changed:
            plans.append(("normalTheme", tuple(tuple(c) for c in colors), new_colors))
            indexes.update((0, color_index) for color_index in changed)

    if "riztimeTheme" in selected_types:
        riztimes = getRiztime(chart, 0, -1)
        if not isinstance(riztimes, list):
            return None
        for riztime in riztimes:
            if not isinstance(riztime, dict):
                return None
            theme_index = riztime.get("themeIndex")
            theme_start = riztime.get("start")
            theme_end = riztime.get("end")
            if (
                not _is_int(theme_index)
                or not _is_finite_number(theme_start)
                or not _is_finite_number(theme_end)
            ):
                return None
            if float(theme_start) < start:
                continue
            if end is not None and float(theme_end) > end:
                continue
            colors = riztime.get("colorsList")
            mapped = _map_theme_colors(colors, color_map)
            if mapped is None:
                return None
            new_colors, changed = mapped
            if not changed:
                continue
            old_colors = tuple(tuple(c) for c in colors)
            plans.append(("riztimeTheme", theme_index, old_colors, new_colors))
            indexes.update(
                (theme_index, color_index) for color_index in changed
            )

    return plans, indexes


def _apply_trans_plans(chart: dict, plans: list[tuple]) -> bool:
    actions = []
    try:
        for plan in plans:
            kind = plan[0]
            if kind == "linePoint":
                _, line_index, point_index, old_color, new_color = plan
                if setLinePoint(
                    chart,
                    line_index,
                    point_index,
                    color=list(new_color),
                ) is None:
                    raise RuntimeError("line point color set failed")
                actions.append(
                    lambda line_index=line_index, point_index=point_index,
                    old_color=old_color: setLinePoint(
                        chart,
                        line_index,
                        point_index,
                        color=list(old_color),
                    )
                )
            elif kind in ("lineColor", "ringColor"):
                (
                    _,
                    line_index,
                    node_index,
                    old_start,
                    old_end,
                    new_start,
                    new_end,
                ) = plan
                setter = setLineColor if kind == "lineColor" else setRingPoint
                if setter(
                    chart,
                    line_index,
                    node_index,
                    startcolor=list(new_start),
                    endcolor=list(new_end),
                ) is None:
                    raise RuntimeError(f"{kind} set failed")
                actions.append(
                    lambda setter=setter, line_index=line_index,
                    node_index=node_index, old_start=old_start,
                    old_end=old_end: setter(
                        chart,
                        line_index,
                        node_index,
                        startcolor=list(old_start),
                        endcolor=list(old_end),
                    )
                )
            elif kind == "normalTheme":
                _, old_colors, new_colors = plan
                if setNormalTheme(
                    chart,
                    *[list(color) for color in new_colors],
                ) is None:
                    raise RuntimeError("normal theme set failed")
                actions.append(
                    lambda old_colors=old_colors: setNormalTheme(
                        chart,
                        *[list(color) for color in old_colors],
                    )
                )
            elif kind == "riztimeTheme":
                _, theme_index, old_colors, new_colors = plan
                if setRiztime(
                    chart,
                    theme_index,
                    *[list(color) for color in new_colors],
                ) is None:
                    raise RuntimeError("riztime theme set failed")
                actions.append(
                    lambda theme_index=theme_index,
                    old_colors=old_colors: setRiztime(
                        chart,
                        theme_index,
                        *[list(color) for color in old_colors],
                    )
                )
            else:
                raise RuntimeError("unknown transColor plan")
    except Exception:
        for action in reversed(actions):
            try:
                action()
            except Exception:
                pass
        return False
    return True


def transColor(
    chart: dict,
    origioncolorlist: list | str,
    targetcolorlist: list | str,
    type: list | str = "linePoint",
    starttime: float = 0.0,
    endtime: float | None = None,
    isRealStartTime: bool = False,
    isRealEndTime: bool = False,
) -> list[dict] | None:
    """按颜色映射替换谱面中的颜色节点。

    ``origioncolorlist`` / ``targetcolorlist`` 是单个颜色或颜色列表；
    两种列表长度必须相等。颜色替换按列表索引一一对应，使用规范化后的
    RGBA 精确匹配。``type`` 指定替换范围，返回的主题索引统一使用
    ``"theme"`` 类型。

    线节点按节点时间过滤；Riztime 主题只有整个时间区间都位于
    ``[starttime, endtime]`` 内才会替换；普通主题不受时间范围影响。
    任一结构、参数或写入失败都会回退全部修改并返回 ``None``。
    """
    if not isinstance(chart, dict):
        return _chart_failure()

    origins = _parse_trans_color_list(origioncolorlist)
    targets = _parse_trans_color_list(targetcolorlist)
    if origins is None:
        return fail(
            None,
            "参数 origioncolorlist 不是可解析的颜色或颜色列表",
            code="color.invalid",
            parameter="origioncolorlist",
            actual=origioncolorlist,
            expected="颜色或等长颜色列表",
        )
    if targets is None:
        return fail(
            None,
            "参数 targetcolorlist 不是可解析的颜色或颜色列表",
            code="color.invalid",
            parameter="targetcolorlist",
            actual=targetcolorlist,
            expected="颜色或等长颜色列表",
        )
    if len(origins) != len(targets):
        return fail(
            None,
            f"origioncolorlist 长度 {len(origins)} 与 targetcolorlist 长度 {len(targets)} 不一致",
            code="color.length_mismatch",
            parameter="origioncolorlist/targetcolorlist",
            actual=[len(origins), len(targets)],
            expected="两者长度相等",
        )
    if len(set(origins)) != len(origins):
        return fail(
            None,
            "origioncolorlist 中存在重复颜色",
            code="color.duplicate",
            parameter="origioncolorlist",
            actual=origioncolorlist,
            expected="颜色列表中没有重复项",
        )

    selected_types = _parse_trans_types(type)
    if selected_types is None:
        return fail(
            None,
            f"参数 type={type!r} 不是有效的替换范围",
            code="trans.type_invalid",
            parameter="type",
            actual=type,
            expected="linePoint/lineColor/ringColor/normalTheme/riztimeTheme 或其列表",
        )

    time_range = _trans_time_range(
        chart,
        starttime,
        endtime,
        isRealStartTime,
        isRealEndTime,
    )
    if time_range is None:
        return fail(
            None,
            "时间范围参数非法或无法换算为 tick",
            code="time.invalid",
            parameter="starttime/endtime",
            actual=[starttime, endtime],
            expected="有限数且 >= 0，endtime 不小于 starttime",
            path=["bpmShifts"],
        )
    start, end = time_range

    color_map = dict(zip(origins, targets))
    plans = []
    indexes = {}

    line_types = [kind for kind in selected_types if kind in _TRANS_LINE_TYPES]
    if line_types:
        collected = _trans_line_color_changes(
            chart,
            line_types,
            color_map,
            start,
            end,
        )
        if collected is None:
            return fail(
                None,
                "无法收集线节点/线色/判定环颜色替换计划，谱面结构非法",
                code="trans.line_structure_invalid",
                parameter="type",
                actual=line_types,
                expected="线节点、线色和判定环结构合法",
                path=["lines"],
            )
        line_plans, line_indexes = collected
        plans.extend(line_plans)
        indexes.update(line_indexes)

    theme_types = [kind for kind in selected_types if kind in _TRANS_THEME_TYPES]
    if theme_types:
        collected = _trans_theme_color_changes(
            chart,
            theme_types,
            color_map,
            start,
            end,
        )
        if collected is None:
            return fail(
                None,
                "无法收集主题颜色替换计划，谱面主题结构非法",
                code="trans.theme_structure_invalid",
                parameter="type",
                actual=theme_types,
                expected="themes 与 challengeTimes 结构合法",
                path=["themes", "challengeTimes"],
            )
        theme_plans, theme_indexes = collected
        plans.extend(theme_plans)
        indexes["theme"] = theme_indexes

    if not plans:
        return []

    order = []
    for selected in selected_types:
        group = "theme" if selected in _TRANS_THEME_TYPES else selected
        if group not in order:
            order.append(group)

    result = []
    for group in order:
        group_indexes = indexes.get(group)
        if not group_indexes:
            continue
        result.append(
            {
                "type": group,
                "indexlist": [list(index) for index in sorted(group_indexes)],
            }
        )

    if not _apply_trans_plans(chart, plans):
        return fail(
            None,
            "应用颜色替换计划失败，已回退全部修改",
            code="trans.apply_failed",
            parameter="type",
            actual=selected_types,
            expected="所有颜色节点均可写回",
            path=["lines", "themes"],
        )
    return result


install_exception_api(globals())
