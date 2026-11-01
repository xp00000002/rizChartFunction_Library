# chart 模块函数说明

[← 返回总览](README.md)

`chart.py` 负责颜色工具、主题/Riztime、画布、摄像机、引导线、Note 与 BPM 的创建和修改。

## 延迟计算

部分修改函数支持 `isDelayCalculate: bool = False`：

- `True` 时跳过 `floorPosition` 的计算/全谱重算，降低批量修改的开销。
- 新增或修改的单个节点会把 `floorPosition` 写成 `NaN`；全谱重算接口只跳过重算。
- 调用结束后需要执行 [`refresh()`](base.md#refresh) 修复所有高度值。
- 未 `refresh()` 前 `check()` / `export()` 会因 `NaN` 高度失败。
- 不建议日常频繁使用，仅在单次修改量较大时开启。

## 目录

- [延迟计算](#延迟计算)
- [基础字段](#基础字段)
  - [`setBaseBpm()`](#setbasebpm)
  - [`setDelay()`](#setdelay)
  - [`setFileVersion()`](#setfileversion)
- [颜色与主题](#颜色与主题)
  - [`rgb()`](#rgb)
  - [`rgba()`](#rgba)
  - [`mixColor()`](#mixcolor)
  - [`splitColor()`](#splitcolor)
  - [`setNormalTheme()`](#setnormaltheme)
  - [`setRiztime()`](#setriztime)
  - [`addRiztime()`](#addriztime)
  - [`deleteRiztime()`](#deleteriztime)
- [画布](#画布)
  - [`addCanvas()`](#addcanvas)
  - [`deleteCanvas()`](#deletecanvas)
- [画布位置](#画布位置)
  - [`addCanvasPosition()`](#addcanvasposition)
  - [`setCanvasPosition()`](#setcanvasposition)
  - [`deleteCanvasPosition()`](#deletecanvasposition)
- [画布流速](#画布流速)
  - [`addCanvasSpeed()`](#addcanvasspeed)
  - [`setCanvasSpeed()`](#setcanvasspeed)
  - [`deleteCanvasSpeed()`](#deletecanvasspeed)
- [摄像机](#摄像机)
  - [`addCameraPosition()`](#addcameraposition)
  - [`setCameraPosition()`](#setcameraposition)
  - [`deleteCameraPosition()`](#deletecameraposition)
  - [`addCameraScale()`](#addcamerascale)
  - [`setCameraScale()`](#setcamerascale)
  - [`deleteCameraScale()`](#deletecamerascale)
- [引导线](#引导线)
  - [`addLine()`](#addline)
  - [`deleteLine()`](#deleteline)
- [线节点](#线节点)
  - [`createLinePoint()`](#createlinepoint)
  - [`addLinePoint()`](#addlinepoint)
  - [`setLinePoint()`](#setlinepoint)
  - [`deleteLinePoint()`](#deletelinepoint)
- [判定环](#判定环)
  - [`createRingPoint()`](#createringpoint)
  - [`addRingPoint()`](#addringpoint)
  - [`setRingPoint()`](#setringpoint)
  - [`deleteRingPoint()`](#deleteringpoint)
- [线色覆盖](#线色覆盖)
  - [`createLineColor()`](#createlinecolor)
  - [`addLineColor()`](#addlinecolor)
  - [`setLineColor()`](#setlinecolor)
  - [`deleteLineColor()`](#deletelinecolor)
- [音符](#音符)
  - [`createNote()`](#createnote)
  - [`addNote()`](#addnote)
  - [`setNote()`](#setnote)
  - [`deleteNote()`](#deletenote)
- [BPM](#bpm)
  - [`addBpmShift()`](#addbpmshift)
  - [`setBpmShift()`](#setbpmshift)
  - [`deleteBpmShift()`](#deletebpmshift)

## 基础字段

### `setBaseBpm()`

**函数声明**

```python
setBaseBpm(chart: dict, basebpm: float, isFixedBpm: bool = False) -> object | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `basebpm` | `float` | 是 | - | 新的基准 BPM |
| `isFixedBpm` | `bool` | 否 | `False` | 是否保持实际 BPM 不变 |

**用途**

重置基准 BPM。

**输入限制**

谱面必须在 `time=0.0` 处有一个 BPM 节点。

**具体实现**

两种模式成功后都会按新的 BPM 时间轴重新计算整份谱面的相关 `floorPosition`（`bpmShifts`、`canvasMoves[].speedKeyPoints`、`lines[].linePoints`、`lines[].notes` 以及 Hold 尾部的 `otherInformations[2]`）。

**注意事项/细节**

`isFixedBpm=False` 时只修改 `bPM`；为 `True` 时同时按比例修改 `bpmShifts` 中每个节点的 `value`，保持 `旧 bPM * 旧 value = 新 bPM * 新 value`。

**返回值**

成功返回原 `bPM`。谱面缺少 `time=0.0` BPM 节点、结构非法、新 BPM 不为正数、固定 BPM 时缺少 `bpmShifts` 或节点非法、无法计算 `floorPosition` 等情况下返回 `None`，且不做部分修改。

**示例**

```python
from rizChartFunction import new, setBaseBpm

chart = new(175.0)

old_bpm = setBaseBpm(chart, 150.0)
print(old_bpm, chart["bPM"])  # 175.0 150.0

# 保持实际 BPM 不变：所有 bpmShifts.value 会按比例换算
chart2 = new(175.0)
setBaseBpm(chart2, 350.0, isFixedBpm=True)
print(chart2["bPM"], chart2["bpmShifts"][0]["value"])  # 350.0 0.5
```

### `setDelay()`

**函数声明**

```python
setDelay(chart: dict, delay: int) -> object | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `delay` | `int` | 是 | - | 新的谱面延迟，单位 ms |

**用途**

重置谱面延迟。

**输入限制**

`delay` 必须是 `int`（`bool` 不接受）。

**返回值**

修改 `chartDelayMs`，返回原值。

类型不正确或其他原因无法修改时返回 `None`，且不修改谱面。

### `setFileVersion()`

**函数声明**

```python
setFileVersion(chart: dict, fileversion: int) -> object | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `fileversion` | `int` | 是 | - | 新的文件版本 |

**用途**

重置文件版本。

**输入限制**

`fileversion` 必须是 `int`（`bool` 不接受）。

**返回值**

修改 `fileVersion`，返回原值。

类型不正确或其他原因无法修改时返回 `None`，且不修改谱面。

## 颜色与主题

### `rgb()`

**函数声明**

```python
rgb(red: int | float, green: int | float, blue: int | float) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `red` | `int \| float` | 是 | - | 红色通道，`int` 为 0-255，`float` 为 0.0-1.0 |
| `green` | `int \| float` | 是 | - | 绿色通道，`int` 为 0-255，`float` 为 0.0-1.0 |
| `blue` | `int \| float` | 是 | - | 蓝色通道，`int` 为 0-255，`float` 为 0.0-1.0 |

**用途**

把 RGB 通道转换为 0-255 的 `[r, g, b, 255]`。

**输入限制**

每个通道可以混用 `int` 和 `float`。

越界值夹到边界，非数字视为 0， `float` 四舍五入到 0-255。

**返回值**

返回 `[r, g, b, 255]`，例如 `rgb(52, 0.6, 255)` 返回 `[52, 153, 255, 255]`。

### `rgba()`

**函数声明**

```python
rgba(red: int | float, green: int | float, blue: int | float, alpha: int | float) -> list[int]
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `red` | `int \| float` | 是 | - | 红色通道，`int` 为 0-255，`float` 为 0.0-1.0 |
| `green` | `int \| float` | 是 | - | 绿色通道，`int` 为 0-255，`float` 为 0.0-1.0 |
| `blue` | `int \| float` | 是 | - | 蓝色通道，`int` 为 0-255，`float` 为 0.0-1.0 |
| `alpha` | `int \| float` | 是 | - | 透明度通道，`int` 为 0-255，`float` 为 0.0-1.0 |

**用途**

把 RGBA 通道转换为 0-255 的 `[r, g, b, a]`。

**输入限制**

每个通道可以混用 `int` 和 `float`。

越界值夹到边界，非数字视为 0， `float` 四舍五入到 0-255。

**返回值**

返回 `[r, g, b, a]`，例如 `rgba(52, 0.6, 255, 0.5)` 返回 `[52, 153, 255, 128]`。

### `mixColor()`

**函数声明**

```python
mixColor(basecolor: str | list, covercolor: str | list) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `basecolor` | `str \| list` | 是 | - | 基础色 |
| `covercolor` | `str \| list` | 是 | - | 覆盖色 |

**用途**

按 Rizline 覆盖色公式混合两个颜色。

**输入限制**

两个颜色都支持 HEX （`#RRGGBB`、`#RRGGBBAA`、`RRGGBB`、`RRGGBBAA`）或 `[r, g, b]` / `[r, g, b, a]` 列表。

RGB 最后四舍五入回 0-255，输出 alpha 等于基础色 alpha。

**具体实现**

按 Rizline 的覆盖色公式计算实际显示颜色。

设基础色为 1、覆盖色为 2，通道归一化到 0-1：

```text
R0' = R1' * (1 - A2') + R2' * A2'
G0' = G1' * (1 - A2') + G2' * A2'
B0' = B1' * (1 - A2') + B2' * A2'
A0 = A1
```

**返回值**

返回 `[r, g, b, a]`；输入非法时返回 `None`。

**示例**

```python
from rizChartFunction import mixColor

mixColor([255, 0, 0, 255], [0, 0, 255, 128])
# [127, 0, 128, 255]
```

### `splitColor()`

**函数声明**

```python
splitColor(mixcolor: str | list, basecolor: str | list | None = None,
           covercolor: str | list | None = None) -> list[int] | bool | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `mixcolor` | `str \| list` | 是 | - | 混合颜色 |
| `basecolor` | `str \| list \| None` | 否 | `None` | 基础色；`None` 表示推导基础色 |
| `covercolor` | `str \| list \| None` | 否 | `None` | 覆盖色；`None` 表示推导覆盖色 |

**用途**

拆分混合色、基础色和覆盖色。

**注意事项/细节**

- 只给 `basecolor`：推导覆盖色，返回 `[r, g, b, a]`。
- 只给 `covercolor`：推导基础色，返回 `[r, g, b, a]`。
- 两者都给：校验混合结果；匹配返回 `True`，不匹配返回 `False`。
- 两者都不给、输入非法或无法推导：返回 `None`。

覆盖色在数学上通常不唯一。

基础色在舍入边界附近也可能不唯一。

**返回值**

本函数 返回能复现 `mixcolor` 的规范解：覆盖色取 alpha 最小的解，基础色取最接近 实数反解的值。

推导基础色时，如果覆盖色 alpha 为 255，基础色 RGB 对结果 没有影响，此时返回 `mixcolor` 本身作为规范基础色。

若 `mixcolor` 的 RGB 与覆盖色不一致，则不存在可行基础色，返回 `None`。

**示例**

```python
from rizChartFunction import mixColor, splitColor

mix = mixColor([255, 0, 0, 255], [0, 0, 255, 128])  # [127, 0, 128, 255]
splitColor(mix, basecolor=[255, 0, 0, 255])          # [0, 0, 255, 128]
splitColor(mix, covercolor=[0, 0, 255, 128])         # [255, 0, 0, 255]
splitColor(mix, [255, 0, 0, 255], [0, 0, 255, 128])  # True
```

### `setNormalTheme()`

**函数声明**

```python
setNormalTheme(chart: dict, color1, color2, color3) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `color1` | `str \| list` | 是 | - | 第一个颜色 |
| `color2` | `str \| list` | 是 | - | 第二个颜色 |
| `color3` | `str \| list` | 是 | - | 第三个颜色 |

**用途**

设置第一个主题的三种颜色。

**输入限制**

颜色支持：

- HEX：`#RRGGBB`、`#RRGGBBAA`、`RRGGBB`、`RRGGBBAA`；
- 列表：`[r, g, b]` 或 `[r, g, b, a]`，通道必须是 0-255 的整数。

**返回值**

设置 `themes[0].colorsList` 的三种颜色，返回原主题的规格 Dict。

格式错误、超出范围或无法修改时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, rgb, setNormalTheme

chart = new(175.0)

old_theme = setNormalTheme(chart, "#1A1A2E", "1A1A2E", [255, 255, 255])
setNormalTheme(chart, rgb(26, 0.1, 46), "#FFFFFF", [0, 0, 0])
```

### `setRiztime()`

**函数声明**

```python
setRiztime(chart: dict, index: int = -1, color1=None, color2=None, color3=None,
           start: float | None = None, end: float | None = None,
           transtime: float | None = None, checkpoint: float | None = None) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | Riztime 索引；正序从 1 开始，0 视为 1，倒序从 -1 开始 |
| `color1` | `str \| list \| None` | 否 | `None` | 第一个颜色；`None` 表示不修改 |
| `color2` | `str \| list \| None` | 否 | `None` | 第二个颜色；`None` 表示不修改 |
| `color3` | `str \| list \| None` | 否 | `None` | 第三个颜色；`None` 表示不修改 |
| `start` | `float \| None` | 否 | `None` | Riztime 开始时间；`None` 表示不修改 |
| `end` | `float \| None` | 否 | `None` | Riztime 结束时间；`None` 表示不修改 |
| `transtime` | `float \| None` | 否 | `None` | 转换时间；`None` 表示不修改 |
| `checkpoint` | `float \| None` | 否 | `None` | 检查点；`None` 表示不修改 |

**用途**

设置一个 Riztime 的主题颜色与时间。

**具体实现**

修改 `start` 后会按 `start` 重新排序，`theme` 与 `challengeTime` 一起移动。

**注意事项/细节**

正序 `index` 修改 `themes[index]` 与 `challengeTimes[index - 1]`。

倒序 `index` 修改 `themes[index]` 与 `challengeTimes[index]`。

`start` 相同时放在已有 Riztime 后面。

**返回值**

索引不存在、 指向 Normal Theme（`themes[0]`）或无法修改时返回 `None`。

`end` 必须大于等于生效后的 `start`，`transtime` 必须大于等于 `0.0`，否则返回 `None` 且不修改。

成功时返回原 Riztime 的合并规格 Dict。

所有可选参数为 `None` 时直接 返回原规格且不做修改。

**示例**

```python
from rizChartFunction import new, setRiztime

chart = new(175.0)

# 修改第一个 Riztime 的第一个颜色和时间；其余颜色保持不变
old = setRiztime(
    chart,
    index=1,
    color1="#FF0000",
    start=30.0,
    end=45.0,
    transtime=0.5,
)

# 只检查并重新排序：把最后一个 Riztime 的 start 改到最前面
setRiztime(chart, index=-1, start=0.0, end=10.0)
```

### `addRiztime()`

**函数声明**

```python
addRiztime(chart: dict, color1, color2, color3,
           start: float = 0.0, end: float = 0.0,
           transtime: float = 0.5, checkpoint: float = 0.0) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `color1` | `str \| list` | 是 | - | 第一个颜色 |
| `color2` | `str \| list` | 是 | - | 第二个颜色 |
| `color3` | `str \| list` | 是 | - | 第三个颜色 |
| `start` | `float` | 否 | `0.0` | 开始时间 |
| `end` | `float` | 否 | `0.0` | 结束时间，必须大于等于 `start` |
| `transtime` | `float` | 否 | `0.5` | 转换时间，必须大于等于 `0.0` |
| `checkpoint` | `float` | 否 | `0.0` | 检查点 |

**用途**

按 `start` 升序插入一个 Riztime。

**具体实现**

按 `start` 升序插入，`start` 相同时放在已有 Riztime 后面。

**注意事项/细节**

后续的 `themes` 与 `challengeTimes` 同步后移。

如果当前**只有一个 Riztime**，且它的 `start` 与 `end` 相同，则视为 占位用的空 Riztime：先删除它及其配对主题，再插入新的 Riztime。

这样 `new()` 自带的默认空 Riztime 会被第一次添加的 Riztime 替换，而不是 保留成多余的一条。

**返回值**

成功返回插入后的 `challengeTimes` 索引（从 `0` 开始）；颜色、时间、结构或顺序不合法而无法插入时返回 `None`，且不修改谱面。注意 `setRiztime()` / `deleteRiztime()` 的 `index` 使用从 `1` 开始的 Riztime 索引。


**示例**

```python
from rizChartFunction import new, addRiztime

chart = new(175.0)

riztime_index = addRiztime(
    chart,
    "#00FF00",
    "#0000FF",
    "#FFFFFF",
    start=60.0,
    end=75.0,
    transtime=0.5,
    checkpoint=0.0,
)
if riztime_index is None:
    raise RuntimeError("添加 Riztime 失败")
```

### `deleteRiztime()`

**函数声明**

```python
deleteRiztime(chart: dict, index: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 删除索引，规则同 `setRiztime()` |

**用途**

删除指定 Riztime。

**返回值**

成功时返回被删除 Riztime 的合并规格 Dict。

索引不存在、指向 Normal Theme 或无法删除时返回 `None`。

**示例**

```python
from rizChartFunction import deleteRiztime, new

chart = new(175.0)

removed = deleteRiztime(chart, index=1)
if removed is None:
    raise RuntimeError("删除 Riztime 失败")

print(removed["colorsList"])
```

## 画布

### `addCanvas()`

**函数声明**

```python
addCanvas(chart: dict, index: int | None = None) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int \| None` | 否 | `None` | 插入位置；0 表示最前，负值从末尾计算，`None` 表示末尾 |

**用途**

插入一个画布。

**输入限制**

越界返回 `None`。

**具体实现**

新画布使用与 `new()` 中第 0 个画布相同的初始化结构，并设置对应的 `index`。

**注意事项/细节**

`index` 是列表插入位置：`0` 插到最前，正整数 `i` 插到当前第 `i` 个画布 之前，`-1` 插到最后一个画布之前，`None` 追加到末尾。

插入位置及其后的画布 `index` 顺延，同时更新 `lines[].linePoints[].canvasIndex` 和 `lines[].notes[].otherInformations[1]` 的绑定值。

**返回值**

成功返回新画布的 `index`。

结构非法、画布索引不连续或越界时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addCanvas

chart = new(175.0)

new_index = addCanvas(chart, index=0)
if new_index is None:
    raise RuntimeError("添加画布失败")

print(new_index)  # 0
print([canvas["index"] for canvas in chart["canvasMoves"]])  # [0, 1]
```

### `deleteCanvas()`

**函数声明**

```python
deleteCanvas(chart: dict, index: int = -1, isRelative: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 画布索引或空画布索引，0 起，负数从末尾计算 |
| `isRelative` | `bool` | 否 | `False` | 是否在所有空画布中按相对位置选择 |

**用途**

删除一个空画布。

**注意事项/细节**

`isRelative=False` 时，`index` 是画布索引。

只有没有任何 `linePoints[].canvasIndex` 或 `notes[].otherInformations[1]` 指向该画布 时才能删除。

`isRelative=True` 时，`index` 是所有空画布中的相对位置，例如 `0` 表示 第一个空画布，`-1` 表示最后一个空画布。

如果删除的不是最后一个画布，后面的画布 `index` 会向前顺延，同时更新 绑定的 `canvasIndex` 与 `otherInformations[1]`。

**返回值**

成功返回被删除画布的规格 Dict。

索引不存在、画布非空、结构非法或无法删除 时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addCanvas, deleteCanvas

chart = new(175.0)

# 先追加一个空画布，再按绝对索引删除
new_index = addCanvas(chart)
if new_index is None:
    raise RuntimeError("添加画布失败")

deleted = deleteCanvas(chart, new_index)
if deleted is None:
    raise RuntimeError("删除画布失败")
```

## 画布位置

### `addCanvasPosition()`

**函数声明**

```python
addCanvasPosition(chart: dict, index: int, time: float,
                  position: float = 0.0, easetype: int = 0,
                  isRealTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `position` | `float` | 否 | `0.0` | 节点 x 坐标，写入节点的 `value` |
| `easetype` | `int` | 否 | `0` | 缓动类型；大于 18 视为 18，小于 0 视为 0 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

为指定画布的 `xPositionKeyPoints` 添加一个节点。

**输入限制**

`isRealTime=True` 时按 BPM 时间轴换算，谱面必须有 `time=0.0` 的 BPM 节点。

**注意事项/细节**

为 `canvasMoves[index].xPositionKeyPoints` 添加节点，保证 `time` 非递减。

若与已有节点 `time` 相同，新节点放在已有节点**之后**。

新节点的 `floorPosition` 固定为 `0.0`。

**返回值**

成功返回插入后的关键点索引；画布或节点结构非法、时间/坐标无效时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import new, addCanvasPosition

chart = new(100.0)

# 第 4 tick 把画布 0 移动到 x = 0.5，使用缓动类型 5
addCanvasPosition(chart, 0, 4.0, 0.5, 5)

# 实际 2.4 秒（100 BPM 下等于 tick 4）
addCanvasPosition(chart, -1, 2.4, 0.5, isRealTime=True)
```

### `setCanvasPosition()`

**函数声明**

```python
setCanvasPosition(chart: dict, canvasindex: int,
                  positionindex: int = -1, time: float | None = None,
                  position: float | None = None,
                  easetype: int | None = None,
                  isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `positionindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间，必须大于等于 `0.0`；`None` 表示不修改 |
| `position` | `float \| None` | 否 | `None` | 新 x 坐标；`None` 表示不修改 |
| `easetype` | `int \| None` | 否 | `None` | 新缓动类型；大于 18 视为 18，小于 0 视为 0；`None` 表示不修改 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改画布 `xPositionKeyPoints` 中的一个节点。

**输入限制**

指向第 0 个节点时不能修改 `time`（允许传入 `0.0`）。

**具体实现**

修改后按 `time` 重新排序。

**注意事项/细节**

若与已有节点时间相同，节点排在已有节点 之后。

**返回值**

所有修改参数均为 `None` 时直接返回原节点的规格 Dict，不修改谱面。

成功返回修改前的原节点的规格 Dict。

索引不存在、参数非法或无法重排时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addCanvasPosition, setCanvasPosition

chart = new(100.0)
addCanvasPosition(chart, 0, 4.0, 0.5, 5)

old = setCanvasPosition(chart, 0, 1, position=0.8, easetype=2)
print(old)  # 修改前的节点

# 修改时间后自动重排
setCanvasPosition(chart, 0, 1, time=2.0)
```

### `deleteCanvasPosition()`

**函数声明**

```python
deleteCanvasPosition(chart: dict, canvasindex: int,
                     positionindex: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `positionindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |

**用途**

删除画布的 `xPositionKeyPoints` 节点。

**注意事项/细节**

删除对应节点。

指向第 0 个节点时不删除，而是重置为 `new()` 中的初始 节点：`time=0.0, value=0.0, easeType=0, floorPosition=0.0`。

**返回值**

成功返回被删除或被重置前的原节点的规格 Dict。

索引不存在或结构非法时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addCanvasPosition, deleteCanvasPosition

chart = new(100.0)
addCanvasPosition(chart, 0, 4.0, 0.5, 5)

old = deleteCanvasPosition(chart, 0, -1)
if old is None:
    raise RuntimeError("删除画布节点失败")

# 指向第 0 个节点时只重置，不删除
old_first = deleteCanvasPosition(chart, 0, 0)
```

## 画布流速

### `addCanvasSpeed()`

**函数声明**

```python
addCanvasSpeed(chart: dict, index: int, time: float,
               speed: float = 1.0,
               isDelayCalculate: bool = False,
               isChangeZeroSpeed: bool = True,
               isRealTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `speed` | `float` | 否 | `1.0` | 画布流速 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isChangeZeroSpeed` | `bool` | 否 | `True` | 是否调整接近 0 的流速 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

为指定画布的 `speedKeyPoints` 添加一个流速节点。

**输入限制**

参数、结构或画布索引非法时返回 `None`，且不修改谱面。

**具体实现**

默认添加后重新计算整份谱面的相关 `floorPosition`；`isDelayCalculate=True`
时跳过全谱重算，新节点的 `floorPosition` 写为 `NaN`。

**注意事项/细节**

`isChangeZeroSpeed=True` 时：

- `speed` 在 `[0.0, 0.0001]` 内 → 写入 `0.0001`
- `speed` 在 `[-0.0001, 0.0)` 内 → 写入 `-0.0001`
- 其他值保持不变

为 `canvasMoves[index].speedKeyPoints` 添加节点，保证 `time` 非递减。

若与已有节点 `time` 相同，新节点放在已有节点**之后**。

新节点 `easeType=0`；默认 `floorPosition` 由重算得到，
`isDelayCalculate=True` 时为 `NaN`。

**返回值**

成功返回插入后的关键点索引；参数、结构或画布索引非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import new, addCanvasSpeed

chart = new(100.0)

# 第 4 tick 起流速变为 2
addCanvasSpeed(chart, 0, 4.0, 2.0)

# 实际 2.4 秒（100 BPM 下等于 tick 4）
addCanvasSpeed(chart, -1, 2.4, 2.0, isRealTime=True)

# 传 0 会写成 0.0001
addCanvasSpeed(chart, 0, 8.0, 0.0)
```

### `setCanvasSpeed()`

**函数声明**

```python
setCanvasSpeed(chart: dict, canvasindex: int,
               speedindex: int = -1, time: float | None = None,
               speed: float | None = None,
               isDelayCalculate: bool = False,
               isChangeZeroSpeed: bool = True,
               isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `speedindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间，必须大于等于 `0.0`；`None` 表示不修改 |
| `speed` | `float \| None` | 否 | `None` | 新流速；`None` 表示不修改 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isChangeZeroSpeed` | `bool` | 否 | `True` | 是否调整接近 0 的流速 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改画布 `speedKeyPoints` 中的一个节点。

**输入限制**

指向第 0 个节点时不能修改 `time`（允许传入 `0.0`）。

**具体实现**

修改后按 `time` 重新排序。默认重新计算整份谱面的相关
`floorPosition`；`isDelayCalculate=True` 时跳过全谱重算，修改后节点的
`floorPosition` 写为 `NaN`。

**注意事项/细节**

若与已有节点时间相同，节点排在已有节点 之后。

`isChangeZeroSpeed` 的规则与 `addCanvasSpeed()` 相同。

**返回值**

所有修改参数均为 `None` 时直接返回原节点的规格 Dict，不修改谱面。

成功返回修改前的原节点 规格 Dict。

索引不存在、参数非法或无法重排时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addCanvasSpeed, setCanvasSpeed

chart = new(100.0)
addCanvasSpeed(chart, 0, 4.0, 2.0)

old = setCanvasSpeed(chart, 0, 1, speed=1.5)
print(old)  # 修改前的节点

# 修改时间后自动重排
setCanvasSpeed(chart, 0, 1, time=2.0)
```

### `deleteCanvasSpeed()`

**函数声明**

```python
deleteCanvasSpeed(chart: dict, canvasindex: int,
                  speedindex: int = -1,
                  isDelayCalculate: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `speedindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |

**用途**

删除画布的 `speedKeyPoints` 节点。

**具体实现**

默认删除后重新计算整份谱面的相关 `floorPosition`；
`isDelayCalculate=True` 时跳过全谱重算。

**注意事项/细节**

删除对应节点。

指向第 0 个节点时不删除，而是重置为 `new()` 中的初始节点：
`time=0.0, value=1.0, easeType=0`。默认 `floorPosition=0.0`；
`isDelayCalculate=True` 时为 `NaN`。

**返回值**

成功返回被删除或被重置前的原节点的规格 Dict。

索引不存在或结构非法时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addCanvasSpeed, deleteCanvasSpeed

chart = new(100.0)
addCanvasSpeed(chart, 0, 4.0, 2.0)

old = deleteCanvasSpeed(chart, 0, -1)
if old is None:
    raise RuntimeError("删除流速节点失败")

# 指向第 0 个节点时只重置，不删除
old_first = deleteCanvasSpeed(chart, 0, 0)
```

## 摄像机

### `addCameraPosition()`

**函数声明**

```python
addCameraPosition(chart: dict, time: float, position: float = 0.0,
                  easetype: int = 0, isRealTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `position` | `float` | 否 | `0.0` | 节点 x 坐标，写入节点的 `value` |
| `easetype` | `int` | 否 | `0` | 缓动类型，夹取到 0-18 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数（需要 `time=0.0` 的 BPM 节点） |

**用途**

为 `cameraMove.xPositionKeyPoints` 添加节点。

**输入限制**

参数或结构非法时返回 `None`，且不修改谱面。

**注意事项/细节**

为 `cameraMove.xPositionKeyPoints` 添加节点，保证 `time` 非递减。

若与已有节点 `time` 相同，新节点放在已有节点之后。

新节点 `floorPosition` 固定为 `0.0`。

**返回值**

成功返回插入后的关键点索引；参数或结构非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import new, addCameraPosition

chart = new(100.0)
addCameraPosition(chart, 4.0, 0.5, 3)
```

### `setCameraPosition()`

**函数声明**

```python
setCameraPosition(chart: dict, index: int = -1,
                  time: float | None = None,
                  position: float | None = None,
                  easetype: int | None = None,
                  isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间，必须大于等于 `0.0`；`None` 表示不修改 |
| `position` | `float \| None` | 否 | `None` | 新 x 坐标；`None` 表示不修改 |
| `easetype` | `int \| None` | 否 | `None` | 新缓动类型，夹取到 0-18；`None` 表示不修改 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改 `cameraMove.xPositionKeyPoints` 节点。

**输入限制**

指向第 0 个节点时不能修改 `time`（允许传入 `0.0`）。

**具体实现**

修改后按 `time` 重新排序。

**注意事项/细节**

若与已有节点时间相同，节点排在已有节点 之后。

**返回值**

所有修改参数均为 `None` 时直接返回原节点的规格 Dict，不修改谱面。

成功返回 修改前的原节点的规格 Dict。

索引不存在或参数非法时返回 `None`，且不修改 谱面。

**示例**

```python
from rizChartFunction import new, addCameraPosition, setCameraPosition

chart = new(100.0)
addCameraPosition(chart, 4.0, 0.5, 3)

old = setCameraPosition(chart, 1, position=0.8, easetype=5)
print(old)  # 修改前的节点
```

### `deleteCameraPosition()`

**函数声明**

```python
deleteCameraPosition(chart: dict, index: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |

**用途**

删除 `cameraMove.xPositionKeyPoints` 节点。

**注意事项/细节**

删除对应节点。

指向第 0 个节点时不删除，而是重置为 `new()` 中的初始 节点：`time=0.0, value=0.0, easeType=0, floorPosition=0.0`。

**返回值**

成功返回被删除或被重置前的原节点的规格 Dict。

索引不存在或结构非法时返回 `None`，且不修改谱面。

### `addCameraScale()`

**函数声明**

```python
addCameraScale(chart: dict, time: float, scale: float = 1.0,
               easetype: int = 0, isRealTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `scale` | `float` | 否 | `1.0` | 缩放比例，必须大于 `0.0`，但不限制在 0.1-10.0 内 |
| `easetype` | `int` | 否 | `0` | 缓动类型，夹取到 0-18 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数（需要 `time=0.0` 的 BPM 节点） |

**用途**

为 `cameraMove.scaleKeyPoints` 添加节点。

**注意事项/细节**

为 `cameraMove.scaleKeyPoints` 添加节点，保证 `time` 非递减。

时间 相同时放在已有节点之后。

新节点 `floorPosition` 固定为 `0.0`。

**返回值**

成功返回插入后的关键点索引；`scale <= 0.0`、参数或结构非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import new, addCameraScale

chart = new(100.0)
addCameraScale(chart, 4.0, 2.0, 5)

# 0.1-10.0 之外也允许
addCameraScale(chart, 8.0, 20.0)
```

### `setCameraScale()`

**函数声明**

```python
setCameraScale(chart: dict, index: int = -1,
               time: float | None = None,
               scale: float | None = None,
               easetype: int | None = None,
               isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间，必须大于等于 `0.0`；`None` 表示不修改 |
| `scale` | `float \| None` | 否 | `None` | 新缩放比例，必须大于 `0.0`；`None` 表示不修改 |
| `easetype` | `int \| None` | 否 | `None` | 新缓动类型，夹取到 0-18；`None` 表示不修改 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改 `cameraMove.scaleKeyPoints` 节点。

**输入限制**

指向第 0 个节点时不能修改 `time`（允许传入 `0.0`）。

**具体实现**

修改后按 `time` 重新排序。

**注意事项/细节**

若与已有节点时间相同，节点排在已有节点 之后。

**返回值**

成功返回修改前的原节点的规格 Dict。

索引不存在、`scale <= 0.0` 或参数非法 时返回 `None`，且不修改谱面。

### `deleteCameraScale()`

**函数声明**

```python
deleteCameraScale(chart: dict, index: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |

**用途**

删除 `cameraMove.scaleKeyPoints` 节点。

**注意事项/细节**

删除对应节点。

指向第 0 个节点时不删除，而是重置为 `new()` 中的初始 节点：`time=0.0, value=1.0, easeType=0, floorPosition=0.0`。

**返回值**

成功返回被删除或被重置前的原节点的规格 Dict。

索引不存在或结构非法时返回 `None`，且不修改谱面。

## 引导线

### `addLine()`

**函数声明**

```python
addLine(chart: dict, linepointslist: list,
        ringpointslist: list | dict,
        index: int | None = None,
        isDelayCalculate: bool = False,
        *, notes: list | None = None,
        linecolors: list | None = None) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `linepointslist` | `list` | 是 | - | 线节点列表，长度必须大于等于 2 |
| `ringpointslist` | `list \| dict` | 是 | - | 判定环颜色节点；`dict` 表示一个，`list` 表示多个，至少一个 |
| `index` | `int \| None` | 否 | `None` | 插入位置；`None` 表示追加到末尾，负数从末尾计算 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `notes` | `list \| None` | 否 | `None` | Note 列表；省略或空列表表示不加 Note |
| `linecolors` | `list \| None` | 否 | `None` | `lineColor` 节点列表；省略或空列表表示不加线色 |

**用途**

在 `lines` 的指定位置插入一条引导线，并计算新线的派生字段。

**输入限制**

- `linepointslist` 至少 2 个节点；`ringpointslist` 至少 1 个节点。
- `notes` / `linecolors` 可以为空；两者都是 keyword-only 参数。
- `index=0` 插到最前，`-1` 插到最后一个之前，`None` 追加到末尾。
- 默认要求谱面在 `time=0.0` 处有 BPM 节点；`isDelayCalculate=True` 时
  跳过高度计算，新节点的 `floorPosition` 为 `NaN`。
- 线节点、判定环、Note、线色都可以用完整节点或规格 Dict，但不能混用错误结构。
- 任一节点非法、索引非法或谱面结构不足时，整条线不插入。

**具体实现**

1. 把完整的线节点、判定环、Note、线色转换为统一规格，并把 `isRealTime` 时间换算为 tick。
2. 四类节点分别按 `time` 稳定排序；相同时间保持输入顺序。
3. 默认根据 BPM 时间轴、`canvasIndex` 对应画布计算线节点 `floorPosition`；
   `isDelayCalculate=True` 时写为 `NaN`。
4. 默认根据线节点计算 Note 头部 `floorPosition`，Hold 尾部另外计算画布和高度；
   `isDelayCalculate=True` 时头部和尾部高度写为 `NaN`。
5. 写入新线的 `linePoints`、`notes`、`judgeRingColor`、`lineColor`，不修改已有线。

**注意事项/细节**

完整节点与规格 Dict 的区别只是输入形状：

| 类型 | 完整节点 | 规格 Dict |
| --- | --- | --- |
| 线节点 | `{time, xPosition, color, easeType, canvasIndex, floorPosition}` | `{time, xPosition, canvasIndex, easeType, color, isRealTime?}` |
| 判定环 | `{startColor, endColor, time}` | `{time, startColor, endColor?, isRealTime?}` |
| Note | `{type, time, floorPosition, otherInformations}` | `{time, type, endtime?, isRealTime?, isRealEndTime?}` |
| 线色 | `{startColor, endColor, time}` | `{time, startColor, endColor?, isRealTime?}` |

- 完整节点中的 `floorPosition` / `otherInformations` 派生值不会被直接使用；默认会按当前谱面重新计算线节点、Note 头部和 Hold 尾部高度，`isDelayCalculate=True` 时新节点高度为 `NaN`。
- 完整 Note 的 Hold 尾部时间取自 `otherInformations[0]`；默认重新计算 Hold 尾部画布和高度，`isDelayCalculate=True` 时高度为 `NaN`。
- Tap / Drag 的 `otherInformations` 三元素占位会保留；缺少时补成空列表。
- 完整 Note 的头部必须在新的线节点范围内；Hold 尾部必须大于头部且不超过线尾节点时间。
- `easeType` 会夹取到 0-18。
- 颜色 Dict 必须包含 `r`、`g`、`b`、`a` 四个通道；颜色也可以用 HEX、`[r,g,b]`、`[r,g,b,a]` 输入。
- `createLinePoint()` / `createNote()` / `createRingPoint()` / `createLineColor()` 返回的是规格 Dict；整条线复制时也可以直接传谱面里的完整节点。

**返回值**

成功返回新线的索引；失败返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import (
    new, addCanvas, addLine,
    createLinePoint, createRingPoint, createNote, createLineColor,
)

chart = new(100.0)
addCanvas(chart)

# 全部使用规格 Dict
addLine(
    chart,
    linepointslist=[
        {
            "time": 0.0,
            "xPosition": 0.0,
            "canvasIndex": 0,
            "easeType": 0,
            "color": "#FFFFFF",
        },
        {
            "time": 4.0,
            "xPosition": 1.0,
            "canvasIndex": 1,
            "easeType": 5,
            "color": "#FF0000",
        },
    ],
    ringpointslist=[
        {"time": 0.0, "startColor": "#FFFFFF", "endColor": "#FF0000"},
    ],
    notes=[
        {"time": 1.0, "type": "tap"},
        {"time": 2.0, "type": "hold", "endtime": 3.0},
    ],
    linecolors=[
        {"time": 0.0, "startColor": "#FFFFFF", "endColor": "#FF0000"},
    ],
)

# 使用 create 函数构造规格节点
p0 = createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
p4 = createLinePoint(4.0, 1.0, 0, 0, "#FFFFFF")
ring = createRingPoint(0.0, "#FFFFFF")
note = createNote(1.0, "tap")
color = createLineColor(0.0, "#FFFFFF")
addLine(chart, [p0, p4], ring, notes=[note], linecolors=[color])
```

```python
# 复制整条线；派生字段会重新计算
src = chart["lines"][0]

addLine(
    chart,
    src["linePoints"],
    src["judgeRingColor"],
    notes=src["notes"],
    linecolors=src["lineColor"],
)
```

### `deleteLine()`

**函数声明**

```python
deleteLine(chart: dict, index: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |

**用途**

删除指定索引的引导线。

**返回值**

成功返回被删除引导线的规格 Dict；谱面、`lines` 或索引非法时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import deleteLine

removed = deleteLine(chart, index=-1)
if removed is None:
    raise RuntimeError("删除引导线失败")
```

## 线节点

### `createLinePoint()`

**函数声明**

```python
createLinePoint(time: float, xPosition: float,
                index: int, easetype: int,
                color: str | list,
                isRealTime: bool = False,
                chart: dict | None = None) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `time` | `float` | 是 | - | 节点时间；默认是 tick，`isRealTime=True` 时为实际秒数 |
| `xPosition` | `float` | 是 | - | 节点 x 坐标 |
| `index` | `int` | 是 | - | 节点所在画布索引，支持负数（插入时解析） |
| `easetype` | `int` | 是 | - | 缓动类型，夹取到 0-18 |
| `color` | `str \| list` | 是 | - | 节点颜色，支持 HEX / RGB / RGBA |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `chart` | `dict \| None` | 否 | `None` | 参照谱面；仅 `isRealTime=True` 时使用 |

**用途**

创建一个线节点规格 Dict，不修改谱面，也不计算 `floorPosition`。

**输入限制**

`isRealTime=True` 时必须提供有效 `chart`，用于把实际秒数换算为 tick。

**具体实现**

整线插入时由 [`addLine()`](#addline) 计算。

单节点追加使用 [`addLinePoint()`](#addlinepoint)，由后者根据参数计算。

画布是否存在、BPM / 流速结构是否足以计算 `floorPosition`，由插入函数 检查。

**注意事项/细节**

不包含 `floorPosition`。

因此 tick 规格本身不需要谱面有 `time=0.0` 的 BPM 节点。

本函数只校验参数和规格结构。需要直接向已有引导线追加节点时，使用
[`addLinePoint()`](#addlinepoint)，不要手动修改 `lines` 结构。

**返回值**

不修改谱面，直接返回一个**线节点规格 Dict**：

```python
{
    "time": float,            # tick
    "xPosition": float,
    "color": [r, g, b, a],
    "easeType": int,
    "canvasIndex": int,
}
```

参数或谱面非法时返回 `None`。

**示例**

```python
from rizChartFunction import (
    new, createLinePoint, createRingPoint, addLine,
)

chart = new(100.0)

start = createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
end = createLinePoint(4.0, 0.5, 0, 5, "#FF0000")
ring = createRingPoint(0.0, "#FFFFFF")

if start is None or end is None or ring is None:
    raise RuntimeError("创建线节点规格失败")

# floorPosition 在 addLine() 中计算
if addLine(chart, [start, end], ring) is None:
    raise RuntimeError("添加引导线失败")

# isRealTime=True：100 BPM 下 2.4 秒等于 tick 4.0
point = createLinePoint(
    2.4, 0.5, 0, 5, "#FF0000",
    isRealTime=True, chart=chart,
)
```

### `addLinePoint()`

**函数声明**

```python
addLinePoint(chart: dict, time: float, xPosition: float,
             canvasindex: int, easetype: int, color: str | list,
             lineindex: int = -1,
             isDelayCalculate: bool = False,
             isRealTime: bool = False,
             isAbsolutePosition: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `xPosition` | `float` | 是 | - | 节点 x 坐标 |
| `canvasindex` | `int` | 是 | - | 节点所在画布索引 |
| `easetype` | `int` | 是 | - | 缓动类型，夹取到 0-18 |
| `color` | `str \| list` | 是 | - | 节点颜色 |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isAbsolutePosition` | `bool` | 否 | `False` | `True` 时 `xPosition` 是绝对 x 坐标 |

**用途**

向指定引导线添加一个节点。

**输入限制**

参数、线结构或索引非法时 返回 `None`，且不修改谱面。

**具体实现**

按 `time` 插入节点。默认重算整份谱面的相关 `floorPosition`；
`isDelayCalculate=True` 时跳过全谱重算，新节点的 `floorPosition` 写为
`NaN`，需要随后调用 `refresh()`。

**注意事项/细节**

时间相同时放在已有节点之后。

`isAbsolutePosition=True` 时，`xPosition` 按绝对屏幕 x 处理，会减去 目标时刻节点所在画布的 `getCanvasPositionAt()`，再把相对坐标写入节点。

**返回值**

成功返回插入后的线节点索引；画布 x 无法计算、参数或结构非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import addLinePoint

# 相对坐标
addLinePoint(chart, 8.0, 2.0, 0, 3, "#FF0000", lineindex=0)

# 绝对坐标：画布在目标时刻的 x 为 10 时，节点会存为相对 x 2.0
addLinePoint(
    chart, 8.0, 12.0, 1, 3, "#FF0000",
    lineindex=0, isAbsolutePosition=True,
)
```

### `setLinePoint()`

**函数声明**

```python
setLinePoint(chart: dict, lineindex: int = -1,
             pointindex: int = -1, time: float | None = None,
             xPosition: float | None = None,
             canvasindex: int | None = None,
             easetype: int | None = None,
             color: str | list | None = None,
             isDelayCalculate: bool = False,
             isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `pointindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间，必须大于等于 `0.0`；`None` 表示不修改 |
| `xPosition` | `float \| None` | 否 | `None` | 新 x 坐标；`None` 表示不修改 |
| `canvasindex` | `int \| None` | 否 | `None` | 新画布索引；`None` 表示不修改 |
| `easetype` | `int \| None` | 否 | `None` | 新缓动类型，夹取到 0-18；`None` 表示不修改 |
| `color` | `str \| list \| None` | 否 | `None` | 新颜色；`None` 表示不修改 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改引导线中的一个节点。

**具体实现**

修改后按 `time` 重新排序。默认重算整份谱面的相关 `floorPosition`；
`isDelayCalculate=True` 时跳过全谱重算，修改后节点的 `floorPosition`
写为 `NaN`，需要随后调用 `refresh()`。

**注意事项/细节**

时间相同时放在已有节点之后。

**返回值**

所有修改参数均为 `None` 时直接返回原节点规格 Dict。

成功返回修改前的原节点的规格 Dict。

索引不存在、参数非法或无法重排时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import setLinePoint

old = setLinePoint(chart, lineindex=0, pointindex=1,
                   xPosition=0.5, easetype=2)
print(old)  # 修改前的节点
```

### `deleteLinePoint()`

**函数声明**

```python
deleteLinePoint(chart: dict, lineindex: int = -1,
                pointindex: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `pointindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |

**用途**

删除引导线中的一个节点。

**返回值**

删除指定节点并返回原节点的规格 Dict。

**当该线只有两个或更少节点时不能删除**， 返回 `None`。

索引不存在或结构非法时同样返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import deleteLinePoint

removed = deleteLinePoint(chart, lineindex=0, pointindex=-1)
if removed is None:
    raise RuntimeError("删除线节点失败")
```

## 判定环

### `createRingPoint()`

**函数声明**

```python
createRingPoint(time: float, startcolor: str | list,
                endcolor: str | list | None = None,
                isRealTime: bool = False,
                chart: dict | None = None) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `startcolor` | `str \| list` | 是 | - | 起始颜色 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 结束颜色；`None` 表示与起始颜色相同 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `chart` | `dict \| None` | 否 | `None` | 参照谱面；**仅 `isRealTime=True` 时使用** |

**用途**

创建一个判定环颜色节点，不修改谱面。

**注意事项/细节**

生成一个判定环颜色节点，不修改谱面：

```python
{
    "startColor": [r, g, b, a],
    "endColor": [r, g, b, a],
    "time": float,
}
```

- `endcolor=None` 时复制 `startcolor`，两者是独立对象
- 颜色支持 `#RRGGBB`、`#RRGGBBAA`、`RRGGBB`、`RRGGBBAA`、
  `[r,g,b]`、`[r,g,b,a]`
- `isRealTime=True` 必须提供有效的 `chart`，并把秒数换算为 tick；
  谱面缺少 `time=0.0` 的 BPM 节点时返回 `None`
- `isRealTime=False` 时 `chart` 会被忽略，可直接传 `None`

**返回值**

成功返回判定环规格 Dict；参数或谱面非法时返回 `None`。

**示例**

```python
from rizChartFunction import new, createRingPoint

ring = createRingPoint(4.0, "#FFFFFF", "#FF0000")
if ring is None:
    raise RuntimeError("创建判定环颜色节点失败")

chart = new(100.0)

# 实际 2.4 秒（100 BPM 下等于 tick 4）
ring = createRingPoint(2.4, "#FFFFFF", isRealTime=True, chart=chart)
```

### `addRingPoint()`

**函数声明**

```python
addRingPoint(chart: dict, index: int, time: float,
             startcolor: str | list,
             endcolor: str | list | None = None,
             isRealTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `startcolor` | `str \| list` | 是 | - | 起始颜色 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 结束颜色；`None` 表示与 `startcolor` 相同 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

向指定引导线添加判定环颜色节点。

**具体实现**

判定环颜色不参与 `floorPosition` 计算。

**注意事项/细节**

向指定引导线的 `judgeRingColor` 按时间顺序插入节点。

时间相同时放在 已有节点之后。

**返回值**

成功返回插入后的判定环索引；线索引、时间、颜色或结构非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import addRingPoint

addRingPoint(chart, 0, 4.0, "#FF0000", "#00FF00")
```

### `setRingPoint()`

**函数声明**

```python
setRingPoint(chart: dict, lineindex: int = -1,
             ringindex: int = -1, time: float | None = None,
             startcolor: str | list | None = None,
             endcolor: str | list | None = None,
             isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `ringindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间，必须大于等于 `0.0`；`None` 表示不修改 |
| `startcolor` | `str \| list \| None` | 否 | `None` | 新起始颜色；`None` 表示不修改 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 新结束颜色；`None` 表示**不修改** |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改判定环颜色节点。

**具体实现**

修改后按 `time` 重新排序。

**注意事项/细节**

时间相同时放在已有节点之后。

注意：这里的 `endcolor=None` 表示**不修改**，与 `addRingPoint()` / `createRingPoint()` 中“与起始颜色相同”的语义不同。

**返回值**

所有修改参数 均为 `None` 时直接返回原节点规格 Dict。

成功返回修改前的原节点的规格 Dict。

索引不存在、参数非法或无法重排时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import setRingPoint

old = setRingPoint(chart, 0, 1, time=2.0, startcolor="#0000FF")
if old is None:
    raise RuntimeError("修改判定环颜色节点失败")
```

### `deleteRingPoint()`

**函数声明**

```python
deleteRingPoint(chart: dict, lineindex: int = -1,
                ringindex: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `ringindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |

**用途**

删除判定环颜色节点。

**返回值**

删除指定判定环颜色节点并返回原节点的规格 Dict。

**该线只剩一个判定环节点时不能删除**，返回 `None`。

索引不存在或结构 非法时同样返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import deleteRingPoint

removed = deleteRingPoint(chart, lineindex=0, ringindex=-1)
if removed is None:
    raise RuntimeError("删除判定环颜色节点失败")
```

## 线色覆盖

### `createLineColor()`

**函数声明**

```python
createLineColor(time: float, startcolor: str | list,
                endcolor: str | list | None = None,
                isRealTime: bool = False,
                chart: dict | None = None) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `time` | `float` | 是 | - | 节点时间，必须大于等于 `0.0` |
| `startcolor` | `str \| list` | 是 | - | 起始颜色，支持 HEX / RGB / RGBA |
| `endcolor` | `str \| list \| None` | 否 | `None` | 结束颜色；`None` 表示与 `startcolor` 相同 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `chart` | `dict \| None` | 否 | `None` | 参照谱面；仅 `isRealTime=True` 时使用 |

**用途**

创建一个线色覆盖节点，不修改谱面。

**输入限制**

`isRealTime=True` 时必须提供有效 `chart`，用于把实际秒数换算为 tick。

**注意事项/细节**

节点结构与判定环颜色节点相同。

否则 `chart` 可以不传。

**返回值**

不修改谱面，直接返回一个线色覆盖节点：

```python
{
    "startColor": [r, g, b, a],
    "endColor": [r, g, b, a],
    "time": float,
}
```

时间、 颜色或谱面非法时返回 `None`。

**示例**

```python
from rizChartFunction import createLineColor

color = createLineColor(4.0, "#FF0000", "#00FF00")
if color is None:
    raise RuntimeError("创建线色覆盖节点失败")

# 2.4 秒 @ 100 BPM = tick 4.0
color = createLineColor(
    2.4, "#FFFFFF", isRealTime=True, chart=chart,
)
```

### `addLineColor()`

**函数声明**

```python
addLineColor(chart: dict, index: int, time: float,
             startcolor: str | list,
             endcolor: str | list | None = None,
             isRealTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 节点时间 |
| `startcolor` | `str \| list` | 是 | - | 起始颜色 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 结束颜色；`None` 表示与 `startcolor` 相同 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

向指定引导线添加线色覆盖节点。

**具体实现**

线色覆盖不参与 `floorPosition` 计算。

`lineColor` 可以为空， 添加时会自动补上第一个节点。

**注意事项/细节**

向指定引导线的 `lineColor` 按时间顺序插入节点。

时间相同时放在已有 节点之后。

**返回值**

成功返回插入后的线色索引；线索引、时间、颜色或结构非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import addLineColor

addLineColor(chart, 0, 4.0, "#FF0000", "#00FF00")
```

### `setLineColor()`

**函数声明**

```python
setLineColor(chart: dict, lineindex: int = -1,
             colorindex: int = -1, time: float | None = None,
             startcolor: str | list | None = None,
             endcolor: str | list | None = None,
             isRealTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `colorindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新时间；`None` 表示不修改 |
| `startcolor` | `str \| list \| None` | 否 | `None` | 新起始颜色；`None` 表示不修改 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 新结束颜色；`None` 表示**不修改** |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |

**用途**

修改线色覆盖节点。

**具体实现**

修改后按 `time` 重新排序。

**注意事项/细节**

时间相同时放在已有节点之后。

注意：这里的 `endcolor=None` 表示**不修改**，与 `addLineColor()` 中 “与起始颜色相同”的语义不同。

**返回值**

所有修改参数 均为 `None` 时直接返回原节点规格 Dict。

成功返回修改前的原节点的规格 Dict。

索引不存在、参数非法或无法重排时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import setLineColor

old = setLineColor(chart, 0, 1, time=2.0, startcolor="#0000FF")
if old is None:
    raise RuntimeError("修改线色覆盖节点失败")
```

### `deleteLineColor()`

**函数声明**

```python
deleteLineColor(chart: dict, lineindex: int = -1,
                colorindex: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `colorindex` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |

**用途**

删除线色覆盖节点。

**注意事项/细节**

允许删除最后一个节点，使 `lineColor` 变为空列表。

**返回值**

删除指定线色覆盖节点并返回原节点的规格 Dict。

`lineColor` 为空、索引不存在或结构非法时返回 `None`。

**示例**

```python
from rizChartFunction import deleteLineColor

removed = deleteLineColor(chart, lineindex=0, colorindex=-1)
if removed is None:
    raise RuntimeError("删除线色覆盖节点失败")
```

## 音符

### `createNote()`

**函数声明**

```python
createNote(time: float, type: int | str,
           endtime: float = 0.0,
           isRealTime: bool = False,
           isRealEndTime: bool = False,
           chart: dict | None = None) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `time` | `float` | 是 | - | Note 头部时间；默认是 tick，`isRealTime=True` 时为实际秒数 |
| `type` | `int \| str` | 是 | - | `0`/`"tap"`、`1`/`"drag"`、`2`/`"hold"`，不区分大小写 |
| `endtime` | `float` | 否 | `0.0` | 仅 Hold 有效；必须大于 `time` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `True` 时 `endtime` 是实际秒数 |
| `chart` | `dict \| None` | 否 | `None` | 参照谱面；仅 `isRealTime` / `isRealEndTime` 为 `True` 时使用 |

**用途**

创建一个 Note 规格 Dict，不修改谱面，也不计算 `floorPosition`。

**具体实现**

整线插入时由 [`addLine()`](#addline) 计算。

单节点追加使用 [`addNote()`](#addnote)， 由后者根据参数计算头部高度和 Hold 尾部信息。

- `type` 不区分大小写
- Tap / Drag 完全忽略 `endtime`
- Hold 的 `endtime` 必须大于 `time`
- 头部/尾部是否在线的首末节点之间，由插入函数检查；`createNote()`
  本身不需要线上下文
- tick 规格不需要 `chart`；`isRealTime` / `isRealEndTime` 为 `True` 时
  必须提供有效 `chart`

**注意事项/细节**

不包含 `floorPosition` 和 `otherInformations`。

**返回值**

不修改谱面，直接返回一个 **Note 规格 Dict**：

```python
# Tap / Drag
{
    "type": int,
    "time": float,
}

# Hold
{
    "type": 2,
    "time": float,
    "endtime": float,
}
```

参数或谱面非法时返回 `None`。

**示例**

```python
from rizChartFunction import createNote

# Tap，头部在 1.5
note = createNote(1.5, "tap")

# Hold，尾部在 2.5
hold = createNote(1.5, "hold", 2.5)

# 实际秒数：0.9 秒 @ 100 BPM = tick 1.5
note = createNote(0.9, "tap", isRealTime=True, chart=chart)
```

### `addNote()`

**函数声明**

```python
addNote(chart: dict, index: int, time: float,
        type: int | str, endtime: float = 0.0,
        isDelayCalculate: bool = False,
        isRealTime: bool = False,
        isRealEndTime: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | Note 头部时间，必须在线的首末节点之间 |
| `type` | `int \| str` | 是 | - | `0`/`"tap"`、`1`/`"drag"`、`2`/`"hold"`，不区分大小写 |
| `endtime` | `float` | 否 | `0.0` | 仅 Hold 有效；必须大于 `time` 且不超过线尾节点时间 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `True` 时 `endtime` 是实际秒数 |

**用途**

向指定引导线添加一个 Note。

**输入限制**

参数、时间范围、类型、画布或结构非法时返回 `None`，且不修改谱面。

**具体实现**

按 `time` 插入，`notes[].time` 保持非递减。

**注意事项/细节**

相同时间允许，新 Note 放在已有 Note 之后。

**头部画布规则**（与 Hold 尾部不同）：

```text
[p_i.time, p_{i+1}.time)  → p_i.canvasIndex
t == p_j.time             → p_j.canvasIndex（右侧节点，含最后一个节点）
```

**Hold 尾部画布规则**：

```text
(p_i.time, p_{i+1}.time]  → p_i.canvasIndex
t == p_j.time             → p_{j-1}.canvasIndex（左侧节点/前一段）
```

- `notes[].floorPosition` 默认为头部所在画布在头部时间的 `floorPosition`；
  `isDelayCalculate=True` 时为 `NaN`
- Hold 的 `otherInformations = [尾部时间, 尾部画布, 尾部 floorPosition]`；
  `isDelayCalculate=True` 时尾部 floorPosition 为 `NaN`
- Tap / Drag 的 `otherInformations = []`，并完全忽略 `endtime`
- Hold 未提供有效 `endtime`（默认 `0.0` 通常无效）会失败

**返回值**

成功返回插入后的 Note 索引；参数、时间范围、类型、画布或结构非法时返回 `None`，且不修改谱面。


**示例**

```python
from rizChartFunction import addNote

# 头部在 1.5：属于 [1,2) 段，画布 0
addNote(chart, 0, 1.5, "tap")

# 头部正好在 2.0：属于右侧节点，画布 1
addNote(chart, 0, 2.0, "tap")

# 尾部正好在 2.0：属于左侧区间 (1,2]，画布 0
addNote(chart, 0, 1.5, "hold", 2.0)

# 尾部 2.5：大于 2.0，画布 1
addNote(chart, 0, 1.5, "hold", 2.5)
```

### `setNote()`

**函数声明**

```python
setNote(chart: dict, lineindex: int = -1,
        noteindex: int = -1, time: float | None = None,
        type: int | str | None = None,
        endtime: float | None = None,
        isDelayCalculate: bool = False,
        isRealTime: bool = False,
        isRealEndTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `noteindex` | `int` | 否 | `-1` | Note 索引，0 起，负数从末尾计算 |
| `time` | `float \| None` | 否 | `None` | 新头部时间；`None` 表示不修改 |
| `type` | `int \| str \| None` | 否 | `None` | 新类型；`None` 表示不修改 |
| `endtime` | `float \| None` | 否 | `None` | 新尾部时间；`None` 表示不修改 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `True` 时 `endtime` 是实际秒数 |

**用途**

修改一个 Note。

**注意事项/细节**

类型转换规则：

- Tap/Drag 保持 Tap/Drag：保留旧 `otherInformations`，忽略 `endtime`
- Tap/Drag → Hold：必须提供 `endtime`
- Hold → Tap/Drag：清空 `otherInformations`，忽略 `endtime`，不比较新头部时间与旧尾部时间
- Hold → Hold：`endtime=None` 时沿用旧尾部；否则使用新值
- `type=None` 且原本是 Hold：`endtime` 有值时更新尾部

修改头部时间后按时间重排。

相同时间放在已有 Note 之后。

头部与 Hold 尾部的画布规则、`floorPosition` 重算与 `addNote()` 相同。
`isDelayCalculate=True` 时头部与 Hold 尾部高度写为 `NaN`，需要随后调用
`refresh()`。

**返回值**

成功返回修改前的原 Note 规格 Dict。

失败返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import setNote

# Tap 变 Hold，并指定尾部
old = setNote(chart, 0, 0, type="hold", endtime=2.5)

# Hold 变 Drag，同时把头部移到 3.0（不比较旧尾部）
old = setNote(chart, 0, 0, type="drag", time=3.0)
```

### `deleteNote()`

**函数声明**

```python
deleteNote(chart: dict, lineindex: int = -1,
           noteindex: int = -1) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `noteindex` | `int` | 否 | `-1` | Note 索引，0 起，负数从末尾计算 |

**用途**

删除一个 Note。

**注意事项/细节**

允许删除最后一个 Note，使 `notes` 变为 空列表。

**返回值**

删除指定 Note 并返回原 Note 的规格 Dict。

`notes` 为空、索引不存在或结构非法时返回 `None`。

**示例**

```python
from rizChartFunction import deleteNote

removed = deleteNote(chart, lineindex=0, noteindex=-1)
if removed is None:
    raise RuntimeError("删除 Note 失败")
```

## BPM

### `addBpmShift()`

**函数声明**

```python
addBpmShift(chart: dict, value: float, time: float,
            isDelayCalculate: bool = False,
            isRealtime: bool = False, isFixedTime: bool = False,
            isMultiply: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `value` | `float` | 是 | - | 变化值，必须大于 `0` |
| `time` | `float` | 是 | - | 变化时间点，必须大于等于 `0` |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isRealtime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数，否则是 tick |
| `isFixedTime` | `bool` | 否 | `False` | 是否保持后续节点的绝对时间不变 |
| `isMultiply` | `bool` | 否 | `False` | `True` 时 `value` 是倍率，否则是实际 BPM |

**用途**

添加或修改一个 BPM 变化节点。

**输入限制**

参数、结构或时间轴不合法时返回 `None`，且不修改谱面。

**注意事项/细节**

- 谱面通常需要在 `time=0.0` 处有一个 BPM 节点。
  **缺少该节点时，本函数是唯一可以补上它的入口**：只接受 `time=0.0`
  （或 `isRealtime=True` 且 `time=0.0` 秒），直接在 `bpmShifts` 最前方
  插入节点；其他时间点返回 `None`。此时若 `isFixedTime=True`，会以
  文件中已有的 `bpmShifts[].floorPosition` 作为旧绝对时间参照。
- `isRealtime=False`：直接在 `bpmShifts[].time`（tick）处添加。
- `isRealtime=True`：先按当前 BPM 时间轴把秒数换算为 tick。
- `isMultiply=False`：节点 `value` 设为 `value / bPM`。
- `isMultiply=True`：节点 `value` 直接设为 `value`。
- 已有节点的 `time` 相同时，新节点插入到已有同时间节点之后，不修改已有节点；同一时间以最右侧的 BPM 节点为准。
- `isFixedTime=True` 时，调整后续节点的 `time` 以保持它们的绝对时间不变。
- 默认无论是否固定时间，都会按新的 BPM 时间轴重新计算整份谱面的相关
  `floorPosition`（`bpmShifts`、`canvasMoves[].speedKeyPoints`、
  `lines[].linePoints`、`lines[].notes` 以及 Hold 尾部的
  `otherInformations[2]`）。
- `isDelayCalculate=True` 时跳过这次全谱重算，新 BPM 节点的
  `floorPosition` 写为 `NaN`，需要随后调用 `refresh()`。

**返回值**

成功返回插入后的 BPM 节点索引；参数、结构或时间轴不合法时返回 `None`，且不修改谱面。相同时间的节点会插入到已有节点之后。


**示例**

```python
from rizChartFunction import new, addBpmShift

chart = new(100.0)

# 第 4 tick 变成 200 BPM
addBpmShift(chart, 200.0, 4.0)

# 第 8 tick 的倍率设为 2
addBpmShift(chart, 2.0, 8.0, isMultiply=True)

# 在实际时间 2.4 秒处设为 150 BPM，并保持后续绝对时间不变
addBpmShift(chart, 150.0, 2.4, isRealtime=True, isFixedTime=True)
```

### `setBpmShift()`

**函数声明**

```python
setBpmShift(chart: dict, index: int = -1, value: float | None = None,
            time: float | None = None,
            isDelayCalculate: bool = False,
            isRealtime: bool = False,
            isFixedTime: bool = False, isMultiply: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `value` | `float \| None` | 否 | `None` | 变化值；`None` 表示不修改，否则必须大于 `0.0` |
| `time` | `float \| None` | 否 | `None` | 节点时间；`None` 表示不修改，否则必须大于 `0.0` |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isRealtime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isFixedTime` | `bool` | 否 | `False` | 是否保持修改点之后节点的绝对时间不变 |
| `isMultiply` | `bool` | 否 | `False` | `True` 时 `value` 是倍率，否则是实际 BPM |

**用途**

修改一个 BPM 变化节点。

**输入限制**

参数、结构或时间冲突等导致失败时返回 `None`，且不修改谱面。

**注意事项/细节**

- 指向第 0 个节点时不能修改 `time`，但允许传入 `0.0`。
- 修改 `time` 后会自动重排，保持 `bpmShifts[].time` 非递减；相同时间允许。
- 若新时间与其他节点冲突，返回 `None`。
- `isFixedTime=True` 时调整新位置之后节点的 `time`，保持其绝对时间不变。
- 默认会按新的 BPM 时间轴重新计算整份谱面的相关 `floorPosition`
  （`bpmShifts`、`canvasMoves[].speedKeyPoints`、`lines[].linePoints`、
  `lines[].notes` 以及 Hold 尾部的 `otherInformations[2]`）。
- `isDelayCalculate=True` 时跳过全谱重算，修改后 BPM 节点的
  `floorPosition` 写为 `NaN`，需要随后调用 `refresh()`。

**返回值**

成功返回修改前的原节点的规格 Dict；参数、结构或时间冲突导致失败时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addBpmShift, setBpmShift

chart = new(100.0)
addBpmShift(chart, 200.0, 4.0)
addBpmShift(chart, 2.0, 8.0, isMultiply=True)

old = setBpmShift(chart, index=1, value=150.0, isFixedTime=True)
if old is None:
    raise RuntimeError("修改 BPM 节点失败")

print(old)  # 修改前的节点规格 Dict
```

### `deleteBpmShift()`

**函数声明**

```python
deleteBpmShift(chart: dict, index: int = -1,
               isDelayCalculate: bool = False,
               isFixedTime: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 否 | `-1` | 节点索引，0 起，负数从末尾计算 |
| `isDelayCalculate` | `bool` | 否 | `False` | 为 `True` 时跳过 `floorPosition` 计算/全谱重算，需随后调用 `refresh()` |
| `isFixedTime` | `bool` | 否 | `False` | 是否保持删除点之后节点的绝对时间不变 |

**用途**

删除一个 BPM 变化节点。

**注意事项/细节**

- 删除 `bpmShifts[index]`。
- 指向第 0 个节点时不删除，而是重置为 `new()` 中的初始节点：
  `time=0.0, value=1.0, easeType=0`；默认 `floorPosition=0.0`，
  `isDelayCalculate=True` 时为 `NaN`。
- `isFixedTime=True` 时调整删除点之后节点的 `time`，保持其绝对时间不变。
- 默认会按新的 BPM 时间轴重新计算整份谱面的相关 `floorPosition`
  （`bpmShifts`、`canvasMoves[].speedKeyPoints`、`lines[].linePoints`、
  `lines[].notes` 以及 Hold 尾部的 `otherInformations[2]`）。
- `isDelayCalculate=True` 时跳过全谱重算，需要随后调用 `refresh()`。

**返回值**

成功返回被删除/被重置前的原节点的规格 Dict。

索引不存在、结构非法或无法删除 时返回 `None`，且不修改谱面。

**示例**

```python
from rizChartFunction import new, addBpmShift, deleteBpmShift

chart = new(100.0)
addBpmShift(chart, 200.0, 8.0)

old = deleteBpmShift(chart, index=1, isFixedTime=True)
if old is None:
    raise RuntimeError("删除 BPM 节点失败")

print(old)  # 被删除的节点规格 Dict

# 指向第 0 个节点时只重置，不删除
old_first = deleteBpmShift(chart, index=0)
```
