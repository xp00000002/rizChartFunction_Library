# advanced 模块函数说明

[← 返回总览](README.md)

`advanced.py` 提供按规格 Dict 批量插入、跨谱面复制对象、批量修改缓动和绘图的组合函数。所有函数只调用
`base.py` / `chart.py` / `query.py` 暴露的公开函数，不直接修改谱面 dict。

## 使用约定

- 本模块及 `advanced_copy.py` / `advanced_ease.py` / `advanced_draw.py` /
  `advanced_font.py` 只调用 `base.py` / `chart.py` / `query.py` 暴露的公开函数，
  不直接修改谱面 dict。
- `chart` 均为谱面 dict。索引参数默认支持负数从末尾计算；具体边界规则见各函数。
- 时间参数默认是 tick；`isRealTime` / `isRealEndTime` 等为 `True` 时按 BPM
  时间轴换算为 tick。
- 颜色参数支持 HEX / RGB(A) 列表；函数返回的规格中统一使用 RGBA 列表。
- 返回值分三类：
  - 批量插入、复制、缓动函数：成功返回 `[]`，失败返回失败索引列表；整体输入
    非法通常返回 `[-1]`。具体规则以对应章节为准。
  - 绘图、文字函数：成功返回新建线索引列表，失败返回 `None`。
  - 单个对象或查询类辅助函数：成功返回对象/数值，失败返回 `None`。

## 目录

- [插入函数](#插入函数)
  - [插入函数通用规则](#插入函数通用规则)
  - [`addLineByDict()`](#addlinebydict)
  - [`addLinePointByDict()`](#addlinepointbydict)
  - [`addRingPointByDict()`](#addringpointbydict)
  - [`addLineColorByDict()`](#addlinecolorbydict)
  - [`addNoteByDict()`](#addnotebydict)
  - [`addIsolatedNote()`](#addisolatednote)
  - [`addRiztimeByDict()`](#addriztimebydict)
  - [`addBpmByDict()`](#addbpmbydict)
  - [`addCanvasByDict()`](#addcanvasbydict)
  - [`addCanvasPositionByDict()`](#addcanvaspositionbydict)
  - [`addCanvasSpeedByDict()`](#addcanvasspeedbydict)
  - [`addCameraPositionByDict()`](#addcamerapositionbydict)
  - [`addCameraScaleByDict()`](#addcamerascalebydict)
- [复制函数](#复制函数)
  - [`copyLine()`](#copyline)
  - [`copyLinePoint()`](#copylinepoint)
  - [`copyRingPoint()`](#copyringpoint)
  - [`copyLineColor()`](#copylinecolor)
  - [`copyNote()`](#copynote)
  - [`copyBpmShift()`](#copybpmshift)
  - [`copyRiztime()`](#copyriztime)
  - [`copyCanvas()`](#copycanvas)
  - [`copyCanvasPosition()`](#copycanvasposition)
  - [`copyCanvasSpeed()`](#copycanvasspeed)
  - [`copyCamera()`](#copycamera)
  - [`copyCameraPosition()`](#copycameraposition)
  - [`copyCameraScale()`](#copycamerascale)
- [缓动函数](#缓动函数)
  - [缓动函数通用规则](#缓动函数通用规则)
  - [`setBpmShiftEase()`](#setbpmshiftease)
  - [`setLinePointPositionEase()`](#setlinepointpositionease)
  - [`setLinePointColorEase()`](#setlinepointcolorease)
  - [`setLinePointColorByList()`](#setlinepointcolorbylist)
  - [`setRingColorEase()`](#setringcolorease)
  - [`setLineColorEase()`](#setlinecolorease)
  - [`setCanvasPositionEase()`](#setcanvaspositionease)
  - [`setCanvasSpeedEase()`](#setcanvasspeedease)
  - [`setCameraPositionEase()`](#setcamerapositionease)
  - [`setCameraScaleEase()`](#setcamerascaleease)
- [绘图与文字函数](#绘图与文字函数)
  - [`drawPolygon()`](#drawpolygon)
  - [`drawEllipse()`](#drawellipse)
  - [`getClosedRegion()`](#getclosedregion)
  - [`drawText()`](#drawtext)
  - [`drawThinText()`](#drawthintext)
- [示例](#示例)

## 插入函数

本组函数按规格 Dict 或对象参数向谱面插入新对象。

### 插入函数通用规则

- `dictlist` 可以是单个规格 Dict，也可以是多个规格 Dict 组成的列表。
- 列表形式表示批量导入；空列表视为成功，返回 `[]`。
- 批量插入函数统一返回 `list[int]`：全部成功时为空列表 `[]`，否则为失败规格在
  **原始输入列表**中的索引。
- `isFailAddAllowed=False`（默认）为原子模式：任一规格插入失败时，回退本批
  全部插入，返回 `[失败索引]`。
- `isFailAddAllowed=True` 时跳过失败规格，继续插入其余规格，返回所有失败索引
  （升序）。
- 失败规格自身已经插入的部分也会回退；`True` 模式下已成功的其它规格保留。
- 整体输入非法（`chart` / `dictlist` / `index` 等）返回 `[-1]`。
- 除 `addLineByDict()` 外，带 `time` / `start` 的输入会先稳定排序，再依次插入；
  返回的失败索引仍按原始输入位置计算。
- `addCanvasByDict()` 的画布列表按输入顺序追加，但每个画布内部的关键点按
  `time` 排序。
- 线子节点可带可选父索引字段：
  - `lineindex` / `lineIndex` / `line_index`
  - 缺省为 `-1`，即最后一条线
- 画布子节点可带可选父索引字段：
  - `canvasindex` / `canvasIndex` / `canvas_index`
  - 缺省为 `-1`，即最后一条画布
- 这些父索引字段只用于 `advanced.py`，不会写入谱面。

### `addLineByDict()`

**函数声明**

```python
addLineByDict(chart: dict, dictlist: dict | list,
              index: int | None = -1,
              isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 一条线规格或线规格列表 |
| `index` | `int \| None` | 否 | `-1` | 插入位置；`-1` / `None` 表示追加到末尾 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按 `getLine()` 返回的线规格批量插入引导线。

**输入规格**

```python
{
    "linePoints": [线节点规格, ...],
    "notes": [Note 规格, ...],
    "judgeRingColor": [颜色节点规格, ...],
    "lineColor": [颜色节点规格, ...],
}
```

`notes` / `lineColor` 可省略。内部节点会由 `addLine()` 按时间稳定排序并重算
`floorPosition`。

**注意事项/细节**

- `index=-1` 表示追加到末尾；其他索引传给 `addLine()`。
- 批量插入时保持列表中的线条顺序。
- 线规格可包含 `index` 字段，但该字段会被忽略。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addLinePointByDict()`

**函数声明**

```python
addLinePointByDict(chart: dict, dictlist: dict | list,
                   isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 线节点规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按线节点规格向指定线批量添加节点。

**输入规格**

线节点规格，外加可选 `lineindex`：

```python
{
    "time": float,
    "xPosition": float,
    "canvasIndex": int,
    "easeType": int,
    "color": [r, g, b, a],
    "lineindex": int,   # 可选，默认 -1
}
```

**注意事项/细节**

- 按 `time` 稳定排序后依次插入。
- `lineindex` 缺省为最后一条线。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addRingPointByDict()`

**函数声明**

```python
addRingPointByDict(chart: dict, dictlist: dict | list,
                   isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 判定环规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按判定环颜色规格向指定线批量添加判定环节点。

**输入规格**

```python
{
    "time": float,
    "startColor": [r, g, b, a],
    "endColor": [r, g, b, a],  # 可选
    "lineindex": int,           # 可选，默认 -1
}
```

按 `time` 稳定排序后插入。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addLineColorByDict()`

**函数声明**

```python
addLineColorByDict(chart: dict, dictlist: dict | list,
                    isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 线色覆盖规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按线色覆盖规格向指定线批量添加节点。

**输入规格**

```python
{
    "time": float,
    "startColor": [r, g, b, a],
    "endColor": [r, g, b, a],  # 可选
    "lineindex": int,           # 可选，默认 -1
}
```

按 `time` 稳定排序后插入。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addNoteByDict()`

**函数声明**

```python
addNoteByDict(chart: dict, dictlist: dict | list,
              isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | Note 规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按 Note 规格向指定线批量添加 Note。

**输入规格**

```python
{"type": 0, "time": float}                    # Tap
{"type": 1, "time": float}                    # Drag
{"type": 2, "time": float, "endtime": float}  # Hold
{"type": 0, "time": float, "lineindex": int}  # 可选父线索引
```

按 `time` 稳定排序后插入，`lineindex` 缺省为最后一条线。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addIsolatedNote()`

**函数声明**

```python
addIsolatedNote(chart: dict, canvasindex: int, time: float, position: float,
                type: int | str,
                endtime: float | None = None,
                endposition: float | None = None,
                endcanvasindex: int | None = None,
                isRealTime: bool = False,
                isRealEndTime: bool = False,
                isAbsolutePosition: bool = False,
                isAbsoluteEndPosition: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | Note 头部所在画布索引；支持负数从末尾计算 |
| `time` | `float` | 是 | - | Note 头部时间；必须大于等于 0 |
| `position` | `float` | 是 | - | Note 头部位置 |
| `type` | `int \| str` | 是 | - | Note 类型：`0/"tap"`、`1/"drag"`、`2/"hold"`，不区分大小写 |
| `endtime` | `float \| None` | 否 | `None` | Hold 尾部时间；转换后必须大于 `time` |
| `endposition` | `float \| None` | 否 | `None` | Hold 尾部位置；`None` 表示沿用头部位置 |
| `endcanvasindex` | `int \| None` | 否 | `None` | Hold 尾部画布索引；`None` 表示同 `canvasindex` |
| `isRealTime` | `bool` | 否 | `False` | `time` 是否使用真实时间（秒） |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否使用真实时间（秒） |
| `isAbsolutePosition` | `bool` | 否 | `False` | `position` 是否使用绝对坐标 |
| `isAbsoluteEndPosition` | `bool` | 否 | `False` | `endposition` 是否使用绝对坐标 |

**用途**

在谱面上创建一条只服务于一个 Note 的独立引导线，并在线节点处放置
Tap / Drag / Hold。线节点和判定环均为透明色，因此辅助线本身不可见，
但 Note 会保留在该位置。

**行为**

- 线会在末尾追加，成功返回新线索引 `int`；索引可能为 `0`，请用
  `is not None` 判断成功。
- Tap / Drag：
  - 第一个线节点位于 `time`、`position`、`canvasindex`；
  - 第二个线节点位于头部时间上方 `1/16` 节拍处（tick 偏移 `0.0625`）；
  - 两个线节点使用同一画布，并按定位模式保持同一位置；绝对模式下两个节点的
    绝对 x 坐标一致。
- Hold：
  - 第一个线节点位于头部；
  - 最后一个线节点位于 `endtime`、`endposition`、`endcanvasindex`；
  - 若尾部画布与头部画布不同，会额外插入一个位于 `endtime` 前极小时间的
    尾前节点；这是因为谱面 Hold 尾部正好落在节点时间时使用左侧线段的画布。
  - `endtime` 必须大于头部时间；`endposition=None` 时沿用头部解析后的线
    位置；`endcanvasindex=None` 时沿用头部画布。
- Tap / Drag 忽略 `endtime` / `endposition` / `endcanvasindex` / 结束时间标志。

**坐标与时间**

- `position` / `endposition` 默认是相对画布中线的坐标；对应
  `isAbsolute...=True` 时是绝对 x 坐标，会按对应时刻和画布换算为线节点的
  相对坐标。
- `endposition=None` 且头部使用绝对坐标时，会把同一绝对位置换算到尾时刻
  的尾部画布；头部使用相对坐标时则保持同一相对线位置。
- `time` / `endtime` 默认是 tick；`isRealTime` / `isRealEndTime=True` 时按
  实际秒数换算为 tick。
- `1/16` 节拍使用 tick 偏移，不随 BPM 变化。

**返回值与失败**

- 成功返回新线索引；`chart` / 画布 / 时间 / 位置 / 类型非法，Hold 时间
  非法，或建线失败时返回 `None`。
- 失败时不会留下新线或部分 Note。
- `type` 大小写不敏感；`endtime` 为 `None` 时 Hold 会失败。

### `addRiztimeByDict()`

**函数声明**

```python
addRiztimeByDict(chart: dict, dictlist: dict | list,
                 isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | Riztime 规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按 Riztime 规格批量添加 Riztime。

**输入规格**

使用 `getRiztime()` 的合并规格：

```python
{
    "colorsList": [color1, color2, color3],
    "start": float,
    "end": float,
    "transTime": float,
    "checkPoint": float,
}
```

`themeIndex` / `challengeIndex` 会被忽略；按 `start` 稳定排序后插入。
如果原始谱面只有一个 `start == end` 的占位 Riztime，原子回退会在删除本批新增项后恢复该占位。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addBpmByDict()`

**函数声明**

```python
addBpmByDict(chart: dict, dictlist: dict | list,
             isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | BPM 节点规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按 `getBpmShift()` 的 BPM 节点规格批量添加 BPM 变化节点。

**输入规格**

```python
{
    "time": float,
    "value": float,             # 默认是 bpmShifts[].value 倍率
    "easeType": int,            # 可选，BPM 固定为 0，会被忽略
    "isMultiply": bool,         # 可选，默认 True
    "isRealtime": bool,         # 可选，默认 False
}
```

`value` 默认按倍率处理，复制 `getBpmShift()` 的规格即可直接导入；需要直接传实际 BPM 时设置 `isMultiply=False`。按 `time` 稳定排序后插入。

**注意事项/细节**

- 批内节点使用延迟计算写入，结束后调用一次 `refresh(mode="all", type="all")`，重算**全部** `floorPosition`；BPM 会影响线节点、Note、Hold 尾部、画布流速等所有高度。
- 同时间节点插入到已有节点之后，实际 BPM 以最右侧节点为准。
- 最终刷新失败时返回 `[-1]`；原子模式下会先回退本批插入。
- 原子回退会删除本批新增的 BPM 节点。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

**示例**

```python
from rizChartFunction import addBpmByDict, getBpmShift, new

chart = new(100.0)

# 复制已有 BPM 节点规格（value 为倍率）
spec = getBpmShift(chart, 0)
failed = addBpmByDict(chart, [
    {**spec, "time": 4.0, "value": 2.0},
    {**spec, "time": 8.0, "value": 0.5},
])
if failed:
    raise RuntimeError(f"失败的规格索引：{failed}")

# 直接使用实际 BPM
addBpmByDict(
    chart,
    {"time": 16.0, "value": 150.0, "isMultiply": False},
)
```

### `addCanvasByDict()`

**函数声明**

```python
addCanvasByDict(chart: dict, dictlist: dict | list,
                isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 画布规格或规格列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按画布规格添加画布，并导入其中的横向移动与流速关键点。

**输入规格**

```python
{
    "xPositionKeyPoints": [关键点规格, ...],  # 可选
    "speedKeyPoints": [关键点规格, ...],      # 可选
}
```

关键点规格为 `{time, value, easeType}`。

**注意事项/细节**

- 画布追加到末尾；规格中的 `index` 会被忽略。
- 关键点按 `time` 稳定排序后写入。
- 首节点 `time=0.0` 会替换新画布的默认节点，避免重复。
- 批量画布按列表顺序追加。
- 某个画布规格失败时，会删除该规格已创建的新画布；原子模式还会删除本批早先创建的全部画布。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addCanvasPositionByDict()`

**函数声明**

```python
addCanvasPositionByDict(chart: dict, dictlist: dict | list,
                        isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 画布横向移动节点规格或列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按画布横向移动节点规格批量添加节点。

**输入规格**

```python
{
    "time": float,
    "value": float,
    "easeType": int,
    "canvasindex": int,  # 可选，默认 -1
}
```

按 `time` 稳定排序后插入。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addCanvasSpeedByDict()`

**函数声明**

```python
addCanvasSpeedByDict(chart: dict, dictlist: dict | list,
                     isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 画布速度节点规格或列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按画布速度节点规格批量添加节点。

**输入规格**

```python
{
    "time": float,
    "value": float,
    "easeType": int,
    "canvasindex": int,  # 可选，默认 -1
}
```

按 `time` 稳定排序后插入；不会自动改写接近 0 的流速。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addCameraPositionByDict()`

**函数声明**

```python
addCameraPositionByDict(chart: dict, dictlist: dict | list,
                        isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 摄像机横向移动节点规格或列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按摄像机横向移动节点规格批量添加节点。

**输入规格**

```python
{"time": float, "value": float, "easeType": int}
```

按 `time` 稳定排序后插入。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

### `addCameraScaleByDict()`

**函数声明**

```python
addCameraScaleByDict(chart: dict, dictlist: dict | list,
                     isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `dictlist` | `dict \| list` | 是 | - | 摄像机缩放节点规格或列表 |
| `isFailAddAllowed` | `bool` | 否 | `False` | `False` 为原子模式，失败整批回退；`True` 跳过失败规格并继续 |

**用途**

按摄像机缩放节点规格批量添加节点。

**输入规格**

```python
{"time": float, "value": float, "easeType": int}
```

按 `time` 稳定排序后插入。

**返回值**

返回本批失败规格的原始索引列表；全部成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会先回退本批全部插入；整体输入非法返回 `[-1]`。

## 复制函数

以下每个函数独立列出参数、索引格式、复制模式和注意事项。

### `copyLine()`

**函数声明**

```python
copyLine(sourcechart: dict, indexlist: int | list,
         targetchart: dict | None = None, targetindex: int | None = None,
         copymode: str = "insert", offsettime: float = 0.0,
         offsetposition: float = 0.0, canvasmode: str = "insert",
         isRealOffsetTime: bool = False,
         isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 源线索引；单个 `int` 或 `list[int]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 插入起点；`None` 追加到末尾，负数从末尾计算 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `offsetposition` | `float` | 否 | `0.0` | 横向位置偏移 |
| `canvasmode` | `str` | 否 | `"insert"` | `"insert"` / `"increase"` / `"add"` |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一条或多条完整引导线，包括 `linePoints`、`notes`、`judgeRingColor` 和 `lineColor`。

**索引格式**

- `indexlist` 是扁平线索引列表；复制时按 `indexlist` 的顺序插入。
- 负索引按源谱面线列表解析。

**复制模式**

- `insert`：在 `targetindex` 处按 `indexlist` 顺序插入，保留下标位置之后的目标线。
- `replace`：清空目标谱面的全部线，忽略 `targetindex`，然后按 `indexlist` 顺序重新复制。
- `part`：必须提供整数 `targetindex`。每条源线的目标位置为 `源线索引 + targetindex`；位置存在则替换该目标线，超出目标线数量则按处理顺序追加。

**注意事项**

- 线节点的 `xPosition`、Note 头/尾时间、判定环时间和线色时间都会应用 `offsettime`；`linePoints` 的 `xPosition` 应用 `offsetposition`。
- `canvasmode` 控制线节点画布引用：`insert` 保留源画布索引并补初始化画布；`increase` 将使用的画布映射到从 `0` 开始的连续索引；`add` 映射到目标最大画布之后并复制源画布内容。
- `canvasmode="add"` 复制源画布内容时应用 `offsettime`，不应用 `offsetposition`。
- 线内部的 Note 如果因偏移或画布映射导致越界，该线视为复制失败。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyLinePoint()`

**函数声明**

```python
copyLinePoint(sourcechart: dict, indexlist: int | list,
              targetchart: dict | None = None,
              targetindex: int | None = None,
              copymode: str = "insert", offsettime: float = 0.0,
              offsetposition: float = 0.0,
              canvasmode: str = "insert",
              isRealOffsetTime: bool = False,
              isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 线节点索引；`[lineindex, pointindex]` 或 `[[lineindex, pointindex], ...]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 目标父线索引；`None` 按 `-1` 处理 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `offsetposition` | `float` | 否 | `0.0` | 横向位置偏移 |
| `canvasmode` | `str` | 否 | `"insert"` | `"insert"` / `"increase"` / `"add"` |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一条或多条线节点到目标线。

**索引格式**

- 单个节点写成 `[lineindex, pointindex]`；多个节点写成 `[[lineindex, pointindex], ...]`。

**复制模式**

- `insert`：按时间稳定排序后插入目标父线，保留目标原节点。
- `replace`：用源节点替换目标父线的全部 `linePoints`；源节点少于 2 个时失败。
- `part`：清空目标父线中严格位于源时间范围 `(a,b)` 的节点，再按时间插入源节点；如果结果少于 2 个节点，使用 replace 方式处理，仍不足则失败。

**注意事项**

- `targetindex` 是目标父线索引，不是线节点插入位置。
- `offsetposition` 加到线节点的 `xPosition`。
- `canvasmode` 规则同 `copyLine()`，映射对象的 `canvasIndex`。
- replace/part 会重建目标线并检查原有 Note 是否越界；越界则失败并回退。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyRingPoint()`

**函数声明**

```python
copyRingPoint(sourcechart: dict, indexlist: int | list,
              targetchart: dict | None = None,
              targetindex: int | None = None,
              copymode: str = "insert", offsettime: float = 0.0,
              isRealOffsetTime: bool = False,
              isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 判定环索引；`[lineindex, ringindex]` 或 `[[lineindex, ringindex], ...]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 目标父线索引；`None` 按 `-1` 处理 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一条或多条判定环颜色节点。

**索引格式**

- 单个节点写成 `[lineindex, ringindex]`；多个节点写成 `[[lineindex, ringindex], ...]`。

**复制模式**

- `insert`：按时间稳定排序后向目标父线添加判定环。
- `replace`：用源判定环替换目标父线的全部判定环。
- `part`：清空目标父线中严格位于源时间范围 `(a,b)` 的判定环，再插入源判定环。

**注意事项**

- `targetindex` 是目标父线索引。
- 目标线至少保留 1 个判定环；replace/part 结果少于 1 个时失败并回退。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyLineColor()`

**函数声明**

```python
copyLineColor(sourcechart: dict, indexlist: int | list,
              targetchart: dict | None = None,
              targetindex: int | None = None,
              copymode: str = "insert", offsettime: float = 0.0,
              isRealOffsetTime: bool = False,
              isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 线色索引；`[lineindex, colorindex]` 或 `[[lineindex, colorindex], ...]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 目标父线索引；`None` 按 `-1` 处理 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一条或多条线色覆盖节点。

**索引格式**

- 单个节点写成 `[lineindex, colorindex]`；多个节点写成 `[[lineindex, colorindex], ...]`。

**复制模式**

- `insert`：按时间稳定排序后向目标父线添加线色节点。
- `replace`：用源线色节点替换目标父线的全部 `lineColor`。
- `part`：清空目标父线中严格位于源时间范围 `(a,b)` 的线色节点，再插入源节点。

**注意事项**

- `targetindex` 是目标父线索引。
- 线色节点只复制起止颜色与时间，不改变目标线的线节点和 Note。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyNote()`

**函数声明**

```python
copyNote(sourcechart: dict, indexlist: int | list,
         targetchart: dict | None = None, targetindex: int | None = None,
         copymode: str = "insert", offsettime: float = 0.0,
         isRealOffsetTime: bool = False,
         isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | Note 索引；`[lineindex, noteindex]` 或 `[[lineindex, noteindex], ...]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 目标父线索引；`None` 按 `-1` 处理 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一条或多条 Note 到目标线。

**索引格式**

- 单个 Note 写成 `[lineindex, noteindex]`；多个 Note 写成 `[[lineindex, noteindex], ...]`。

**复制模式**

- `insert`：按头部时间稳定排序后向目标父线添加 Note。
- `replace`：用源 Note 替换目标父线的全部 Note。
- `part`：清空目标父线中头部时间严格位于 `(a,b)` 的 Note，再插入源 Note。

**注意事项**

- `targetindex` 是目标父线索引。
- Hold 的头部和尾部时间分别应用 `offsettime`。
- 本函数没有 `canvasmode`；复制后的 Note 画布绑定按目标线现有节点推导。
- replace/part 后 Note 头或 Hold 尾超出目标线范围时失败并回退。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyBpmShift()`

**函数声明**

```python
copyBpmShift(sourcechart: dict, indexlist: int | list,
             targetchart: dict | None = None,
             copymode: str = "insert", offsettime: float = 0.0,
             isRealOffsetTime: bool = False,
             isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 源 BPM 节点索引；单个 `int` 或 `list[int]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个 BPM 变化节点。

**索引格式**

- `indexlist` 是扁平 BPM 节点索引；负索引从末尾计算。

**复制模式**

- `insert`：按时间稳定排序后合并进目标 `bpmShifts`；保留目标原有节点。
- `replace`：清空目标 BPM 节点后复制源节点；首节点按不可删除首节点的规则处理。
- `part`：清空目标中时间严格位于源时间范围 `(a,b)` 的 BPM 节点，再插入源节点。

**注意事项**

- `value` 使用 `bpmShifts[].value` 倍率语义，与 `getBpmShift()` 的规格一致。
- 相同时间节点允许；实际 BPM 以最右侧节点为准。
- 复制完成后执行全谱 `refresh(mode="all", type="all")`，重算所有受 BPM 影响的 `floorPosition`。
- 源节点没有 `time=0.0` 时，replace 会保留目标重置后的默认首节点。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyRiztime()`

**函数声明**

```python
copyRiztime(sourcechart: dict, indexlist: int | list,
            targetchart: dict | None = None,
            copymode: str = "insert", offsettime: float = 0.0,
            isRealOffsetTime: bool = False,
            isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 源 Riztime 索引；从 1 开始，单个 `int` 或 `list[int]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个 Riztime 及其配色。

**索引格式**

- Riztime 索引从 `1` 开始；`0` 非法。`-1` 表示最后一条。

**复制模式**

- `insert`：按 start 稳定排序后添加 Riztime。
- `replace`：清空目标全部 Riztime 后复制源 Riztime。
- `part`：删除目标中满足 `目标 start > 源最早 start` 且 `目标 end < 源最晚 end` 的 Riztime，再按 start 添加源 Riztime。

**注意事项**

- `start` 和 `end` 分别应用 `offsettime`。
- 会同时复制 `colorsList`、`transTime` 和 `checkPoint`。
- 不复制源 `themeIndex` / `challengeIndex`；目标索引由插入结果决定。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyCanvas()`

**函数声明**

```python
copyCanvas(sourcechart: dict, indexlist: int | list,
           targetchart: dict | None = None, targetindex: int | None = None,
           copymode: str = "insert", offsettime: float = 0.0,
           offsetposition: float = 0.0,
           isRealOffsetTime: bool = False,
           isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 源画布索引；单个 `int` 或 `list[int]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 插入起点；`None` 追加到末尾，负数从末尾计算 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `offsetposition` | `float` | 否 | `0.0` | 横向位置偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个画布及其横向移动、流速关键点。

**索引格式**

- `indexlist` 是扁平画布索引；复制时按 `indexlist` 的顺序处理。

**复制模式**

- `insert`：在 `targetindex` 处按 `indexlist` 顺序插入画布，并复制画布内容。
- `part`：必须提供整数 `targetindex`。每个源画布的目标位置为 `源画布索引 + targetindex`；目标位置存在则替换该画布内容，超出目标画布数量则按处理顺序追加。
- `replace` 不允许，传入后返回 `[-1]`。

**注意事项**

- 画布位置关键点的 `value` 应用 `offsetposition`；位置和流速关键点的时间应用 `offsettime`。
- 插入模式会同步更新目标线节点和 Hold 尾部中受画布索引移动影响的引用。
- `part` 替换已有画布时保留目标画布索引，只替换其关键点内容。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyCanvasPosition()`

**函数声明**

```python
copyCanvasPosition(sourcechart: dict, indexlist: int | list,
                  targetchart: dict | None = None,
                  targetindex: int | None = None,
                  copymode: str = "insert", offsettime: float = 0.0,
                  offsetposition: float = 0.0,
                  isRealOffsetTime: bool = False,
                  isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 画布位置节点；`[canvasindex, pointindex]` 或 `[[canvasindex, pointindex], ...]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 目标父画布索引；`None` 按 `-1` 处理 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `offsetposition` | `float` | 否 | `0.0` | 横向位置偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个画布横向移动关键点。

**索引格式**

- 单个节点写成 `[canvasindex, pointindex]`；多个节点写成 `[[canvasindex, pointindex], ...]`。

**复制模式**

- `insert`：按时间稳定排序后向目标画布添加关键点。
- `replace`：清空目标画布的全部位置关键点后复制源节点。
- `part`：清空目标画布中严格位于源时间范围 `(a,b)` 的位置关键点，再插入源节点。

**注意事项**

- `targetindex` 是目标父画布索引。
- `offsetposition` 加到关键点的 `value`。
- 首节点不可删除时按首节点重置规则处理。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyCanvasSpeed()`

**函数声明**

```python
copyCanvasSpeed(sourcechart: dict, indexlist: int | list,
                targetchart: dict | None = None,
                targetindex: int | None = None,
                copymode: str = "insert", offsettime: float = 0.0,
                isRealOffsetTime: bool = False,
                isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 画布流速节点；`[canvasindex, pointindex]` 或 `[[canvasindex, pointindex], ...]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `targetindex` | `int \| None` | 否 | `None` | 目标父画布索引；`None` 按 `-1` 处理 |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个画布流速关键点。

**索引格式**

- 单个节点写成 `[canvasindex, pointindex]`；多个节点写成 `[[canvasindex, pointindex], ...]`。

**复制模式**

- `insert`：按时间稳定排序后向目标画布添加流速节点。
- `replace`：清空目标画布的全部流速节点后复制源节点。
- `part`：清空目标画布中严格位于源时间范围 `(a,b)` 的流速节点，再插入源节点。

**注意事项**

- `targetindex` 是目标父画布索引。
- 本函数不提供 `offsetposition`；不自动改写接近 `0` 的流速。
- 首节点不可删除时按首节点重置规则处理。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyCamera()`

**函数声明**

```python
copyCamera(sourcechart: dict, targetchart: dict | None = None,
           copymode: str = "insert", offsettime: float = 0.0,
           offsetposition: float = 0.0,
           isRealOffsetTime: bool = False,
           isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `offsetposition` | `float` | 否 | `0.0` | 横向位置偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制整个摄像机对象，包括位置和缩放两个关键点数组。

**索引格式**

- 本函数没有 `indexlist`，始终复制整个摄像机对象。

**复制模式**

- `insert`：把源摄像机的位置和缩放节点按时间合并到目标摄像机。
- `replace`：清空目标摄像机的两个关键点数组后复制源内容。
- `part` 不允许，传入后返回 `[0]`。

**注意事项**

- `offsetposition` 作用于位置关键点的 `value`，不作用于缩放关键点。
- 没有 `targetindex`、`indexlist`、`canvasmode`。
- 由于只有一个摄像机对象，`isFailAddAllowed=True` 也不会产生跳过效果；所有失败固定返回 `[0]`。

**返回值**

成功返回 `[]`；所有失败返回 `[0]`。

### `copyCameraPosition()`

**函数声明**

```python
copyCameraPosition(sourcechart: dict, indexlist: int | list,
                   targetchart: dict | None = None,
                   copymode: str = "insert", offsettime: float = 0.0,
                   offsetposition: float = 0.0,
                   isRealOffsetTime: bool = False,
                   isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 源摄像机位置节点索引；单个 `int` 或 `list[int]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `offsetposition` | `float` | 否 | `0.0` | 横向位置偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个摄像机横向移动关键点。

**索引格式**

- `indexlist` 是扁平摄像机位置关键点索引。

**复制模式**

- `insert`：按时间稳定排序后合并进目标位置数组。
- `replace`：清空目标摄像机位置数组后复制源节点。
- `part`：清空目标位置数组中严格位于源时间范围 `(a,b)` 的节点，再插入源节点。

**注意事项**

- 没有 `targetindex`。
- `offsetposition` 加到关键点的 `value`。
- 首节点不可删除时按首节点重置规则处理。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

### `copyCameraScale()`

**函数声明**

```python
copyCameraScale(sourcechart: dict, indexlist: int | list,
                targetchart: dict | None = None,
                copymode: str = "insert", offsettime: float = 0.0,
                isRealOffsetTime: bool = False,
                isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `sourcechart` | `dict` | 是 | - | 源谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 源摄像机缩放节点索引；单个 `int` 或 `list[int]` |
| `targetchart` | `dict \| None` | 否 | `None` | 目标谱面；`None` 表示使用 `sourcechart` |
| `copymode` | `str` | 否 | `"insert"` | `"insert"` / `"replace"` / `"part"` |
| `offsettime` | `float` | 否 | `0.0` | 时间偏移 |
| `isRealOffsetTime` | `bool` | 否 | `False` | `offsettime` 是否按目标谱面 BPM 时间轴换算；`True` 时按每个节点原 tick 处的 BPM 换算 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败元素并继续 |

**用途**

复制一个或多个摄像机缩放关键点。

**索引格式**

- `indexlist` 是扁平摄像机缩放关键点索引。

**复制模式**

- `insert`：按时间稳定排序后合并进目标缩放数组。
- `replace`：清空目标摄像机缩放数组后复制源节点。
- `part`：清空目标缩放数组中严格位于源时间范围 `(a,b)` 的节点，再插入源节点。

**注意事项**

- 没有 `targetindex`，也不提供 `offsetposition`。
- 首节点不可删除时按首节点重置规则处理。

**返回值**

成功返回 `[]`。`isFailAddAllowed=False` 时任一失败会回退本批全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。整体输入非法返回 `[-1]`。

## 缓动函数

缓动函数批量修改一组已有节点之间的过渡；它们不是按规格 Dict 插入，而是按索引选择节点，并通过 `easetype` 指定目标过渡。

### 缓动函数通用规则

- 所有缓动函数统一返回 `list[int]`：全部成功返回 `[]`；原子模式失败返回一个失败索引；`isFailAddAllowed=True` 时返回全部失败索引（升序）；整体输入非法返回 `[-1]`。
- `isFailAddAllowed=False`（默认）为原子模式，先完整预演；任一索引失败则谱面保持原样。
- `isFailAddAllowed=True` 时逐个预演并提交，失败索引不修改谱面，成功索引保留。
- 失败索引是 `indexlist` 中的**原始位置**，不是稳定排序后的位置。
- `indexlist` 可为单个索引，也可为索引列表；线 / 画布子节点使用 `[父索引, 子索引]` 或 `[[父索引, 子索引], ...]`。
- 负索引从末尾计算；选择节点后必须存在**时间严格大于当前节点**的下一个节点，否则该索引失败。
- `setLinePointPositionEase()` 与 `setLinePointColorEase()` 要求当前节点和下一个节点位于同一画布。
- `precision`：`inserttype="uniform"` / `"arc"` / `"curvature"` 时必须是正整数，表示插入节点数量；`"recursion"` / `"priority"` 时必须是正的有限浮点数（整数也可），表示允许误差。
- `inserttype` 只接受 `"uniform"`、`"arc"`、`"curvature"`、`"recursion"`、`"priority"`；默认 `"uniform"`。
- `arc` / `curvature` 会先把时间归一化到 `[0,1]`，位置/数值按两端差值归一化，颜色通道按 `0..255 → [0,1]` 归一化，再计算归一化空间中的弧长或曲率。
- `inserttype="uniform"` / `"arc"` / `"curvature"` 不限制插入数量，所有采样点都会尝试插入。
- `inserttype="recursion"` / `"priority"` 每个 tick 最多 48 个节点（包含该 tick 的整数时间端点）。若某个 tick 的采样点超过容量，会在该 tick 内按时间均匀挑选可插入点，并继续处理后续 tick；不会因为一个 tick 满而丢弃整个区间剩余的 tick。已经插入的节点保留，函数仍视为成功。
- `easetype` 为整数 `0..25`；也可传四元素 Cubic Bezier 列表 `[x1, y1, x2, y2]`，其中 `x1` / `x2` 必须在 `[0,1]` 内。
- 对有原生 `easeType` 的节点，`0..18` 直接写入；`19..22` 在中点插入一个节点并精确拆成两段；`23..25` 与 Cubic Bezier 通过插入节点模拟。
- `19 / 20 / 21 / 22` 的拆分为：`15+16` / `16+15` / `18+17` / `17+18`（前一段写在前节点，后一段写在后插入节点）。
- BPM、流速、颜色节点没有可表达的通用 `easeType`，因此除下述特殊值外都通过插入节点模拟。
- `setBpmShiftEase()` 会在所有实际修改完成后执行一次全谱 `refresh(mode="all", type="all")`；流速、线节点、颜色节点由各自的公开修改函数即时重算相关 `floorPosition`。
- 对于 BPM、流速、颜色节点，`13` 为零阶保持，`14` 为瞬时跳变；线点颜色还需要自动把所有涉及的线节点设为 `linear`，详见对应函数。

### `setBpmShiftEase()`

**函数声明**

```python
setBpmShiftEase(chart: dict, indexlist: int | list,
                easetype: int | list,
                precision: int | float = 1,
                inserttype: str = "uniform",
                isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | BPM 节点扁平索引，单个 `int` 或 `list[int]` |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值，含义取决于 `inserttype` |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

在选中的 BPM 节点与其下一个 BPM 节点之间，按目标缓动插入 BPM 变化节点，使实际 BPM 时间轴近似目标过渡。

**索引格式**

- `indexlist` 是 `bpmShifts` 的扁平索引；负索引从末尾计算。
- 默认按索引从大到小处理，避免插入节点影响尚未处理的低索引。

**缓动行为**

- `easetype=13`：原生零阶保持，不修改节点。
- `easetype=14`：在 `math.nextafter(当前时间, 下一节点时间)` 插入下一节点的倍率值，形成瞬时跳变。
- 其它 `easetype`：按 `inserttype` / `precision` 在区间内采样目标倍率，逐个添加 BPM 节点；所有新增节点使用 `addBpmShift(..., isMultiply=True)`。
- 允许的采样值必须大于 `0`；Cubic Bezier 或其他曲线产生非法 BPM 时该索引失败。
- 全部实际修改结束后统一执行一次全谱 `refresh()`，因此可以修正所有受 BPM 影响的 `floorPosition`。

**注意事项**

- 若 `math.nextafter()` 无法得到严格位于当前时间和下一节点时间之间的时间点，`14` 失败。
- 同一时间存在多个 BPM 节点时，只有时间严格递增的下一节点可作为过渡终点。
- 原子模式预演使用延迟计算，提交后才统一刷新；失败时不会留下待刷新节点。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setLinePointPositionEase()`

**函数声明**

```python
setLinePointPositionEase(chart: dict, indexlist: int | list,
                         easetype: int | list,
                         precision: int | float = 1,
                         inserttype: str = "uniform",
                         isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 线节点索引；`[lineindex, pointindex]` 或 `[[lineindex, pointindex], ...]` |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改线节点 `xPosition` 从当前节点到下一节点的缓动。线节点颜色仍保持原有的两端线性过渡，不随位置缓动改变。

**索引格式**

- `indexlist` 使用 `[lineindex, pointindex]`；单个线节点传一对，多个传二维列表。
- 负 `lineindex` / `pointindex` 从末尾计算。
- 当前节点和下一节点必须位于同一 `canvasIndex`；否则该索引失败。

**缓动行为**

- `easetype=0..18`：直接写入当前线节点的 `easeType`，不插入节点。
- `easetype=19..22`：在时间中点插入一个线节点，位置取两端中点，颜色取两端颜色的线性中点；当前节点写前半段，插入节点写后半段。
- `easetype=23..25` 或 Cubic Bezier：按采样点插入线节点，当前节点与插入节点写 `easeType=0`；插入节点颜色按原两端颜色在对应归一化位置的线性值计算。
- 直接写入和拆分模式都不会改变线节点颜色；模拟模式也会尽量保持颜色为原线性过渡的分段近似。

**注意事项**

- 没有下一节点、下一节点时间不递增、或当前/下一节点画布不同时失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。
- 批量处理按线索引和子索引从大到小进行，避免插入节点改变尚未处理的索引。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setLinePointColorEase()`

**函数声明**

```python
setLinePointColorEase(chart: dict, indexlist: int | list,
                      easetype: int | list,
                      precision: int | float = 1,
                      inserttype: str = "uniform",
                      isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 线节点索引；`[lineindex, pointindex]` 或二维列表 |
| `easetype` | `int \| list` | 是 | - | 目标颜色过渡缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改线节点颜色从当前节点到下一节点的过渡。因为线节点只有一个 `easeType` 同时控制位置，本函数会强制把当前节点和插入节点设为 `linear`。

**索引格式**

- `indexlist` 使用 `[lineindex, pointindex]`；负索引从末尾计算。
- 当前节点和下一节点必须位于同一 `canvasIndex`。

**缓动行为**

- `easetype=0`：不插入节点，仅把当前线节点设为 `easeType=0`。
- `easetype=13`：在下一节点前插入一个使用当前颜色的线节点，使颜色保持到接近下一节点；当前节点和插入节点均设为 `linear`。
- `easetype=14`：在当前节点后插入一个使用下一节点颜色的线节点，使颜色立即跳变；当前节点和插入节点均设为 `linear`。
- 其它 `easetype`：按采样点插入线节点，颜色取目标颜色曲线在对应归一化位置的值；当前节点和插入节点均设为 `linear`。
- 插入节点的 `xPosition` 从**修改前**的位置曲线采样：使用当前节点原来的 `easeType` 在对应归一化位置计算位置，因此颜色修改不会改变原位置曲线。

**注意事项**

- 本函数会改变位置行为：当前节点和所有插入节点都变为 `linear`，原位置曲线会被分段线性近似。
- 若 `math.nextafter()` 无法得到严格位于区间内的时间点，需要插入的 `13` / `14` 失败。
- 插入节点使用当前画布；当前/下一节点画布不同、没有下一节点或时间不递增时失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setLinePointColorByList()`

**函数声明**

```python
setLinePointColorByList(chart: dict, lineindex: int,
                        startpointindex: int, endpointindex: int,
                        startcolor: str | list | None = None,
                        endcolor: str | list | None = None,
                        easetype: int | list = 0) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 是 | - | 线索引；支持负数从末尾计算 |
| `startpointindex` | `int` | 是 | - | 起始节点索引；支持负数 |
| `endpointindex` | `int` | 是 | - | 结束节点索引；解析后的绝对索引必须大于起始索引 |
| `startcolor` | `str \| list \| None` | 否 | `None` | 起始节点颜色；`None` 使用起始节点原色 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 结束节点颜色；`None` 使用结束节点原色 |
| `easetype` | `int \| list` | 否 | `0` | 颜色插值缓动 `0..25`，或 Cubic Bezier 列表 |

**用途**

对指定线上的一个节点索引区间重新着色，区间包含起始节点和结束节点。
本函数**只修改已有节点的颜色**，不新增、不删除节点，也不会修改节点的
`easeType`、时间或位置。

**插值方式**

- 以起始节点到结束节点的时间比例为归一化参数，使用 `easetype` 计算
  每个中间节点的颜色。
- 起始节点固定为 `startcolor`（`None` 时为原色），结束节点固定为
  `endcolor`（`None` 时为原色）。
- 区间首尾节点时间相同时，退化为按节点索引比例插值。
- `easetype` 支持 `0..25` 和 `[x1, y1, x2, y2]` Cubic Bezier。
- 颜色按 RGBA 四通道线性插值并四舍五入到 `0..255`。

**注意事项**

- 谱面只保存已有节点上的颜色；节点之间由游戏/编辑器自行线性插值。
  如果节点分布稀疏，实际颜色过渡会变成较粗的分段线性效果，可能无法
  准确还原目标缓动曲线，需要自行确认节点密度。
- 成功返回 `[]`；参数非法、索引越界、颜色或 `easetype` 非法时返回 `None`。
- 本函数不应出现部分成功；实现会先校验并计算全部目标颜色，再统一写入。
  若写入过程中发生异常，会尝试恢复已修改节点的原色。

### `setRingColorEase()`

**函数声明**

```python
setRingColorEase(chart: dict, indexlist: int | list,
                 easetype: int | list,
                 precision: int | float = 1,
                 inserttype: str = "uniform",
                 isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 判定环颜色节点索引；`[lineindex, ringindex]` 或二维列表 |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改判定环颜色从当前节点的 `startColor` 到 `endColor` 的过渡，并在需要时插入中间颜色节点。

**索引格式**

- `indexlist` 使用 `[lineindex, ringindex]`；负索引从末尾计算。
- 选择节点后必须存在下一个判定环节点，以确定过渡结束时间。

**缓动行为**

- `easetype=0`：线性的原生颜色过渡，不修改节点。
- `easetype=13`：把当前节点的 `endColor` 设为当前 `startColor`，形成零阶保持。
- `easetype=14`：在当前节点后插入一个 `startColor=endColor=原 endColor` 的节点，形成瞬时跳变。
- 其它 `easetype`：按采样点插入颜色节点；当前节点的 `endColor` 改为第一个采样颜色，插入节点依次连接目标颜色，最后一段接回原 `endColor`。

**注意事项**

- 颜色通道按 `0..255` 写入，模拟时会四舍五入并夹取到合法范围。
- 没有下一节点、下一节点时间不递增或 `math.nextafter()` 无可用间隙时相应失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setLineColorEase()`

**函数声明**

```python
setLineColorEase(chart: dict, indexlist: int | list,
                 easetype: int | list,
                 precision: int | float = 1,
                 inserttype: str = "uniform",
                 isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 线色覆盖节点索引；`[lineindex, colorindex]` 或二维列表 |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改线色覆盖节点从 `startColor` 到 `endColor` 的颜色过渡。

**索引格式**

- `indexlist` 使用 `[lineindex, colorindex]`；负索引从末尾计算。
- 选择节点后必须存在下一个线色覆盖节点。

**缓动行为**

- `easetype=0`：原生线性过渡，不修改节点。
- `easetype=13`：把当前节点 `endColor` 设为 `startColor`。
- `easetype=14`：在当前节点后插入 `startColor=endColor=原 endColor` 的节点。
- 其它 `easetype`：插入目标颜色采样节点，当前节点 `endColor` 接第一个采样值，最后一个插入节点接回原 `endColor`。

**注意事项**

- 没有下一节点、时间不递增或 `math.nextafter()` 无可用间隙时相应失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。
- 插入颜色节点不会改变引导线几何或 `floorPosition`。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setCanvasPositionEase()`

**函数声明**

```python
setCanvasPositionEase(chart: dict, indexlist: int | list,
                      easetype: int | list,
                      precision: int | float = 1,
                      inserttype: str = "uniform",
                      isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 画布位置节点索引；`[canvasindex, pointindex]` 或二维列表 |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改指定画布 `xPositionKeyPoints` 中节点位置值的缓动。

**索引格式**

- `indexlist` 使用 `[canvasindex, pointindex]`；负索引从末尾计算。
- 选择节点后必须在同一数组内存在下一个节点。

**缓动行为**

- `easetype=0..18`：直接写入当前节点 `easeType`。
- `easetype=19..22`：在时间中点插入位置平均值节点，当前节点写前半段，插入节点写后半段（`15+16` / `16+15` / `18+17` / `17+18`）。
- `easetype=23..25` 或 Cubic Bezier：插入目标位置采样节点，当前节点和插入节点写 `easeType=0`。

**注意事项**

- 没有下一节点或时间不递增时失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。
- 画布位置节点会影响相关引导线和 Note 的高度，公开添加函数会重算 `floorPosition`。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setCanvasSpeedEase()`

**函数声明**

```python
setCanvasSpeedEase(chart: dict, indexlist: int | list,
                   easetype: int | list,
                   precision: int | float = 1,
                   inserttype: str = "uniform",
                   isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 画布流速节点索引；`[canvasindex, pointindex]` 或二维列表 |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改指定画布 `speedKeyPoints` 中流速值从当前节点到下一节点的过渡。

**索引格式**

- `indexlist` 使用 `[canvasindex, pointindex]`；负索引从末尾计算。
- 选择节点后必须在同一数组内存在下一个节点。

**缓动行为**

- `easetype=13`：原生零阶保持，不修改节点。
- `easetype=14`：在 `math.nextafter(当前时间, 下一节点时间)` 插入下一节点的流速值，形成瞬时跳变。
- 其它 `easetype`：按采样点插入流速节点；不直接修改当前节点或下一节点的流速值。

**注意事项**

- 流速节点没有通用缓动字段，因此 `0..12`、`15..25` 与 Cubic Bezier 都采用插入节点模拟。
- 没有下一节点、时间不递增或 `math.nextafter()` 无可用间隙时相应失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。
- 添加、修改流速后会重算相关 `floorPosition`。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setCameraPositionEase()`

**函数声明**

```python
setCameraPositionEase(chart: dict, indexlist: int | list,
                      easetype: int | list,
                      precision: int | float = 1,
                      inserttype: str = "uniform",
                      isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 摄像机位置节点扁平索引，单个 `int` 或 `list[int]` |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改摄像机 `xPositionKeyPoints` 中位置值从当前节点到下一节点的过渡。

**索引格式**

- `indexlist` 是扁平摄像机位置节点索引；负索引从末尾计算。
- 选择节点后必须存在下一个摄像机位置节点。

**缓动行为**

- `easetype=0..18`：直接写入当前节点 `easeType`。
- `easetype=19..22`：在时间中点插入位置平均值节点，当前节点写前半段，插入节点写后半段。
- `easetype=23..25` 或 Cubic Bezier：插入目标位置采样节点，当前节点和插入节点写 `easeType=0`。

**注意事项**

- 没有下一节点或时间不递增时失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。
- 摄像机节点不影响音符高度，不触发全谱 `floorPosition` 重算。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

### `setCameraScaleEase()`

**函数声明**

```python
setCameraScaleEase(chart: dict, indexlist: int | list,
                   easetype: int | list,
                   precision: int | float = 1,
                   inserttype: str = "uniform",
                   isFailAddAllowed: bool = False) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `indexlist` | `int \| list` | 是 | - | 摄像机缩放节点扁平索引，单个 `int` 或 `list[int]` |
| `easetype` | `int \| list` | 是 | - | 目标缓动 `0..25`，或 Cubic Bezier 列表 |
| `precision` | `int \| float` | 否 | `1` | 插入数量或误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 节点插入策略 |
| `isFailAddAllowed` | `bool` | 否 | `False` | 失败时是否跳过失败索引并继续 |

**用途**

修改摄像机 `scaleKeyPoints` 中缩放值从当前节点到下一节点的过渡。

**索引格式**

- `indexlist` 是扁平摄像机缩放节点索引；负索引从末尾计算。
- 选择节点后必须存在下一个摄像机缩放节点。

**缓动行为**

- `easetype=0..18`：直接写入当前节点 `easeType`。
- `easetype=19..22`：在时间中点插入缩放平均值节点，当前节点写前半段，插入节点写后半段。
- `easetype=23..25` 或 Cubic Bezier：插入目标缩放采样节点，当前节点和插入节点写 `easeType=0`。

**注意事项**

- 没有下一节点或时间不递增时失败。
- 插入或计算出的缩放值必须大于 `0.0`；Cubic Bezier 产生非正缩放时该索引失败。
- `uniform` / `arc` / `curvature` 不限制插入数量；`recursion` / `priority` 每个 tick 最多 48 个节点（含整数端点），超限时在该 tick 内按时间均匀挑选并继续后续 tick。
- 摄像机节点不影响音符高度，不触发全谱 `floorPosition` 重算。

**返回值**

成功返回 `[]`；原子模式失败返回 `[失败索引]`；`isFailAddAllowed=True` 返回全部失败索引；整体输入非法返回 `[-1]`。

## 绘图与文字函数

本组函数直接生成线、区域或文字几何；具体返回值以各函数章节为准。

### `drawPolygon()`

**函数声明**

```python
drawPolygon(chart: dict, canvasindex: int, pointlist: list,
            isDrawBorder: bool, isFillGraph: bool,
            precision: float = 0.005, bordersize: int | list = [1],
            fillerstyle: str = "linear",
            fillerinfo: list | None = None,
            holelist: list | None = None,
            holecolor: list | str = [0, 0, 0, 0],
            timemultiple: float = 1.65) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 目标画布索引；支持负数从末尾计算 |
| `pointlist` | `list` | 是 | - | 多边形顶点的线节点规格列表 |
| `isDrawBorder` | `bool` | 是 | - | 是否绘制边框 |
| `isFillGraph` | `bool` | 是 | - | 是否绘制内部填充 |
| `precision` | `float` | 否 | `0.005` | 填充线间距 / 角度间隔 / 边界相邻线距离 / 边框层间距 |
| `bordersize` | `int \| list` | 否 | `[1]` | 要绘制的边框层号；支持正负层号；默认不使用第 0 层以避免与填充线重合遮挡 |
| `fillerstyle` | `str` | 否 | `"linear"` | 填充方式：`"linear"` / `"radial"` / `"conic"` / `"radialBorder"` / `"conicBorder"` |
| `fillerinfo` | `list \| None` | 否 | `None` | 填充颜色与中心信息；`isFillGraph=True` 时必需 |
| `holelist` | `list \| None` | 否 | `None` | 孔洞点列表；每个元素是一个闭合孔洞的点规格列表 |
| `holecolor` | `list \| str` | 否 | `[0,0,0,0]` | 孔洞区域填充线使用的颜色；默认全透明 |
| `timemultiple` | `float` | 否 | `1.65` | 时间方向视觉倍率；只影响径向/锥形渐变计算 |

**用途**

在指定画布上绘制一个凸多边形或简单凹多边形。填充线和边框线都由普通引导线组成；成功返回所有新线的索引列表。

**pointlist 与多边形**

- `pointlist` 至少需要 3 个线节点规格。
- 只使用每个节点的 `xPosition` 和 `time`：
  - `xPosition` 为 x 坐标；
  - `time` 为 y 坐标。
- 忽略输入节点的 `canvasIndex` 和 `easeType`，输出线统一使用目标画布、`easeType=0`。
- 先尝试组成凸多边形：
  - 如果输入点全部是凸包顶点，按凸包顺序排列；
  - 并旋转到以输入 `pointlist` 的第一个顶点为起点。
- 如果凸包不能包含全部输入点，按输入顺序尝试组成凹多边形。
- 凹多边形必须是简单多边形：非相邻边不能相交；重复点、零长度边、自交或面积为 0 时返回 `None`。
- 连续共线点允许存在。
- 保留每个顶点的颜色作为边框颜色。

**precision**

- `linear`：平行填充线之间的垂直距离。
- `radial` / `conic`：角度间隔为 `2π * precision`。
- `radialBorder` / `conicBorder`：沿多边形边界采样的相邻射线距离。
- 边框：相邻层之间的偏移距离。

**timemultiple**

- 只影响 `radial` / `conic` / `radialBorder` / `conicBorder` 的颜色渐变计算。
- 计算时将时间方向的差值乘以 `timemultiple`，用于径向距离和锥形角度的视觉归一化。
- 不改变输入顶点坐标，也不改变输出线节点中的 `time` 值；线性填充完全不受影响。
- 必须大于 `0`；默认 `1.65`。
- 当谱面流速设为 `6.5`、画布流速设为 `1` 时，默认值 `1.65` 约等于 x 轴与时间轴的视觉比例。

**bordersize**

- `int` 表示从第 `0` 层到该层号的所有层：
  - `bordersize=2` → `0,1,2`；
  - `bordersize=-2` → `-2,-1,0`；
  - `bordersize=0` → `0`。
- `list[int]` 表示精确指定要绘制的层，例如 `[0, 2, -1]`；空列表表示无边框。
- 层号 `0` 为原多边形边界；正数向外偏移，负数向内偏移。
- 第 `k` 层偏移 `k * precision`。
- 默认值是 `[1]` 而不是 `0`：第 `0` 层边框与外轮廓填充线重合，可能在部分渲染器里造成遮挡；需要原边界边框时可显式传 `bordersize=0` 或包含 `0` 的列表。
- 若某一层向内/向外偏移后多边形退化、自交、分裂成多个独立轮廓，或偏移后出现负 `time`，则跳过该层，并跳过同方向更远的层；其余层继续绘制。
- 每层每条多边形边使用一条独立的引导线。
- 边框使用对应 `pointlist` 顶点的颜色；偏移层沿用原顶点颜色。
- 最终按层号从小到大输出边框线。

**holelist / holecolor**

- `holelist=None` 或 `[]` 表示没有孔洞。
- `holelist` 的每个元素是一个闭合孔洞的点规格列表，例如：
  ```python
  holelist = [
      [hole1_point1, hole1_point2, ...],
      [hole2_point1, hole2_point2, ...],
  ]
  ```
- 孔洞可以使用简单凹多边形；每个孔洞的闭合性、退化、重复点和自交校验与 `pointlist` 相同。
- 孔洞不要求完全位于外轮廓内部，可以超出外轮廓；超出部分不会产生额外填充。
- 孔洞只作用于填充，不影响边框：
  - 外轮廓边框仍按 `pointlist` 和 `bordersize` 绘制；
  - 不会为孔洞自动创建边框。
- 孔洞内的填充线颜色改为 `holecolor`：
  - 默认 `[0,0,0,0]`，即透明，形成孔洞；
  - 也可以传不透明颜色，使孔洞区域用另一种颜色填充。
- 支持所有五种 `fillerstyle`：`linear` / `radial` / `conic` / `radialBorder` / `conicBorder`。
- 多个孔洞重叠时按并集处理；任一孔洞覆盖的位置都使用 `holecolor`。
- 孔洞边界处会生成相邻的可见色/`holecolor` 节点，形成硬切。
- 填充线与孔洞边界相切时只按切点处理，不会把整条相切线变成 `holecolor`。
- `isFillGraph=False` 时完全忽略 `holelist` 和 `holecolor`。
- `holelist` 合法但 `holecolor` 非法时返回 `None`；`holelist` 非法时返回 `None`。

**fillerinfo**

`isFillGraph=False` 时完全忽略 `fillerstyle` 和 `fillerinfo`；`isFillGraph=True` 且 `fillerinfo=None` 时失败。

线性填充：

```python
[angle, [color1, point1], [color2, point2], ...]
```

- `angle` 为 `[0,360)` 的角度；0° 时填充线竖直，颜色从左向右渐变，顺时针旋转。
- 颜色节点至少一个。
- 颜色和位置可以全部省略位置，写成：

```python
[angle, color1, color2, ...]
```

此时按颜色列表顺序在 `[0,1]` 上均匀分配。

径向填充：

```python
[position, time, [color1, point1], [color2, point2], ...]
```

- `position` / `time` 是中心点的 x / y 坐标，必须在多边形内部或边界上。
- `point` 以“中心点到多边形最远顶点的距离”为 1 归一化。
- 也可以省略所有 `point`，写成 `[position, time, color1, color2, ...]`。

锥形填充：

```python
[position, time, angle, [color1, point1], [color2, point2], ...]
```

- `position` / `time` 是中心点。
- `angle` 是渐变起始角度；0° 为竖直向上，顺时针旋转。
- `point` 按从起始角度开始的顺时针 360° 归一化到 `[0,1]`。
- 也可以省略所有 `point`，写成 `[position, time, angle, color1, color2, ...]`。

径向边界填充 / 锥形边界填充：

- `fillerstyle="radialBorder"` 使用与径向填充相同的颜色规则；
- `fillerstyle="conicBorder"` 使用与锥形填充相同的颜色规则；
- 几何上仍从中心向边界发射线，但射线方向改为沿多边形边界按距离采样：
  - 从第一个顶点开始；
  - 每隔 `precision` 的边界弧长取一个采样点；
  - 当再加一个 `precision` 会回到第一个采样点或越过它时停止。
- `precision >= 多边形周长` 时只绘制一条射线。

**凹多边形的填充空隙**

- 线性填充在凹多边形中可能出现多个可见区间；
- 径向/锥形填充的射线也可能穿出再进入多边形；
- 这些空隙仍由同一条线表达：
  - 可见区间使用填充颜色；
  - 空隙使用 `alpha=0` 的透明颜色；
  - 在可见区间和空隙边界放置相邻的可见/透明节点，形成硬切；
  - 不会为每个空隙额外创建一条线。
- `radialBorder` / `conicBorder` 同样使用该规则。

颜色节点位置必须升序，允许重复；重复位置形成颜色突变。例如：

```python
[(绿, 0), (红, 0.5), (蓝, 0.5), (黄, 1)]
```

表示 `0..0.5` 为绿→红，在 `0.5` 处为红，随后突变为蓝，再蓝→黄。

**颜色插值**

- 颜色支持 `str` / RGB(A) 列表 / RGBA Dict，内部统一为 RGBA 列表。
- 颜色通道按 RGBA 四通道线性插值。
- 径向渐变会沿射线计算边界颜色；边界颜色按实际 `半径 / 最远顶点距离` 单独采样，不强制等于颜色节点颜色。
- 仅当射线边界时间小于中心时间时，径向渐变中重复位置的颜色节点才会展开成极小的径向区间，并将切换中心向多边形中心内缩 `0.008` 个谱面坐标单位，以补偿编辑器/游戏渲染偏移；其它方向保持原位置不变。

**返回与失败**

- 成功返回新创建线的索引列表：填充线在前，边框线在后；边框按内层到外层、每层按多边形边顺序排列。
- `isDrawBorder=False` 且 `isFillGraph=False` 时返回 `[]`。
- 任意一条线创建失败时回退全部新线并返回 `None`。
- `isFillGraph=True` 时，`holelist` 非法、孔洞退化/自交，或 `holecolor` 非法时返回 `None`。
- `timemultiple` 不为有限正数时返回 `None`。
- 整体输入非法返回 `None`。

**注意事项**

- 生成线的判定环颜色统一为全透明。
- 允许同一 `time` 的两个线节点形成水平线段。
- 填充线和边框线创建完成后统一执行一次 `refresh(mode="all", type="all")`，重新计算 `floorPosition`。
- 画布索引支持负数，但输出节点使用解析后的实际画布索引。

### `drawEllipse()`

**函数声明**

```python
drawEllipse(chart: dict, canvasindex: int, centerpoint: dict,
            xLength: float, yLength: float,
            isDrawBorder: bool, isFillGraph: bool,
            angle: float = 0.0, lineprecision: float = 0.005,
            colorList: list | None = None, bordersize: int | list = [1],
            fillerstyle: str | None = None, fillerinfo: list | None = None,
            inserttype: str | None = None,
            insertprecision: object = None,
            timemultiple: float = 1.65) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 目标画布索引；支持负数从末尾计算 |
| `centerpoint` | `dict` | 是 | - | 椭圆中心；只使用 `xPosition` 和 `time` |
| `xLength` | `float` | 是 | - | x 方向半轴长度，必须大于 0 |
| `yLength` | `float` | 是 | - | y 方向半轴长度，必须大于 0 |
| `isDrawBorder` | `bool` | 是 | - | 是否绘制椭圆边框 |
| `isFillGraph` | `bool` | 是 | - | 是否绘制内部填充 |
| `angle` | `float` | 否 | `0.0` | 顺时针旋转角度；只旋转形状，不旋转填充渐变 |
| `lineprecision` | `float` | 否 | `0.005` | 填充线参数 / 边界射线间距 / 边框层间距；必须大于 0 |
| `colorList` | `list \| None` | 否 | `None` | 边框四向颜色；`isDrawBorder=True` 时必需 |
| `bordersize` | `int \| list` | 否 | `[1]` | 边框层号；规则同 `drawPolygon()`；默认不使用第 0 层以避免与填充线重合遮挡 |
| `fillerstyle` | `str \| None` | 否 | `None` | `"linear"` / `"radial"` / `"conic"` / `"radialBorder"` / `"conicBorder"` |
| `fillerinfo` | `list \| None` | 否 | `None` | 填充颜色与中心信息；`isFillGraph=True` 时必需 |
| `inserttype` | `str \| None` | 否 | `None` | 非 90° 边框插入策略：`"uniform"` / `"arc"` / `"curvature"` / `"recursion"` / `"priority"` |
| `insertprecision` | `int \| float \| None` | 否 | `None` | 前三种为每半弧总节点数；后两种为弦高误差阈值 |
| `timemultiple` | `float` | 否 | `1.65` | 时间方向倍率；有效 `yLength = yLength * timemultiple` |

**用途**

在指定画布上绘制椭圆轮廓和/或内部填充，返回所有新建线的索引列表。椭圆以 `centerpoint` 为中心，`xLength` / `yLength` 是半轴长度，不是直径。

**几何约定**

- 未旋转的四个轴端点固定为：
  - 上：`(centerX, centerTime + yLength)`；
  - 右：`(centerX + xLength, centerTime)`；
  - 下：`(centerX, centerTime - yLength)`；
  - 左：`(centerX - xLength, centerTime)`。
- 正值 `angle` 按顺时针旋转；旋转后四个端点的描述名仍按未旋转的上/右/下/左固定。
- `colorList` 必须是四个颜色，顺序为上、右、下、左；颜色支持 `str` / RGB(A) 列表 / RGBA Dict。边框节点沿该顺序做 RGBA 线性插值；旋转只改变端点坐标，不改变颜色名。
- `timemultiple` 会把有效 y 半轴改为 `yLength * timemultiple`；`centerpoint["time"]` 本身不再额外缩放。
  - 因此实际输出点的 time 跨度会随 `timemultiple` 变化，但中心时间保持不变。
  - 必须大于 `0`；默认 `1.65`。
  - 当谱面流速设为 `6.5`、画布流速设为 `1` 时，默认值 `1.65` 约等于 x 轴与时间轴的视觉比例。

**90° 倍数**

`angle` 对 360° 取模后落在 `0 / 90 / 180 / 270` 时：

- 使用四个旋转后的轴端点，按 `time` 从低到高排列。
- 最低时间端点到两个中间时间端点各建一条线，`easeType=16`（Out Circle）。
- 两个中间时间端点到最高时间端点各建一条线，`easeType=15`（In Circle）。
- 每层共四条线；每条线两端使用对应上/右/下/左端点的 `colorList` 颜色。
- `inserttype` / `insertprecision` 完全忽略，包括非法值。

**非 90°**

- 计算旋转后椭圆上 `time` 最低点和最高点。
- 在最低点与最高点之间拆成左右两条半椭圆，分别生成一条多节点线。
- 最低点、最高点和四个旋转后的轴端点会按所在半弧强制加入对应线；即使 `insertprecision` 很小，也不会丢弃这些点。
- `inserttype="uniform"` / `"arc"` / `"curvature"` 时，`insertprecision` 是每条半弧的总节点数，强制点计入该数量；强制点本身超过该数量时，输出会超过 `insertprecision`。
- `inserttype="recursion"` / `"priority"` 时，按弦高误差细分，并限制每条线每个 tick 最多 48 个节点；强制点始终保留。
- 非 90° 且 `isDrawBorder=True` 时，`inserttype` 和 `insertprecision` 必需；90° 或 `isDrawBorder=False` 时忽略。

**bordersize**

- `int` / `list[int]` 的展开规则与 `drawPolygon()` 相同；默认 `[1]`。
- 第 `k` 层使用半轴 `xLength + k * lineprecision` 和
  `yLength + k * lineprecision`；`k=0` 为原边界，正数向外，负数向内。
- 默认不使用第 `0` 层，避免原边界与填充线重合造成遮挡；需要原边界时显式指定 `0`。
- 若某一层任一轴不大于 0，则跳过该层，并跳过同方向更远的层；其它方向继续。
- 90° 每层输出四条线；非 90° 每层输出两条线。
- 边框颜色由 `colorList` 上/右/下/左固定顺序插值；90° 使用端点颜色，非 90° 使用节点参数颜色。
- 最终按层号从小到大输出边框线；层内按生成顺序输出。

**填充**

填充与轮廓表示独立；即使 `isDrawBorder=False`，也可以单独生成填充。`fillerstyle` 支持 `drawPolygon()` 的五种方式，`fillerinfo` 的结构与颜色规则相同：

- `linear`：平行填充线；
- `radial` / `conic`：中心射线填充；
- `radialBorder`：从中心向椭圆边界、从上方 0° 开始，按 `lineprecision` 的边界弧长顺时针采样射线；颜色沿用径向规则；
- `conicBorder`：从中心向椭圆边界、从 `fillerinfo` 的起始角度开始，按 `lineprecision` 的边界弧长顺时针采样射线；颜色按从该角度开始的锥形规则；
- `isFillGraph=True` 且 `fillerstyle=None` 或 `fillerinfo=None` 时返回 `None`；
- `isFillGraph=False` 时完全忽略 `fillerstyle` 和 `fillerinfo`。

**返回与失败**

- 成功返回新创建线的索引列表：填充线在前，边框线在后；边框按层号从小到大排列。
- 两个绘制开关都为 `False` 时返回 `[]`。
- 输入非法、填充/边框参数不一致或任意一条线创建失败时，回退全部新线并返回 `None`。
- 失败包括：`centerpoint` 不是 dict、半轴不大于 0、`lineprecision` 不大于 0、`timemultiple` 不为有限正数、`colorList` 缺失或不是四色、非 90° 边框缺少插入参数、`fillerinfo` 中心在椭圆外等。
- 生成线的判定环颜色统一为全透明。
- 所有线创建完成后统一执行一次 `refresh(mode="all", type="all")`，重新计算 `floorPosition`。

**注意事项**

- `centerpoint` 的 `color` / `easeType` / `canvasIndex` 被忽略；只取 `xPosition` 和 `time`。
- 旋转不会改变渐变角度；线性填充的 `angle`、锥形填充的起始角度均独立于椭圆旋转角。
- 90° 分支不检查 `inserttype` / `insertprecision`；非 90° 填充-only 调用也不检查它们。
- `colorList` 在 `isDrawBorder=False` 时忽略。

### `getClosedRegion()`

**函数声明**

```python
getClosedRegion(chart: dict, canvasindex: int, lineindexlist: list,
                isCreateCrossPoint: bool = True,
                isInsertPoint: bool = True,
                precision: int | float = 1,
                inserttype: str = "uniform") -> list[list[dict]] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 目标画布索引；支持负数从末尾计算 |
| `lineindexlist` | `list` | 是 | - | 参与计算且必须位于同一画布的线索引列表 |
| `isCreateCrossPoint` | `bool` | 否 | `True` | 是否把新交点直接作为区域边界点 |
| `isInsertPoint` | `bool` | 否 | `True` | 是否按实际缓动曲线求交并插入模拟节点 |
| `precision` | `int \| float` | 否 | `1` | `uniform`/`arc`/`curvature` 为每个原节点区间的插入数量；`recursion`/`priority` 为弦高误差阈值 |
| `inserttype` | `str` | 否 | `"uniform"` | 插入策略：`"uniform"` / `"arc"` / `"curvature"` / `"recursion"` / `"priority"` |

**用途**

计算 `lineindexlist` 中所有线在同一画布上围成的闭合区域，并返回所有有界区域。每个区域是一个按顺序排列的线节点规格列表。

**返回值与区域语义**

- 返回 `[[point1-1, point1-2, ...], [point2-1, ...], ...]`。
- 返回**所有**有界闭合区域，而不是只返回最外层区域。
- 环形/带洞结构不返回带洞多边形，而是将其边界拆成独立区域。例如外圈和内圈视为两个区域；外圈区域包含内圈区域。
- 类似 Venn 图的重叠结构返回每个最小闭合图形。
- 每个区域按顺时针排列，起点优先取 `lineindexlist` 第一条线的第一个交点对应的点。
- 没有闭合区域、输入非法或无法形成合法简单区域时返回 `None`。
- 函数只读取谱面，不修改原 `chart`。

**isCreateCrossPoint**

- `True`：交点直接作为区域边界点。交点本身已有节点时使用该节点；否则返回新计算出的交点。
- `False`：不在交点处新建节点，而是用已有节点替换交点，优先规则为：
  1. 交点处已有节点时直接使用；
  2. 否则优先使用两个相邻交点之间的内部节点；
  3. 同一条线在相邻两个交点之间的全部原节点都保留；
  4. 如果该线在这个区间内完全没有内部节点，则取交点外侧、沿该线相邻的已有节点；
  5. 同一节点被多个交点选中时只保留一次。
- 替换后优先沿原线追踪；如果追踪结果自交，则对同一组替代节点按区域中心顺时针极角重排；仍自交、少于 3 个点或面积非法时返回 `None`。
- 外侧节点只看“沿原线相邻”的节点，不按欧氏距离选择。

**isInsertPoint**

- `False`：所有节点之间一律按直线段处理；交点、闭合判断和返回点都忽略实际 `easeType`。
- `True`：使用实际 `easeType` 曲线求交并判断闭合；边界确定后再插入模拟节点。
- 插入点**不参与** `isCreateCrossPoint=False` 的内部/外部节点选择，因为交点先在平滑曲线上计算。
- 线性段（`easeType=0`）不插入节点。
- `precision` / `inserttype` 的语义与 `setXxxEase()` 一致：
  - `uniform` / `arc` / `curvature`：每个原节点区间插入 `precision` 个节点；
  - `recursion` / `priority`：`precision` 为弦高误差阈值。
- 实际缓动可能导致线性时封闭而缓动后不封闭，或反之；函数按 `isInsertPoint` 指定的几何模型判断。

**颜色与节点规格**

- 已有节点保留原颜色。
- 同一位置有多个已有节点时，取 `lineindexlist` 中靠前的线的节点颜色。
- 新交点没有已有节点时，取 `lineindexlist` 中靠前的相交线在该交点的颜色插值。
- 插入节点的颜色按原线节点两端颜色线性插值。
- 返回点统一 `easeType=0`，使用目标画布索引，并包含 `time` / `xPosition` / `canvasIndex` / `easeType` / `color` 字段。
- 返回点可直接作为 `drawPolygon()` 的 `pointlist` 使用。

**失败条件**

- `lineindexlist` 为空、索引非法或任一线不在目标画布。
- 所选线没有形成任何有界闭合区域。
- 线集合出现完全重合、无法拆分的重叠段。
- 区域无法通过简单性校验，且 `isCreateCrossPoint=False` 的极角回退仍无法形成简单多边形。
- `isInsertPoint=True` 时 `inserttype` 或 `precision` 非法。

**注意事项**

- `lineindexlist` 的顺序会影响起点选择和同位置颜色优先级。
- 返回区域中不包含重复的首尾点；闭合关系由列表顺序隐含。
- 结果可用于：

```python
regions = getClosedRegion(chart, 0, [0, 1, 2, 3])
if regions is not None:
    for region in regions:
        drawPolygon(chart, 0, region, True, True, ...)
```

### `drawText()`

**函数声明**

```python
drawText(chart: dict, canvasindex: int, fontpath: object, text: str,
         position: float, time: float, fontsize: float,
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
         precision: float | None = None) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 目标画布索引；支持负数从末尾计算 |
| `fontpath` | `str \| PathLike` | 是 | - | 单个 TTF/OTF/TTC 字体文件路径 |
| `text` | `str` | 是 | - | 单行文字；不支持换行 |
| `position` | `float` | 是 | - | 文字水平定位锚点 |
| `time` | `float` | 是 | - | 文字填充轮廓的底部位置 |
| `fontsize` | `float` | 是 | - | X 方向字号；必须大于 0 |
| `color` | `list \| str` | 否 | `"#000000"` | 文字填充颜色 |
| `weight` | `int \| float \| None` | 否 | `None` | 可变字体 `wght` 轴；静态字体忽略 |
| `letterspacing` | `float` | 否 | `0.0` | 字间距，单位是 em；实际距离为 `letterspacing * fontsize` |
| `align` | `str` | 否 | `"left"` | `"left"` / `"center"` / `"right"` |
| `bordersize` | `int \| list \| None` | 否 | `None` | 线框层号；语义同 `drawPolygon()` 的 `bordersize`，`None` / `[]` 无边框 |
| `bordercolor` | `list \| str` | 否 | `"#000000"` | 线框颜色 |
| `isFillGraph` | `bool` | 否 | `True` | 是否填充文字；`False` 时只画线框、不画背景 |
| `background` | `bool` | 否 | `False` | 是否绘制背景；仅填充模式有效 |
| `backgroundcolor` | `list \| str` | 否 | `"#000000"` | 背景颜色，同时用作文字孔洞填充色 |
| `padding` | `float` | 否 | `0.0` | 背景相对文字/边框外接框的扩展距离 |
| `timemultiple` | `float` | 否 | `1.65` | Y 方向相对 X 方向的伸缩倍数；必须大于 0 |
| `isFlipX` | `bool` | 否 | `False` | 以整段文字中心为轴水平镜像 |
| `precision` | `float \| None` | 否 | `None` | 填充线间距；`None` 时按字号自动取 `max(0.001, fontsize * 0.01)` |

**用途**

使用单个字体文件绘制单行文字。字体轮廓会被转成闭合图形，并通过
`drawPolygon()` 进行线性填充。文字可以包含多个字符，一个字符也可以包含多个填充
组件和孔洞。

**坐标与排版**

- 字体原始坐标向上对应谱面 `time` 增大，不做 Y 翻转。
- `time` 对应整段文字**填充轮廓的最低点**；边框和背景可以继续向下/外延伸。
- X 方向缩放为 `fontsize / unitsPerEm`。
- Y 方向缩放为 `X缩放 * timemultiple`。
- `timemultiple` 只影响字形纵向尺寸，不影响用于定位的 `time` 值。
- 当谱面流速设为 `6.5`、画布流速设为 `1` 时，默认值 `1.65` 约等于 x 轴与时间轴的视觉比例。
- `letterspacing` 使用 em 单位；实际间距为 `letterspacing * fontsize`。
- `align` 决定 `position` 是整段文字的左端、中心还是右端。
- 不支持换行和行距；需要多行时由用户多次调用。
- `isFlipX=True` 时，字形、字符顺序、边框和背景布局整体以文字中心为轴镜像；
  `align` 的锚点行为仍然保持正确。

**填充**

- `isFillGraph=True` 时只支持 `linear` 填充。
- `isFillGraph=False` 时不绘制文字填充、不绘制背景，只绘制线框。
- `precision` 是填充线间距，同时也是边框层偏移距离。
- `precision=None` 时自动使用 `max(0.001, fontsize * 0.01)`；字号越小，间距自动越细。
- 一个字符的多个组件分别填充；孔洞通过 `drawPolygon(holelist=...)` 扣除。
- 背景开启时，文字孔洞使用 `backgroundcolor` 填充；背景关闭时孔洞透明。

**边框 / 线框**

- `bordersize` 与 `drawPolygon()` 的 `bordersize` 语义一致：
  - `None` / `[]`：无边框；
  - `0` → `[0]`；
  - `1` → `[0,1]`；
  - `-1` → `[-1,0]`；
  - `list`：精确指定层号。
- 第 `k` 层偏移距离为 `k * precision`；正数向外，负数向内。
- 第 `0` 层可能与文字填充线重合；填充模式下若担心遮挡，可只使用正/负层。
- 边框不再是填充环，而是沿字形轮廓的普通线；线宽由游戏/编辑器的线渲染决定。
- 外轮廓和孔洞轮廓都画。
- 每条轮廓边生成一条 `addLine()` 线，避免 `addLine()` 对非时间单调轮廓排序。
- 某一层偏移失效、自交、组件合并或孔洞碰撞时，跳过该层及同方向更远的层。
- `isFillGraph=True` 时填充和线框可以同时存在。
- `isFillGraph=False` 时只画线框。

**背景**

- 仅 `isFillGraph=True` 且 `background=True` 时绘制。
- 背景矩形由文字和线框各层的外接框加 `padding` 生成。
- 背景区域为“背景矩形 - 文字填充区域”，不依赖谱面层级；线框线绘制在背景之上/之间。
- 背景扣除文字后可能分裂成多个多边形，函数会分别绘制。
- `isFillGraph=False` 或 `background=False` 时忽略 `backgroundcolor` 和 `padding`。

**依赖**

字体功能需要可选依赖：

```powershell
pip install rizchartfunction[font]
```

或手动安装：

```text
fontTools shapely numpy Pillow scikit-image
```

**返回与失败**

- 成功返回所有新建线的索引列表：背景线在前，文字填充线其次，线框线最后。
- `isFillGraph=False` 时只返回线框线。
- `isFillGraph=False` 且 `bordersize=None` / `[]` 时返回 `[]`。
- 空字符串返回 `[]`。
- 字体文件、字形、颜色、`bordersize`、参数非法，或任意一段绘制失败时回滚已创建线并返回 `None`。
- 文本中包含换行符时返回 `None`。
- 字体缺少对应字符时返回 `None`。
- 静态字体传入 `weight` 时使用默认字重，不报错。

### `drawThinText()`

**函数声明**

```python
drawThinText(chart: dict, canvasindex: int, fontpath: object, text: str,
             position: float, time: float, fontsize: float,
             color: list | str = "#000000",
             weight: int | float | None = None,
             letterspacing: float = 0.0,
             align: str = "left",
             timemultiple: float = 1.65,
             isFlipX: bool = False,
             smoothness: float = 0.5) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 目标画布索引；支持负数从末尾计算 |
| `fontpath` | `str \| PathLike` | 是 | - | 单个 TTF/OTF/TTC 字体文件路径 |
| `text` | `str` | 是 | - | 单行文字；不支持换行 |
| `position` | `float` | 是 | - | 文字水平定位锚点 |
| `time` | `float` | 是 | - | 文字骨架的最低点位置 |
| `fontsize` | `float` | 是 | - | X 方向字号；必须大于 0 |
| `color` | `list \| str` | 否 | `"#000000"` | 细线颜色 |
| `weight` | `int \| float \| None` | 否 | `None` | 可变字体 `wght` 轴；静态字体忽略 |
| `letterspacing` | `float` | 否 | `0.0` | 字间距，单位是 em；实际距离为 `letterspacing * fontsize` |
| `align` | `str` | 否 | `"left"` | `"left"` / `"center"` / `"right"` |
| `timemultiple` | `float` | 否 | `1.65` | Y 方向相对 X 方向的伸缩倍数；必须大于 0 |
| `isFlipX` | `bool` | 否 | `False` | 以整段文字中心为轴水平镜像 |
| `smoothness` | `float` | 否 | `0.5` | 骨架平滑/细节程度；范围 `0.0` 到 `1.0` |

**用途**

使用单个字体文件提取字形骨架，并把骨架分支画成细线。不填充字形、不绘制
线框、不绘制背景；只输出一条条普通引导线。适合需要“一笔一画”或极细文字轮廓
的谱面效果。

**坐标与排版**

- 字体原始坐标向上对应谱面 `time` 增大，不做 Y 翻转。
- `time` 对应整段文字**骨架的最低点**；不使用字形填充轮廓底部。
- `position`、`align`、`letterspacing`、`timemultiple` 的语义与 `drawText()` 相同。
- 当谱面流速设为 `6.5`、画布流速设为 `1` 时，默认值 `1.65` 约等于 x 轴与时间轴的视觉比例。
- `isFlipX=True` 时以整段文字中心为轴镜像布局。
- 空字符串、只有空白的文字或没有有效骨架时返回 `[]`。

**骨架与细节**

- 字形先按字号栅格化，再使用 `scikit-image` 的 `skeletonize` 提取一像素宽骨架。
- 端点、交叉点之间的骨架路径各自生成线；一个分支通常对应一条线。
- 由于谱面线节点要求 `time` 非递减，非时间单调的分支（例如 `O` 的闭环、
  `S` 的上下弯曲）会在时间极值处拆成多条线；下降段会反转节点顺序后写入。
- 单像素骨架（例如句点）会用一个很短的线段近似，避免完全消失。
- `smoothness=0.0` 保留最多骨架折点和细节；`smoothness=1.0` 使用最大简化与
  平滑，节点最少；默认 `0.5`。超出 `0.0` 到 `1.0` 返回 `None`。
- 不提供 `precision`；栅格采样密度由 `fontsize` 内部决定，并对超长文字做尺寸上限保护。

**依赖**

与 `drawText()` 相同，需要可选依赖：

```powershell
pip install rizchartfunction[font]
```

或手动安装：

```text
fontTools shapely numpy Pillow scikit-image
```

**返回与失败**

- 成功返回所有新建线的索引列表，每条线对应一段骨架。
- 空字符串、只有空白或没有可绘制骨架时返回 `[]`。
- 字体文件、字形、颜色、`smoothness`、排版参数非法，或任意一段建线失败时
  回滚已创建线并返回 `None`。
- 文本中包含换行符时返回 `None`。
- 字体缺少对应字符时返回 `None`。
- 静态字体传入 `weight` 时使用默认字重，不报错。

## 示例

以下示例展示插入函数的原子模式和允许失败模式；复制、缓动、绘图与文字示例见
各函数章节。

```python
from rizChartFunction import getLine, getLinePoint
from rizChartFunction import addLineByDict, addLinePointByDict

# 复制一条已有线并追加到末尾
line = getLine(chart, 0)
addLineByDict(chart, line)

# 向第 0 条线批量添加线节点；默认原子模式，失败会回退本批全部插入
failed = addLinePointByDict(chart, [
    {**point, "lineindex": 0, "time": 8.0},
    {**point, "lineindex": 0, "time": 6.0},
])
if failed:
    raise RuntimeError(f"插入失败的规格索引：{failed}")

# 允许失败：跳过失败规格并继续，返回所有失败索引
failed = addLinePointByDict(
    chart,
    [
        {**point, "lineindex": 0, "time": 10.0},
        {**point, "lineindex": 999, "time": 12.0},
    ],
    isFailAddAllowed=True,
)
print(f"跳过的规格索引：{failed}")
```
