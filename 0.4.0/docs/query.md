# query 模块函数说明

[← 返回总览](README.md)

`query.py` 负责元数据、对象、时间、颜色、几何与计算查询。

> 函数性能使用 `0-10` 相对开销标注，统一说明见 [PERFORMANCE.md](PERFORMANCE.md)。
>
> 所有可失败函数额外接受 keyword-only `isReturnException`；设为 `True` 时失败抛出自定义异常，详见 [EXCEPTIONS.md](EXCEPTIONS.md)。

## 目录

- [元数据与计数](#元数据与计数)
  - [`getFileVersion()`](#getfileversion)
  - [`getDelay()`](#getdelay)
  - [`getBaseBpm()`](#getbasebpm)
  - [`getLineCount()`](#getlinecount)
  - [`getCanvasCount()`](#getcanvascount)
  - [`getBpmShiftCount()`](#getbpmshiftcount)
  - [`getRiztimeCount()`](#getriztimecount)
  - [`getNoteCount()`](#getnotecount)
- [对象查询](#对象查询)
  - [`getBpmShift()`](#getbpmshift)
  - [`getCanvas()`](#getcanvas)
  - [`getCanvasPosition()`](#getcanvasposition)
  - [`getCanvasSpeed()`](#getcanvasspeed)
  - [`getCamera()`](#getcamera)
  - [`getCameraPosition()`](#getcameraposition)
  - [`getCameraScale()`](#getcamerascale)
  - [`getLine()`](#getline)
  - [`getLinePoint()`](#getlinepoint)
  - [`getRingPoint()`](#getringpoint)
  - [`getLineColor()`](#getlinecolor)
  - [`getNote()`](#getnote)
  - [`getTheme()`](#gettheme)
  - [`getThemeColor()`](#getthemecolor)
  - [`getChallengeTime()`](#getchallengetime)
  - [`getRiztime()`](#getriztime)
- [按时间查询](#按时间查询)
  - [`getBpmShiftByTime()`](#getbpmshiftbytime)
  - [`getCanvasPositionByTime()`](#getcanvaspositionbytime)
  - [`getCanvasSpeedByTime()`](#getcanvasspeedbytime)
  - [`getCameraPositionByTime()`](#getcamerapositionbytime)
  - [`getCameraScaleByTime()`](#getcamerascalebytime)
  - [`getLinePointByTime()`](#getlinepointbytime)
  - [`getRingPointByTime()`](#getringpointbytime)
  - [`getLineColorByTime()`](#getlinecolorbytime)
  - [`getNoteByTime()`](#getnotebytime)
- [按颜色查询](#按颜色查询)
  - [`getThemeByColor()`](#getthemebycolor)
  - [`getLinePointByColor()`](#getlinepointbycolor)
  - [`getRingPointByColor()`](#getringpointbycolor)
  - [`getLineColorByColor()`](#getlinecolorbycolor)
- [颜色查询](#颜色查询)
  - [`getBaseColor()`](#getbasecolor)
  - [`getCoverColor()`](#getcovercolor)
  - [`getRingColor()`](#getringcolor)
  - [`getMixColor()`](#getmixcolor)
- [BPM 与时间](#bpm-与时间)
  - [`getBpmAt()`](#getbpmat)
  - [`getSecondsAt()`](#getsecondsat)
  - [`getTickAt()`](#gettickat)
- [画布与摄像机](#画布与摄像机)
  - [`getCanvasSpeedAt()`](#getcanvasspeedat)
  - [`getCameraPositionAt()`](#getcamerapositionat)
  - [`getCameraScaleAt()`](#getcamerascaleat)
- [计算与搜索](#计算与搜索)
  - [`getFloorPosition()`](#getfloorposition)
  - [`getCanvasPositionAt()`](#getcanvaspositionat)
  - [`getLinePosition()`](#getlineposition)
  - [`getLineByPoint()`](#getlinebypoint)
  - [`getLineByNote()`](#getlinebynote)
  - [`getLineTimeRange()`](#getlinetimerange)
  - [`getNotePosition()`](#getnoteposition)
  - [`getNoteCanvas()`](#getnotecanvas)
- [视觉比例](#视觉比例)
  - [`getXYRatio()`](#getxyratio)
  - [`getXYRatioByChart()`](#getxyratiobychart)
- [视觉边界](#视觉边界)
  - [`getXBorder()`](#getxborder)
  - [`getXBorderByChart()`](#getxborderbychart)
  - [`getYBorder()`](#getyborder)
  - [`getYBorderByChart()`](#getyborderbychart)
- [游戏区域与线宽](#游戏区域与线宽)
  - [`getGameScale()`](#getgamescale)
  - [`getLineWidth()`](#getlinewidth)
- [判定环半径](#判定环半径)
  - [`getRingRadius()`](#getringradius)
- [遮罩透明度](#遮罩透明度)
  - [`getShadeOpacity()`](#getshadeopacity)

## 元数据与计数

### `getFileVersion()`

**函数声明**

```python
getFileVersion(chart: dict, *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询谱面文件版本。

**返回值**

返回 `fileVersion`。

缺失、不是 `int` 或谱面非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读单个字段。

### `getDelay()`

**函数声明**

```python
getDelay(chart: dict, *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询谱面延迟（毫秒）。

**返回值**

返回 `chartDelayMs`（毫秒）。

缺失、不是 `int` 或谱面非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读单个字段。

### `getBaseBpm()`

**函数声明**

```python
getBaseBpm(chart: dict, *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询基准 BPM。

**输入限制**

必须是有限正数。

**返回值**

返回 `bPM`。

缺失、非正数或结构非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读单个字段。

### `getLineCount()`

**函数声明**

```python
getLineCount(chart: dict, *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询引导线数量。

**返回值**

返回引导线数量。

`lines` 不是列表时返回 `None`。

合法空列表返回 `0`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读数组长度。

### `getCanvasCount()`

**函数声明**

```python
getCanvasCount(chart: dict, *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询画布数量。

**返回值**

返回画布数量。

`canvasMoves` 不是列表时返回 `None`。

合法空列表返回 `0`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读数组长度。

### `getBpmShiftCount()`

**函数声明**

```python
getBpmShiftCount(chart: dict, *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询 BPM 变化节点数量。

**返回值**

返回 BPM 变化节点数量。

`bpmShifts` 不是列表时返回 `None`。

合法空列表 返回 `0`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读数组长度。

### `getRiztimeCount()`

**函数声明**

```python
getRiztimeCount(chart: dict, *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询 Riztime 数量。

**返回值**

返回 Riztime 数量，即 `challengeTimes` 的长度。

结构非法时返回 `None`。

合法空列表返回 `0`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只读数组长度。

**示例**

```python
from rizChartFunction import (
    new, getFileVersion, getDelay, getBaseBpm,
    getLineCount, getCanvasCount,
    getBpmShiftCount, getRiztimeCount,
)

chart = new(100.0)

print(getFileVersion(chart))    # 0
print(getDelay(chart))          # 0
print(getBaseBpm(chart))        # 100.0
print(getLineCount(chart))      # 0
print(getCanvasCount(chart))    # 1
print(getBpmShiftCount(chart))  # 1
print(getRiztimeCount(chart))   # 1
```

### `getNoteCount()`

**函数声明**

```python
getNoteCount(chart: dict, startindex: int,
             endindex: int | None = None,
             *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 开始线索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束线索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定线索引范围内所有线的 Note 总数。

**输入限制**

统计指定线索引范围内所有线的 Note 总数。

- `endindex=None`：只查一条线
- `endindex` 为 `int`：查询闭区间 `[startindex, endindex]`
- 查询全部线：`getNoteCount(chart, 0, -1)`
- 按每条线的 `notes` 列表长度统计；合法但没有 Note 时返回 `0`
- 索引或结构非法时返回 `None`

**返回值**

成功返回整数；失败返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(1)`
- 大参数提示：需要遍历所有线及其 Note；大谱面更慢。

**示例**

```python
from rizChartFunction import (
    new, addLine, createLinePoint, createRingPoint,
    createNote, getNoteCount,
)

chart = new(100.0)
p0 = createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
p4 = createLinePoint(4.0, 1.0, 0, 0, "#FFFFFF")
ring = createRingPoint(0.0, "#FFFFFF")

addLine(chart, [p0, p4], ring, notes=[
    createNote(1.0, "tap"),
    createNote(2.0, "hold", 3.0),
])
addLine(chart, [p0, p4], ring, notes=[
    createNote(1.0, "tap"),
])

print(getNoteCount(chart, 0))     # 2
print(getNoteCount(chart, 0, 1))  # 3
print(getNoteCount(chart, 0, -1)) # 3
```

## 对象查询

### `getBpmShift()`

**函数声明**

```python
getBpmShift(chart: dict, startindex: int,
            endindex: int | None = None,
            *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段 BPM 节点规格。

**注意事项/细节**

不含 `floorPosition`。

`getBpmShift(chart, 0, -1)` 查询全部。

**返回值**

返回 BPM 节点规格：

```python
{"time": float, "value": float, "easeType": int}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回节点数；复制范围越大越慢。

### `getCanvas()`

**函数声明**

```python
getCanvas(chart: dict, startindex: int,
          endindex: int | None = None,
          *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始画布索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段画布规格。

**注意事项/细节**

关键点规格为 `{time, value, easeType}`，不含 `floorPosition`。

**返回值**

返回画布规格：

```python
{
    "index": int,
    "xPositionKeyPoints": [...],
    "speedKeyPoints": [...],
}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回画布数；范围越大越慢。

### `getCanvasPosition()`

**函数声明**

```python
getCanvasPosition(chart: dict, canvasindex: int,
                  startindex: int,
                  endindex: int | None = None,
                  *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始关键点索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定画布的 x 位置关键点规格。

**输入限制**

需要查询某一时刻的画布 x 坐标时，使用 `getCanvasPositionAt()`。

**返回值**

返回画布 `xPositionKeyPoints` 的关键点规格：

```python
{"time": float, "value": float, "easeType": int}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回关键点数。

### `getCanvasSpeed()`

**函数声明**

```python
getCanvasSpeed(chart: dict, canvasindex: int,
               startindex: int,
               endindex: int | None = None,
               *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `canvasindex` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始关键点索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定画布的流速关键点规格。

**返回值**

返回画布 `speedKeyPoints` 的关键点规格，不含 `floorPosition`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回关键点数。

### `getCamera()`

**函数声明**

```python
getCamera(chart: dict, *, isReturnException: bool = False) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询摄像机规格。

**返回值**

返回摄像机规格：

```python
{
    "scaleKeyPoints": [...],
    "xPositionKeyPoints": [...],
}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回关键点数。

### `getCameraPosition()`

**函数声明**

```python
getCameraPosition(chart: dict, startindex: int,
                  endindex: int | None = None,
                  *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始关键点索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段摄像机 x 位置关键点规格。

**返回值**

返回摄像机 `xPositionKeyPoints` 的关键点规格。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回关键点数。

### `getCameraScale()`

**函数声明**

```python
getCameraScale(chart: dict, startindex: int,
               endindex: int | None = None,
               *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始关键点索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段摄像机缩放关键点规格。

**返回值**

返回摄像机 `scaleKeyPoints` 的关键点规格。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回关键点数。

### `getLine()`

**函数声明**

```python
getLine(chart: dict, startindex: int,
        endindex: int | None = None,
        *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始线索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段引导线规格。

**注意事项/细节**

数组元素都是规格 Dict，不含派生字段。

**返回值**

返回引导线规格：

```python
{
    "linePoints": [...],
    "notes": [...],
    "judgeRingColor": [...],
    "lineColor": [...],
}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回线/节点数；复制完整线时更重。

### `getLinePoint()`

**函数声明**

```python
getLinePoint(chart: dict, lineindex: int,
             startindex: int,
             endindex: int | None = None,
             *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始线节点索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一条引导线上的线节点规格。

**返回值**

返回线节点规格：

```python
{
    "time": float,
    "xPosition": float,
    "canvasIndex": int,
    "easeType": int,
    "color": [r, g, b, a],
}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回节点数。

### `getRingPoint()`

**函数声明**

```python
getRingPoint(chart: dict, lineindex: int,
             startindex: int,
             endindex: int | None = None,
             *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始判定环索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一条引导线上的判定环规格。

**返回值**

返回判定环规格：

```python
{"startColor": [r, g, b, a], "endColor": [r, g, b, a], "time": float}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回节点数。

### `getLineColor()`

**函数声明**

```python
getLineColor(chart: dict, lineindex: int,
             startindex: int,
             endindex: int | None = None,
             *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始线色节点索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一条引导线上的线色覆盖规格。

**返回值**

返回线色覆盖规格：

```python
{"startColor": [r, g, b, a], "endColor": [r, g, b, a], "time": float}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回节点数。

### `getNote()`

**函数声明**

```python
getNote(chart: dict, lineindex: int,
        startindex: int,
        endindex: int | None = None,
        *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始 Note 索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一条引导线上的 Note 规格。

**返回值**

返回 Note 规格：

```python
# Tap / Drag
{"type": int, "time": float}

# Hold
{"type": 2, "time": float, "endtime": float}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(n)`；空间复杂度：`O(n)`
- 大参数提示：n 为返回 Note 数。

### `getTheme()`

**函数声明**

```python
getTheme(chart: dict, startindex: int,
         endindex: int | None = None,
         *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始主题索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段主题规格。

**返回值**

返回主题规格：

```python
{"colorsList": [[r, g, b, a], [r, g, b, a], [r, g, b, a]]}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartThemeError`；可能异常：`RizChartThemeError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只取主题规格。

### `getThemeColor()`

**函数声明**

```python
getThemeColor(chart: dict, themeindex: int,
              startindex: int,
              endindex: int | None = None,
              *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `themeindex` | `int` | 是 | - | 主题索引，0 起，负数从末尾计算 |
| `startindex` | `int` | 是 | - | 起始颜色索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个主题内的颜色规格。

**返回值**

返回 RGBA 颜色规格：

```python
[r, g, b, a]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartThemeError`；可能异常：`RizChartThemeError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只取主题颜色。

### `getChallengeTime()`

**函数声明**

```python
getChallengeTime(chart: dict, startindex: int,
                 endindex: int | None = None,
                 *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段 challengeTimes 规格。

**返回值**

返回 challengeTimes 规格：

```python
{
    "checkPoint": float,
    "start": float,
    "end": float,
    "transTime": float,
}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartThemeError`；可能异常：`RizChartThemeError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(T)`；空间复杂度：`O(T)`
- 大参数提示：T 为返回挑战时间节点数。

### `getRiztime()`

**函数声明**

```python
getRiztime(chart: dict, startindex: int,
           endindex: int | None = None,
           *, isReturnException: bool = False) -> dict | list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startindex` | `int` | 是 | - | 起始 Riztime 索引，0 起，负数从末尾计算 |
| `endindex` | `int \| None` | 否 | `None` | 结束索引（闭区间）；`None` 表示只查 `startindex` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询一个或一段 Riztime 合并规格。

**返回值**

返回合并后的 Riztime 规格：

```python
{
    "themeIndex": int,
    "challengeIndex": int,
    "colorsList": [...],
    "checkPoint": float,
    "start": float,
    "end": float,
    "transTime": float,
}
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartThemeError`；可能异常：`RizChartThemeError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(T)`；空间复杂度：`O(T)`
- 大参数提示：T 为返回 Riztime 节点数。

## 按时间查询

### `getBpmShiftByTime()`

**函数声明**

```python
getBpmShiftByTime(chart: dict, starttime: float,
                  endtime: float | None = None,
                  indexlist: list | None = None,
                  isRealStartTime: bool = False,
                  isRealEndTime: bool = False,
                  *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | BPM 节点索引列表；`None` 表示全局搜索 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询 BPM 节点索引。

**返回值**

返回单层索引列表：

```python
[index, index, ...]
```

没有匹配返回 `[]`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(B)`；空间复杂度：`O(n)`
- 大参数提示：B 为 BPM 节点数；返回匹配节点。

### `getCanvasPositionByTime()`

**函数声明**

```python
getCanvasPositionByTime(chart: dict, starttime: float,
                        endtime: float | None = None,
                        indexlist: list | None = None,
                        canvasindex: int | None = None,
                        isRealStartTime: bool = False,
                        isRealEndTime: bool = False,
                        *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 关键点索引列表；`None` 表示全局搜索 |
| `canvasindex` | `int \| None` | 否 | `None` | 画布索引；`None` 表示所有画布 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询画布 x 位置关键点索引。

**返回值**

返回多层索引列表：

```python
[[canvasindex, pointindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(C)`；空间复杂度：`O(n)`
- 大参数提示：C 为关键点数；返回匹配节点。

### `getCanvasSpeedByTime()`

**函数声明**

```python
getCanvasSpeedByTime(chart: dict, starttime: float,
                     endtime: float | None = None,
                     indexlist: list | None = None,
                     canvasindex: int | None = None,
                     isRealStartTime: bool = False,
                     isRealEndTime: bool = False,
                     *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 关键点索引列表；`None` 表示全局搜索 |
| `canvasindex` | `int \| None` | 否 | `None` | 画布索引；`None` 表示所有画布 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询画布流速关键点索引。

**返回值**

返回多层索引列表：

```python
[[canvasindex, pointindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(C)`；空间复杂度：`O(n)`
- 大参数提示：C 为关键点数；返回匹配节点。

### `getCameraPositionByTime()`

**函数声明**

```python
getCameraPositionByTime(chart: dict, starttime: float,
                        endtime: float | None = None,
                        indexlist: list | None = None,
                        isRealStartTime: bool = False,
                        isRealEndTime: bool = False,
                        *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 关键点索引列表；`None` 表示全局搜索 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询摄像机 x 位置关键点索引。

**返回值**

返回单层索引列表：

```python
[index, index, ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(C)`；空间复杂度：`O(n)`
- 大参数提示：C 为关键点数；返回匹配节点。

### `getCameraScaleByTime()`

**函数声明**

```python
getCameraScaleByTime(chart: dict, starttime: float,
                     endtime: float | None = None,
                     indexlist: list | None = None,
                     isRealStartTime: bool = False,
                     isRealEndTime: bool = False,
                     *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 关键点索引列表；`None` 表示全局搜索 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询摄像机缩放关键点索引。

**返回值**

返回单层索引列表：

```python
[index, index, ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(C)`；空间复杂度：`O(n)`
- 大参数提示：C 为关键点数；返回匹配节点。

### `getLinePointByTime()`

**函数声明**

```python
getLinePointByTime(chart: dict, starttime: float,
                   endtime: float | None = None,
                   indexlist: list | None = None,
                   canvasindex: int | None = None,
                   lineindex: int | None = None,
                   isRealStartTime: bool = False,
                   isRealEndTime: bool = False,
                   *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 线节点索引列表；`None` 表示全局搜索 |
| `canvasindex` | `int \| None` | 否 | `None` | 画布索引；`None` 表示所有画布 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询线节点索引。

**返回值**

返回多层索引列表：

```python
[[lineindex, pointindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：V 为全部线节点；大谱面按时间扫描更慢。

### `getRingPointByTime()`

**函数声明**

```python
getRingPointByTime(chart: dict, starttime: float,
                   endtime: float | None = None,
                   indexlist: list | None = None,
                   lineindex: int | None = None,
                   isRealStartTime: bool = False,
                   isRealEndTime: bool = False,
                   *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 判定环索引列表；`None` 表示全局搜索 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询判定环索引。

**返回值**

返回多层索引列表：

```python
[[lineindex, ringindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：V 为全部判定环节点；范围越大越慢。

### `getLineColorByTime()`

**函数声明**

```python
getLineColorByTime(chart: dict, starttime: float,
                   endtime: float | None = None,
                   indexlist: list | None = None,
                   lineindex: int | None = None,
                   isRealStartTime: bool = False,
                   isRealEndTime: bool = False,
                   *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | 线色节点索引列表；`None` 表示全局搜索 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询线色覆盖索引。

**返回值**

返回多层索引列表：

```python
[[lineindex, colorindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：V 为全部线色节点；范围越大越慢。

### `getNoteByTime()`

**函数声明**

```python
getNoteByTime(chart: dict, starttime: float,
              endtime: float | None = None,
              indexlist: list | None = None,
              lineindex: int | None = None,
              type: int | str | None = None,
              isRealStartTime: bool = False,
              isRealEndTime: bool = False,
              *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `starttime` | `float` | 是 | - | 起始时间，必须大于等于 `0.0` |
| `endtime` | `float \| None` | 否 | `None` | 结束时间；`None` 表示不限制结束时间，等于 `starttime` 表示精确查找 |
| `indexlist` | `list \| None` | 否 | `None` | Note 索引列表；`None` 表示全局搜索 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `type` | `int \| str \| None` | 否 | `None` | Note 类型；`None` 不限；`3`/`"holdtail"` 按 Hold 尾部时间 |
| `isRealStartTime` | `bool` | 否 | `False` | `starttime` 是否为实际秒数 |
| `isRealEndTime` | `bool` | 否 | `False` | `endtime` 是否为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按时间范围查询 Note 索引；`type=3` 按 Hold 尾部时间查询。

**注意事项/细节**

Note 类型：

- `0` / `"tap"`
- `1` / `"drag"`
- `2` / `"hold"`
- `3` / `"holdtail"`：只匹配 Hold，并用 `otherInformations[0]`
  尾部时间参与时间筛选

`type=None` 时按所有 Note 的头部时间筛选。

**返回值**

返回多层索引列表：

```python
[[lineindex, noteindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：V 为全部 Note；时间范围越大越慢。

**示例**

```python
from rizChartFunction import getNoteByTime

# 头部时间在 [5.0, 10.0] 内的 Note
print(getNoteByTime(chart, 5.0, 10.0))

# 只看第 5 条线
print(getNoteByTime(chart, 5.0, 10.0, lineindex=5))

# 找尾部时间在 [5.0, 10.0] 内的 Hold
print(getNoteByTime(chart, 5.0, 10.0, type="holdtail"))

# 精确查找 7.5 时刻
print(getNoteByTime(chart, 7.5, 7.5))
```

## 按颜色查询

### `getThemeByColor()`

**函数声明**

```python
getThemeByColor(chart: dict, startcolor: str | list,
                endcolor: str | list | None = None,
                indexlist: list | None = None,
                *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startcolor` | `str \| list` | 是 | - | 颜色匹配起始值 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 颜色匹配结束值；`None` 表示精确匹配 `startcolor` |
| `indexlist` | `list \| None` | 否 | `None` | 主题索引列表；`None` 表示全局搜索 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按颜色区间查询主题颜色索引。

**注意事项/细节**

主题的 `colorsList` 中每个颜色独立匹配。

`colorindex` 是 `colorsList[colorindex]` 的下标。

**返回值**

返回主题索引和颜色索引：

```python
[[themeindex, colorindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartThemeError`；可能异常：`RizChartThemeError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(T)`；空间复杂度：`O(n)`
- 大参数提示：T 为主题/挑战时间数量。

### `getLinePointByColor()`

**函数声明**

```python
getLinePointByColor(chart: dict, startcolor: str | list,
                    endcolor: str | list | None = None,
                    indexlist: list | None = None,
                    canvasindex: int | None = None,
                    lineindex: int | None = None,
                    *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startcolor` | `str \| list` | 是 | - | 颜色匹配起始值 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 颜色匹配结束值；`None` 表示精确匹配 `startcolor` |
| `indexlist` | `list \| None` | 否 | `None` | 线节点索引列表；`None` 表示全局搜索 |
| `canvasindex` | `int \| None` | 否 | `None` | 画布索引；`None` 表示所有画布 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按颜色区间查询线节点索引。

**返回值**

返回多层索引列表：

```python
[[lineindex, pointindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`4/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：扫描全部线节点；大谱面明显变慢。

### `getRingPointByColor()`

**函数声明**

```python
getRingPointByColor(chart: dict, startcolor: str | list,
                    endcolor: str | list | None = None,
                    indexlist: list | None = None,
                    lineindex: int | None = None,
                    *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startcolor` | `str \| list` | 是 | - | 颜色匹配起始值 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 颜色匹配结束值；`None` 表示精确匹配 `startcolor` |
| `indexlist` | `list \| None` | 否 | `None` | 判定环索引列表；`None` 表示全局搜索 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按颜色区间查询判定环索引。

**注意事项/细节**

`startColor` 或 `endColor` 任一落入区间即匹配。

**返回值**

返回：

```python
[[lineindex, ringindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`4/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：扫描全部判定环节点。

### `getLineColorByColor()`

**函数声明**

```python
getLineColorByColor(chart: dict, startcolor: str | list,
                    endcolor: str | list | None = None,
                    indexlist: list | None = None,
                    lineindex: int | None = None,
                    *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `startcolor` | `str \| list` | 是 | - | 颜色匹配起始值 |
| `endcolor` | `str \| list \| None` | 否 | `None` | 颜色匹配结束值；`None` 表示精确匹配 `startcolor` |
| `indexlist` | `list \| None` | 否 | `None` | 线色节点索引列表；`None` 表示全局搜索 |
| `lineindex` | `int \| None` | 否 | `None` | 线索引；`None` 表示所有线 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按颜色区间查询线色覆盖索引。

**注意事项/细节**

`startColor` 或 `endColor` 任一落入区间即匹配。

`endcolor` 省略的通道按 `255` 处理；因此若 `startcolor` 的 Alpha 为
`250`，省略 `endcolor` 后 Alpha 匹配区间是 `250-255`。

**返回值**

返回：

```python
[[lineindex, colorindex], ...]
```

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`4/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：扫描全部线色节点。

**示例**

```python
from rizChartFunction import (
    getThemeByColor, getLinePointByColor,
    getRingPointByColor, getLineColorByColor,
)

start = [0, 20, 65, 250]
end = [255, 70, 65]

print(getThemeByColor(chart, start, end))
print(getLinePointByColor(chart, start, end))
print(getRingPointByColor(chart, start, end))
print(getLineColorByColor(chart, start, end))
```

## 颜色查询

### `getBaseColor()`

**函数声明**

```python
getBaseColor(chart: dict, index: int, time: float,
             position: float | None = None,
             isRealTime: bool = False,
             isAbsolutePosition: bool = False,
             *, isReturnException: bool = False) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 查询时间点，必须在头节点与尾节点时间之间 |
| `position` | `float \| None` | 否 | `None` | 查询 x 坐标；`None` 表示忽略此值 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isAbsolutePosition` | `bool` | 否 | `False` | 是否使用绝对 x 坐标 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定引导线在指定时间/位置的基础色。

**注意事项/细节**

查询指定线在指定位置的基础色，不叠加 `lineColor`。

- 查询时间处没有节点：在前后节点之间按时间线性插值，忽略 `position`。
- 查询时间处只有一个节点：直接返回该节点颜色，忽略 `position`。
- 查询时间处有多个同时间节点：必须提供 `position`。按 `linePoints`
  存储顺序连接同时间节点，颜色沿 x 线性过渡；后面的线段覆盖前面的
  线段，返回包含 `position` 的最上层线段颜色。
- 同时间线段两端 x 相同时，按后一个节点的颜色处理。
- `isAbsolutePosition=True` 时，每个节点使用自己的 `canvasIndex` 加上
  该时刻画布 x 坐标后再比较；`False` 时直接使用 `xPosition`。
- 颜色 RGBA 四通道线性插值，`easeType` 不影响颜色。
- 时间越界、同时间多节点缺少 `position`、位置不在任何线段上或结构非法
  时返回 `None`。

**返回值**

成功返回颜色列表 `[r, g, b, a]`；失败返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartColorError`；可能异常：`RizChartColorError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(1)`
- 大参数提示：按线节点/颜色节点插值；节点越多越慢。

**示例**

```python
from rizChartFunction import getBaseColor

# 普通时间插值
color = getBaseColor(chart, 0, 2.5)

# 同时间多节点必须指定位置，绝对坐标按各节点画布换算
color = getBaseColor(
    chart, 1, 5.0, position=5.5, isAbsolutePosition=True,
)
```

### `getCoverColor()`

**函数声明**

```python
getCoverColor(chart: dict, index: int, time: float,
              isRealTime: bool = False,
              *, isReturnException: bool = False) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 所处时间点，必须大于等于 `0.0` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定引导线在指定时间的线色覆盖色。

**注意事项/细节**

查询指定线在指定时间的线色覆盖色。

- `lineColor` 必须非空；为空时返回 `None`。
- 覆盖色节点可以位于引导线时间范围之外，因此 `time` 只要求 `>= 0.0`。
- 早于第一个节点时，返回第一个节点的 `startColor`。
- 晚于或等于最后一个节点时，返回最后一个节点的 `startColor`。
- 正好命中节点时，返回该节点的 `startColor`；同时间多个节点取最右侧。
- 两个节点之间，从当前节点的 `startColor` 线性过渡到当前节点的
  `endColor`，终点是下一个节点的时间。
- 颜色 RGBA 四通道线性插值；结构非法或索引不存在时返回 `None`。

**返回值**

成功返回颜色列表 `[r, g, b, a]`；失败返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartColorError`；可能异常：`RizChartColorError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(1)`
- 大参数提示：按线色覆盖节点查找/插值。

**示例**

```python
from rizChartFunction import getCoverColor

color = getCoverColor(chart, 0, 6.0)
```

### `getRingColor()`

> **版本提示**：本函数自 `0.2.0` 起提供；在 `0.2.0` 之前的版本中不可用。

**函数声明**

```python
getRingColor(chart: dict, index: int, time: float,
             isRealTime: bool = False,
             *, isReturnException: bool = False) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 查询时间，必须大于 `0.0` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定引导线在指定时间的判定环颜色，返回 RGBA 列表。

**注意事项/细节**

- `judgeRingColor` 必须非空；为空时返回 `None`。
- 判定环颜色节点可以位于引导线时间范围之外，因此不检查线节点范围。
- 早于第一个节点时，返回第一个节点的 `startColor`。
- 正好命中节点时，返回该节点的 `startColor`；同一时间存在多个节点时，
  返回索引最大的节点的 `startColor`。
- 两个节点之间，从前一个节点的 `startColor` 线性过渡到其
  `endColor`，终点是下一个节点的时间。
- 晚于最后一个节点时，返回最后一个节点的 `startColor`，可视为其
  `endColor` 位于无穷远处。
- 颜色按 RGBA 四通道线性插值。
- `time <= 0.0`、索引不存在或结构非法时返回 `None`。

**返回值**

成功返回颜色列表 `[r, g, b, a]`；失败返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartColorError`；可能异常：`RizChartColorError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(1)`
- 大参数提示：V 为指定引导线的判定环颜色节点数；节点越多越慢。

**示例**

```python
from rizChartFunction import getRingColor

color = getRingColor(chart, 0, 2.0)
color = getRingColor(chart, 0, 1.0, isRealTime=True)
```

### `getMixColor()`

**函数声明**

```python
getMixColor(chart: dict, index: int, currenttime: float,
            querytime: float | None = None,
            position: float | None = None,
            isRealCurrentTime: bool = False,
            isRealQueryTime: bool = False,
            isAbsolutePosition: bool = False,
            *, isReturnException: bool = False) -> list[int] | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引，0 起，负数从末尾计算 |
| `currenttime` | `float` | 是 | - | 线色覆盖色的所处时间，必须大于等于 `0.0` |
| `querytime` | `float \| None` | 否 | `None` | 基础色查询时间；`None` 表示使用 `currenttime` |
| `position` | `float \| None` | 否 | `None` | 基础色查询 x 坐标；`None` 表示忽略此值 |
| `isRealCurrentTime` | `bool` | 否 | `False` | `True` 时 `currenttime` 是实际秒数 |
| `isRealQueryTime` | `bool` | 否 | `False` | `True` 时 `querytime` 是实际秒数 |
| `isAbsolutePosition` | `bool` | 否 | `False` | 是否使用绝对 x 坐标 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定引导线在指定位置的混合色。

**返回值**

把 `getBaseColor(querytime)` 当作 basecolor，把 `getCoverColor(currenttime)` 当作 covercolor，返回 `mixColor()` 的结果。

- `querytime=None` 时使用 `currenttime` 换算后的 tick。
- `querytime` 必须位于线的头节点与尾节点时间之间。
- `currenttime` 只需大于等于 `0.0`，可以位于线的时间范围之外。
- `lineColor` 为空、基础色查询失败或覆盖色查询失败时返回 `None`。
- 结果 alpha 等于基础色 alpha，覆盖色 alpha 只作为 RGB 混合系数。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartColorError`；可能异常：`RizChartColorError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`4/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(1)`
- 大参数提示：同时考虑基础色和覆盖色；大谱面更慢。

**示例**

```python
from rizChartFunction import getMixColor

# querytime 处的基础色 + currenttime 处的覆盖色
color = getMixColor(chart, 0, currenttime=10.0, querytime=0.0)

# querytime=None 时使用 currenttime
color = getMixColor(chart, 0, currenttime=1.0, isRealCurrentTime=True)
```

## BPM 与时间

### `getBpmAt()`

**函数声明**

```python
getBpmAt(chart: dict, time: float, isRealTime: bool = False, *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数，否则是 tick |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定时间点的实际 BPM。

**返回值**

返回该时刻生效的**实际 BPM**，即 `bPM * bpmShifts[].value`。

- 谱面必须在 `time=0.0` 处有一个 BPM 节点。
- 正好命中 BPM 节点时使用该节点的值；晚于最后一个节点时保持最后值。
- `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。
- 时间非法或 BPM 时间轴结构非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartBpmError`；可能异常：`RizChartBpmError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(B)`；空间复杂度：`O(1)`
- 大参数提示：B 为 BPM 节点数；构建/查找时间轴。

**示例**

```python
from rizChartFunction import getBpmAt

print(getBpmAt(chart, 4.0))
print(getBpmAt(chart, 2.0, isRealTime=True))
```

### `getSecondsAt()`

**函数声明**

```python
getSecondsAt(chart: dict, tick: float, *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `tick` | `float` | 是 | - | tick，必须大于等于 `0.0` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定 tick 对应的绝对秒数。

**输入限制**

谱面必须在 `time=0.0` 处有一个 BPM 节点。

**具体实现**

晚于最后一个 BPM 节点时 继续按最后一个 BPM 节点计算。

**返回值**

返回 BPM 时间轴上 `tick` 对应的绝对秒数。

失败返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartBpmError`；可能异常：`RizChartBpmError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(B)`；空间复杂度：`O(B)`
- 大参数提示：构建 BPM 时间轴并换算。

**示例**

```python
from rizChartFunction import getSecondsAt

print(getSecondsAt(chart, 4.0))
```

### `getTickAt()`

**函数声明**

```python
getTickAt(chart: dict, seconds: float, *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `seconds` | `float` | 是 | - | 绝对秒数，必须大于等于 `0.0` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定绝对秒数对应的 tick。

**输入限制**

谱面必须在 `time=0.0` 处有一个 BPM 节点。

**具体实现**

晚于最后一个 BPM 节点时继续按最后一个 BPM 节点计算。

**返回值**

返回 BPM 时间轴上 `seconds` 对应的 tick，是 `getSecondsAt()` 的逆运算。

失败返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartBpmError`；可能异常：`RizChartBpmError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(B)`；空间复杂度：`O(B)`
- 大参数提示：构建 BPM 时间轴并换算。

**示例**

```python
from rizChartFunction import getTickAt

print(getTickAt(chart, 2.0))
```

## 画布与摄像机

### `getCanvasSpeedAt()`

**函数声明**

```python
getCanvasSpeedAt(chart: dict, index: int, time: float,
                 isRealTime: bool = False,
                 *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 画布索引，0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询画布在指定时间的流速。

**具体实现**

画布流速是**阶梯式突变**的，不在节点之间 插值。

**注意事项/细节**

`speedKeyPoints[].easeType` 固定为 0，也不参与查询。

- 正好命中节点时取该节点值；同一时间有多个节点时取最右侧节点。
- 节点之间保持左侧节点的值，直到下一个节点时间才切换。
- 早于第一个关键点或结构非法时返回 `None`；晚于最后一个关键点时保持最后值。
- `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。

**返回值**

返回画布在指定时间的流速值；时间或结构非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartCanvasError`；可能异常：`RizChartCanvasError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(log C)`；空间复杂度：`O(1)`
- 大参数提示：C 为画布流速关键点数。

**示例**

```python
from rizChartFunction import getCanvasSpeedAt

print(getCanvasSpeedAt(chart, 0, 4.0))
print(getCanvasSpeedAt(chart, 0, 2.0, isRealTime=True))
```

### `getCameraPositionAt()`

**函数声明**

```python
getCameraPositionAt(chart: dict, time: float,
                    isRealTime: bool = False,
                    *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询摄像机在指定时间的 x 位置。

**返回值**

返回摄像机在指定时间的 x 位置，按 `cameraMove.xPositionKeyPoints` 插值。

- 正好命中节点时取该节点值；同一时间有多个节点时取最右侧节点。
- 节点之间使用左侧节点的 `easeType` 插值。
- 早于第一个关键点或结构非法时返回 `None`；晚于最后一个关键点时保持最后值。
- `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(log C)`；空间复杂度：`O(1)`
- 大参数提示：C 为摄像机位置关键点数。

**示例**

```python
from rizChartFunction import getCameraPositionAt

print(getCameraPositionAt(chart, 4.0))
```

### `getCameraScaleAt()`

**函数声明**

```python
getCameraScaleAt(chart: dict, time: float,
                 isRealTime: bool = False,
                 *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询摄像机在指定时间的缩放倍率。

**返回值**

返回摄像机在指定时间的缩放倍率，按 `cameraMove.scaleKeyPoints` 插值。

- 正好命中节点时取该节点值；同一时间有多个节点时取最右侧节点。
- 节点之间使用左侧节点的 `easeType` 插值。
- 早于第一个关键点或结构非法时返回 `None`；晚于最后一个关键点时保持最后值。
- `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(log C)`；空间复杂度：`O(1)`
- 大参数提示：C 为摄像机缩放关键点数。

**示例**

```python
from rizChartFunction import getCameraScaleAt

print(getCameraScaleAt(chart, 4.0))
```

## 计算与搜索

### `getFloorPosition()`

**函数声明**

```python
getFloorPosition(chart: dict, time: float,
                 canvasindex: int | None = None,
                 isRealTime: bool = False,
                 *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `canvasindex` | `int \| None` | 否 | `None` | 画布索引；`None` 时查询 BPM |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数，否则是 tick |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询指定时间点的 floorPosition。

**注意事项/细节**

- `canvasindex=None`：返回 BPM 时间轴在 `time` 处的 `floorPosition`（绝对秒数）。
  `isRealTime=True` 时直接返回 `time`。
- 谱面必须在 `time=0.0` 处有一个 BPM 节点；缺少时返回 `None`。
- `canvasindex` 为整数：按 `canvasMoves[].index` 找到画布，并按
  `speedKeyPoints` 对**秒**积分计算该画布在 `time` 处的 `floorPosition`。
  `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。
- 查询点早于画布第一个 `speedKeyPoint` 时返回 `None`；晚于最后一个时按
  最后一段速度继续计算。

**返回值**

成功返回 `float`。

时间非法、谱面结构不合法或画布不存在时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartFloorPositionError`；可能异常：`RizChartFloorPositionError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(B + C)`；空间复杂度：`O(V)`
- 大参数提示：按 BPM 时间轴和画布流速计算。

**示例**

```python
from rizChartFunction import getFloorPosition, new

chart = new(100.0)

# tick 4 对应的绝对时间（秒）
print(getFloorPosition(chart, 4.0))  # 2.4

# tick 4 时画布 0 的高度
print(getFloorPosition(chart, 4.0, canvasindex=0))

# 实际 2.4 秒时画布 0 的高度
print(getFloorPosition(chart, 2.4, canvasindex=0, isRealTime=True))
```

### `getCanvasPositionAt()`

**函数声明**

```python
getCanvasPositionAt(chart: dict, time: float, index: int = -1,
                    isRealTime: bool = False,
                    *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `index` | `int` | 否 | `-1` | 画布索引，0 起，负数从末尾计算 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询画布在指定时间的中线绝对 x 坐标。

**返回值**

返回画布中线在 `time` 处的绝对 x 坐标，按 `xPositionKeyPoints` 的 `easeType` 插值。

- 查询时间晚于最后一个关键点时，保持最后一个节点的值
- 早于第一个关键点或结构非法时返回 `None`
- `easeType` 不在 0-18 时返回 `None`

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartCanvasError`；可能异常：`RizChartCanvasError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartStructureError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(log C)`；空间复杂度：`O(1)`
- 大参数提示：C 为画布位置关键点数。

**示例**

```python
from rizChartFunction import (
    new, addCanvasPosition, getCanvasPositionAt,
)

chart = new(100.0)
addCanvasPosition(chart, 0, 4.0, 1.0, 0)

print(getCanvasPositionAt(chart, 2.0, 0))        # 0.5
print(getCanvasPositionAt(chart, 2.4, 0, True))  # 2.4 秒 = tick 4，返回 1.0
```

### `getLinePosition()`

**函数声明**

```python
getLinePosition(chart: dict, index: int, time: float,
                isAbsolutePosition: bool = False,
                isRealTime: bool = False,
                *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 线索引（`lines` 数组），0 起，负数从末尾计算 |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0.0` |
| `isAbsolutePosition` | `bool` | 否 | `False` | 是否返回绝对坐标 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询引导线在指定时间的 x 坐标。

**注意事项/细节**

`isAbsolutePosition=True` 时返回绝对坐标，即相对坐标加上该时刻所在画布的
`getCanvasPositionAt()`。

- 查询时间早于首个节点或晚于末个节点时返回 `None`
- 查询时间正好落在节点上：若同一时间有多个节点，取**最右侧**节点；
  x 坐标相同时结果相同，不同时视为只有右侧节点
- 节点之间的 x 坐标按左侧节点的 `easeType` 插值
- 缓动类型不在 0-18 时返回 `None`

**返回值**

成功返回 x 坐标；`isAbsolutePosition=False` 时相对画布中线，
`isAbsolutePosition=True` 时为绝对坐标。时间越界、结构非法或缓动非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(log n)`；空间复杂度：`O(1)`
- 大参数提示：n 为目标线的节点数。

**示例**

```python
from rizChartFunction import getLinePosition

# 相对坐标
print(getLinePosition(chart, 0, 2.0))

# 绝对坐标（相对坐标 + 画布中线坐标）
print(getLinePosition(chart, 0, 2.0, isAbsolutePosition=True))
```

### `getLineByPoint()`

**函数声明**

```python
getLineByPoint(chart: dict, position: float | list | None = None,
               time: float | list | None = None,
               index: int | None = None,
               color: list | str | None = None,
               isAbsolutePosition: bool = False,
               isRealTime: bool = False,
               *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `position` | `float \| list \| None` | 否 | `None` | 节点 x；`None` 任意，`[a,b]` 表示闭区间 |
| `time` | `float \| list \| None` | 否 | `None` | 节点时间；`None` 任意，`[a,b]` 表示闭区间 |
| `index` | `int \| None` | 否 | `None` | 画布索引；`None` 表示所有画布 |
| `color` | `list \| str \| None` | 否 | `None` | 节点颜色，`None` 表示任意 |
| `isAbsolutePosition` | `bool` | 否 | `False` | 是否按绝对坐标查找 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按引导线节点位置查询节点所在的线。

**注意事项/细节**

- `position` 为单值时精确比较；为 `[a,b]` 时闭区间匹配
- `color` 支持 `#RRGGBB`、`#RRGGBBAA`、`RRGGBB`、`RRGGBBAA`、
  `[r,g,b]`、`[r,g,b,a]`；未提供 alpha 时视为 `255`，按 RGBA 精确比较
- `isAbsolutePosition=True` 时，对每个候选节点用它**自身的 time** 查询
  所在画布的 `getCanvasPositionAt()`，再比较
  `position - 画布x == xPosition`
- `index` 支持负数（从末尾计算）

**返回值**

返回 `[[lineindex, pointindex], ...]`；没有符合条件的节点时返回 `[]`。
只有参数非法、画布索引非法或谱面结构损坏等查找失败情况返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`4/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：扫描全部线节点；候选越多越慢。

**示例**

```python
from rizChartFunction import new, getLineByPoint

# 查找画布 0 上、时间 4、x 为 1.0 的节点
result = getLineByPoint(chart, position=1.0, time=4.0, index=0)

# 时间 4-8、x 在 1.0-3.0 之间的白色节点
result = getLineByPoint(
    chart,
    position=[1.0, 3.0],
    time=[4.0, 8.0],
    color="#FFFFFF",
)
```

### `getLineByNote()`

**函数声明**

```python
getLineByNote(chart: dict, position: float | list | None = None,
              time: float | list | None = None,
              type: int | str | None = None,
              isAbsolutePosition: bool = False,
              isRealTime: bool = False,
              *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `position` | `float \| list \| None` | 否 | `None` | Note 的 x；`None` 任意，`[a,b]` 表示闭区间 |
| `time` | `float \| list \| None` | 否 | `None` | Note 时间；`None` 任意，`[a,b]` 表示闭区间 |
| `type` | `int \| str \| None` | 否 | `None` | `0`/`"tap"`、`1`/`"drag"`、`2`/`"hold"`；`None` 任意 |
| `isAbsolutePosition` | `bool` | 否 | `False` | 是否按绝对坐标查找 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 是实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

按 Note 的位置查询 Note 所在的线。

**具体实现**

Note 本身没有 `xPosition`，因此先用时间筛选 Note，再调用 `getLinePosition()` 计算该 Note 时刻的线的 x 坐标并与 `position` 比较。

Hold 只使用头部时间。

**注意事项/细节**

类型字符串不区分大小写。

**返回值**

返回 `[[lineindex, noteindex], ...]`；没有匹配的 Note 时返回 `[]`。
只有参数非法、Note/线结构损坏等查找失败情况返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`5/10`
- 时间复杂度：`O(V)`；空间复杂度：`O(n)`
- 大参数提示：扫描全部 Note 并匹配所属线。

**示例**

```python
from rizChartFunction import getLineByNote

# 所有 Tap
result = getLineByNote(chart, type="tap")

# 时间 10-20、x 在 0-1 之间的 Hold
result = getLineByNote(
    chart,
    position=[0.0, 1.0],
    time=[10.0, 20.0],
    type=2,
)
```

### `getLineTimeRange()`

**函数声明**

```python
getLineTimeRange(chart: dict, lineindex: int = -1,
                 isRealTime: bool = False,
                 *, isReturnException: bool = False) -> list | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时返回实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询引导线首节点到尾节点的时间范围。

**具体实现**

`isRealTime=True` 时使用 BPM 时间轴把两个 tick 换算成秒。

**返回值**

返回引导线首节点到末节点的时间范围：

```python
[first_time, last_time]
```

线不存在、 线节点结构非法或秒数换算失败时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：只取线的首尾节点。

**示例**

```python
from rizChartFunction import getLineTimeRange

print(getLineTimeRange(chart, 0))
print(getLineTimeRange(chart, 0, isRealTime=True))
```

### `getNotePosition()`

**函数声明**

```python
getNotePosition(chart: dict, lineindex: int = -1,
                noteindex: int = -1,
                isAbsolutePosition: bool = False,
                *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `noteindex` | `int` | 否 | `-1` | Note 索引，0 起，负数从末尾计算 |
| `isAbsolutePosition` | `bool` | 否 | `False` | 是否返回绝对 x 坐标 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询 Note 头部所在位置的线 x 坐标。

**具体实现**

Hold 只使用头部时间。

**注意事项/细节**

`isAbsolutePosition=True` 时加上该时刻所在画布的 `getCanvasPositionAt()`。

**返回值**

返回 Note 头部时刻线的 x 坐标。

索引不存在、Note 结构非法或时间越界时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(log n)`；空间复杂度：`O(1)`
- 大参数提示：定位 Note 所在线段。

**示例**

```python
from rizChartFunction import getNotePosition

print(getNotePosition(chart, 0, 0))
print(getNotePosition(chart, 0, 0, isAbsolutePosition=True))
```

### `getNoteCanvas()`

**函数声明**

```python
getNoteCanvas(chart: dict, lineindex: int = -1,
              noteindex: int = -1,
              isHoldTail: bool = False,
              *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `lineindex` | `int` | 否 | `-1` | 线索引，0 起，负数从末尾计算 |
| `noteindex` | `int` | 否 | `-1` | Note 索引，0 起，负数从末尾计算 |
| `isHoldTail` | `bool` | 否 | `False` | 是否返回 Hold 尾部绑定的画布 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

查询 Note 对应的画布索引。

**返回值**

返回 Note 对应的画布索引。

- 默认返回 Note 头部所在画布，按头部规则从 `linePoints` 推导。
- `isHoldTail=True` 且 Note 是 Hold 时，返回其
  `otherInformations[1]` 中记录的尾部画布。
- Note 不是 Hold 时忽略 `isHoldTail`，仍返回头部画布。
- 索引不存在、Note 结构非法、Hold 尾部画布无效或画布不存在时返回
  `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartReferenceError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartEaseError`, `RizChartColorError`, `RizChartThemeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(log n)`；空间复杂度：`O(1)`
- 大参数提示：定位 Note 所在线段。

**示例**

```python
from rizChartFunction import getNoteCanvas

print(getNoteCanvas(chart, 0, 0))
print(getNoteCanvas(chart, 0, 0, isHoldTail=True))
```

## 视觉比例

这一组函数计算画布流速与游戏流速下的 X/Y 视觉比例。

- X 表示 `floorPosition`；
- Y 表示 tick；
- 默认画布流速视为恒定；
- `gamespeed` 必须大于 `0`，`value` 必须大于 `0`。

### `getXYRatio()`

> **版本提示**：本函数自 `0.2.0` 起提供；在 `0.2.0` 之前的版本中不可用。

**函数声明**

```python
getXYRatio(bpm: float, canvasspeed: float, gamespeed: float,
            value: float = 1.0, type: str = "X",
            *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `bpm` | `float` | 是 | - | 谱面实际 BPM，必须大于 `0` |
| `canvasspeed` | `float` | 是 | - | 画布流速；允许为 `0`，但相应除法会按规则返回 `NaN` |
| `gamespeed` | `float` | 是 | - | 玩家设置的全局流速，必须大于 `0` |
| `value` | `float` | 否 | `1.0` | 基础值，必须大于 `0` |
| `type` | `str` | 否 | `"X"` | 基础值类型；只接受 `"X"` 或 `"Y"` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

计算基础值下另一个单位的视觉比例：

- `type="X"`：返回 `value` 个 X 对应的 Y；
- `type="Y"`：返回 `value` 个 Y 对应的 X。

计算方式：

```text
K = 6 + 7 * (gamespeed - 1) / 9

value X = value * 5.625 * bpm / (60 * canvasspeed * K) Y
value Y = value * 60 * canvasspeed * K / (5.625 * bpm) X
```

**返回与失败**

- 成功返回对应的 `float`。
- `type="X"` 且 `canvasspeed == 0` 时发生除零，返回 `NaN`。
- `type="Y"` 且 `canvasspeed == 0` 时按公式返回 `0.0`。
- `bpm <= 0`、`gamespeed <= 0`、`value <= 0`、`type` 不是 `"X"` / `"Y"`、参数非有限数或类型非法时返回 `None`。
- 不修改任何谱面。

**异常**

`isReturnException=True` 时，上述失败不返回失败值。除零 `NaN` 抛 `RizChartDivisionByZeroError`；参数、BPM 或画布失败按具体异常抛出。可能异常：`RizChartValueError`, `RizChartDivisionByZeroError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：纯标量运算，与输入数值大小无关。

**示例**

```python
from rizChartFunction import getXYRatio

print(getXYRatio(180.0, 1.0, 1.0))                 # 2.8125
print(getXYRatio(180.0, 1.0, 1.0, type="Y"))       # 0.35555555555555557
print(getXYRatio(180.0, 0.0, 1.0, type="X"))       # nan
print(getXYRatio(180.0, 0.0, 1.0, type="Y"))       # 0.0
```

### `getXYRatioByChart()`

> **版本提示**：本函数自 `0.2.0` 起提供；在 `0.2.0` 之前的版本中不可用。

**函数声明**

```python
getXYRatioByChart(chart: dict, index: int, time: float,
                  gamespeed: float, value: float = 1.0,
                  type: str = "X",
                  isRealTime: bool = False,
                  *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `index` | `int` | 是 | - | 画布索引；支持负数从末尾计算 |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 0 |
| `gamespeed` | `float` | 是 | - | 玩家设置的全局流速，必须大于 0 |
| `value` | `float` | 否 | `1.0` | 基础值，必须大于 0 |
| `type` | `str` | 否 | `"X"` | 基础值类型；只接受 `"X"` 或 `"Y"` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 为实际秒数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值；批量函数会忽略 `isFailAddAllowed` 并强制原子回退。 |

**用途**

先从谱面指定时间查询实际 BPM（基准 BPM × 当前倍率），再从指定画布、指定时间
查询画布流速，最后按与 [`getXYRatio()`](#getxyrratio) 相同的公式计算 X/Y
视觉比例。画布流速按恒定阶梯值查询，不做插值。

**返回与失败**

- 成功返回对应的 `float`。
- 画布索引非法、时间非法、BPM 查询失败或画布流速查询失败时返回 `None`。
- 画布流速为 `0` 时与 `getXYRatio()` 相同：`type="X"` 返回 `NaN`，`type="Y"` 返回 `0.0`。
- `gamespeed` / `value` / `type` / `isRealTime` 非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值。除零 `NaN` 抛 `RizChartDivisionByZeroError`；参数、BPM 或画布失败按具体异常抛出。可能异常：`RizChartValueError`, `RizChartBpmError`, `RizChartCanvasError`, `RizChartDivisionByZeroError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`2/10`
- 时间复杂度：`O(B + log C)`；空间复杂度：`O(B)`
- 大参数提示：B 为 BPM 节点数，C 为画布流速关键点数；主要成本是 BPM 时间轴和画布流速定位，公式本身为常数时间。

**示例**

```python
from rizChartFunction import getXYRatioByChart, new

chart = new(180.0)
print(getXYRatioByChart(chart, 0, 0.0, 1.0))
print(getXYRatioByChart(chart, 0, 0.0, 1.0, type="Y"))
```

## 视觉边界

这一组函数计算游戏区域的可视 X/Y 边界。

X 边界：

- `type="solidLeft"`：实际左边界
- `type="shadeLeft"`：遮罩左边界
- `type="solidRight"`：实际右边界
- `type="shadeRight"`：遮罩右边界

Y 边界函数位于本节后半部分，返回可视区域上下边界相对当前时刻的距离。

### `getXBorder()`

**函数声明**

```python
getXBorder(canvasposition: float = 0.0,
           cameraposition: float = 0.0,
           camerascale: float = 1.0,
           type: str = "solidLeft",
           isAbsolutePosition: bool = False,
           *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `canvasposition` | `float` | 否 | `0.0` | 画布中心 X 坐标；`isAbsolutePosition=True` 时忽略 |
| `cameraposition` | `float` | 否 | `0.0` | 摄像机中心 X 坐标 |
| `camerascale` | `float` | 否 | `1.0` | 摄像机缩放倍率，必须大于 `0` |
| `type` | `str` | 否 | `"solidLeft"` | 边界类型：`solidLeft` / `shadeLeft` / `solidRight` / `shadeRight` |
| `isAbsolutePosition` | `bool` | 否 | `False` | `True` 时结果为绝对坐标，不使用画布位置项 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

在不查询谱面的情况下，直接根据画布中心、摄像机中心和缩放计算可视 X 边界。

**计算方式**

```text
center = cameraposition - canvasposition
half = camerascale / 2
shade = camerascale / 5.625

solidLeft  = center - half
shadeLeft  = center - half + shade
solidRight = center + half
shadeRight = center + half - shade
```

`isAbsolutePosition=True` 时令 `canvasposition = 0`，即去掉公式中的画布位置项。

**返回值**

成功返回对应边界坐标 `float`；`camerascale <= 0`、参数非有限数、类型非法或坐标参数非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartValueError`；可能异常：`RizChartValueError`, `RizChartTypeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：纯标量计算。

**示例**

```python
from rizChartFunction import getXBorder

print(getXBorder(1.0, 2.0, 4.0, "solidLeft"))   # -1.0
print(getXBorder(1.0, 2.0, 4.0, "solidRight"))  # 3.0
print(getXBorder(1.0, 2.0, 4.0, "solidLeft", True))  # 0.0
```

### `getXBorderByChart()`

**函数声明**

```python
getXBorderByChart(chart: dict, time: float, index: int = 0,
                  type: str = "solidLeft",
                  isRealTime: bool = False,
                  isAbsolutePosition: bool = False,
                  *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0` |
| `index` | `int` | 否 | `0` | 画布索引；支持负数，`isAbsolutePosition=True` 时忽略 |
| `type` | `str` | 否 | `"solidLeft"` | 边界类型：`solidLeft` / `shadeLeft` / `solidRight` / `shadeRight` |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 为实际秒数 |
| `isAbsolutePosition` | `bool` | 否 | `False` | `True` 时结果为绝对坐标，不使用画布位置项 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

查询指定画布和指定时间点的可视 X 边界。

**计算方式**

- `canvasposition` 使用 `getCanvasPositionAt()` 按画布位置关键点和缓动插值；
- `cameraposition` 使用 `getCameraPositionAt()` 按摄像机位置关键点和缓动插值；
- `camerascale` 使用 `getCameraScaleAt()` 按摄像机缩放关键点和缓动插值；
- 三项都取同一查询时间后，套用 `getXBorder()` 的公式。
- `isRealTime=True` 时三项查询都按实际秒数换算 tick。
- `isAbsolutePosition=True` 时忽略 `index`，并在公式中令画布位置项为 `0`。

**返回值**

成功返回对应边界坐标 `float`；画布索引、时间、摄像机位置、摄像机缩放、边界类型或谱面结构非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartStructureError`；可能异常：`RizChartStructureError`, `RizChartTypeError`, `RizChartIndexError`, `RizChartValueError`, `RizChartTimeError`, `RizChartBpmError`, `RizChartCanvasError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`1/10`
- 时间复杂度：`O(log C + log K)`；空间复杂度：`O(1)`
- 大参数提示：C、K 分别为画布位置/摄像机位置与缩放关键点数；实际成本是三次按时间插值查询。

**示例**

```python
from rizChartFunction import getXBorderByChart, new

chart = new(180.0)
print(getXBorderByChart(chart, 0.0))                 # -0.5
print(getXBorderByChart(chart, 0.0, type="solidRight"))  # 0.5
print(getXBorderByChart(chart, 0.0, isAbsolutePosition=True))
```

**Y 边界**

Y 边界系数：

| `type` | 系数 |
| --- | --- |
| `"solidTop"` | `6.5` |
| `"shadeTop"` | `5.5` |
| `"solidLineBottom"` | `-0.5` |
| `"shadeLineBottom"` | `0.5` |
| `"solidBottom"` | `-1.5` |
| `"shadeBottom"` | `-0.5` |

### `getYBorder()`

**函数声明**

```python
getYBorder(bpm: float, canvasspeed: float, gamespeed: float,
           type: str = "solidTop",
           isReturnRealTime: bool = False,
           camerascale: float = 1.0,
           *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `bpm` | `float` | 是 | - | 谱面实际 BPM，必须大于 `0` |
| `canvasspeed` | `float` | 是 | - | 画布流速；允许为 `0`，此时返回 `NaN` |
| `gamespeed` | `float` | 是 | - | 玩家设置的全局流速，必须大于 `0` |
| `type` | `str` | 否 | `"solidTop"` | 边界类型，见上表 |
| `isReturnRealTime` | `bool` | 否 | `False` | `True` 时返回实际秒数，否则返回 tick 数 |
| `camerascale` | `float` | 否 | `1.0` | 摄像机缩放比例，必须大于 `0`；实际 W 会乘以该值 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

在 BPM、画布流速和游戏流速恒定的情况下，直接计算可视 Y 边界。

**计算方式**

```text
K = 6 + 7 * (gamespeed - 1) / 9
目标W = bpm / (60 * canvasspeed * K)
实际W = 目标W * camerascale
边界 = 系数 * 实际W
```

`isReturnRealTime=True` 时，再把 tick 数按当前 BPM 换算为秒：

```text
秒数 = tick数 * 60 / bpm
```

**返回值**

成功返回 `float` tick 数或秒数；`canvasspeed=0` 返回 `NaN`；`bpm <= 0`、`gamespeed <= 0`、`camerascale <= 0`、`type` 非法或参数非有限数时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。除零 `NaN` 抛 `RizChartDivisionByZeroError`；参数错误抛 `RizChartValueError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：纯标量计算。

**示例**

```python
from rizChartFunction import getYBorder

print(getYBorder(180.0, 1.0, 1.0, "solidTop"))          # 3.25
print(getYBorder(180.0, 1.0, 1.0, "solidBottom"))       # -0.75
print(getYBorder(180.0, 1.0, 1.0, "solidTop", True))    # 1.0833333333333333 秒
print(getYBorder(180.0, 1.0, 1.0, "solidTop", False, 2.0))  # 6.5
```

### `getYBorderByChart()`

**函数声明**

```python
getYBorderByChart(chart: dict, time: float, index: int,
                  gamespeed: float,
                  type: str = "solidTop",
                  isRealTime: bool = False,
                  isReturnRealTime: bool = False,
                  *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |
| `time` | `float` | 是 | - | 查询时间点，必须大于等于 `0` |
| `index` | `int` | 是 | - | 画布索引 |
| `gamespeed` | `float` | 是 | - | 玩家设置的全局流速，必须大于 `0` |
| `type` | `str` | 否 | `"solidTop"` | 边界类型，见上表 |
| `isRealTime` | `bool` | 否 | `False` | `True` 时 `time` 为实际秒数 |
| `isReturnRealTime` | `bool` | 否 | `False` | `True` 时返回实际秒数，否则返回 tick 数 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

查询谱面中 BPM、画布流速随时间的实际变化，并使用查询时刻的摄像机缩放，计算可视 Y 边界。

**分段积分算法**

从一个查询 tick 开始，向目标边界方向逐段遍历：

1. 将所有 BPM 节点时间和画布流速关键点时间合并为分段边界。
2. 每一段内 BPM、画布流速视为常数。
3. 查询时刻的摄像机缩放由 `getCameraScaleAt()` 获取，并作为固定比例使用。
4. 该段实际 W：
   ```text
   目标W = bpm / (60 * canvasspeed * K)
   实际W = 目标W * camerascale
   ```
5. 该段包含的 W 数：
   ```text
   段W数 = 段tick长度 / 实际W
   ```
6. 从内向外累加各段的 W 数，直到达到目标边界系数
   （6.5、5.5、0.5、1.5 等）。
7. 最后一段按比例截断，返回累计 tick 距离。

`isReturnRealTime=True` 时，对经过的各段再按该段实际 BPM 累加：

```text
秒数 += 段tick长度 * 60 / bpm
```

**返回值**

成功返回 `float` tick 数或秒数；`canvas speed=0` 导致除零时返回 `NaN`；参数、谱面结构、BPM 时间轴、摄像机缩放、画布或索引非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。除零 `NaN` 抛 `RizChartDivisionByZeroError`；画布/BPM/结构错误按具体异常抛出。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`3/10`
- 时间复杂度：`O(E log E)`；空间复杂度：`O(E)`
- 大参数提示：E 为 BPM 节点数与画布流速关键点数之和；分段越多越慢。摄像机缩放只在查询时刻获取一次。

**示例**

```python
from rizChartFunction import getYBorderByChart, new

chart = new(180.0)
print(getYBorderByChart(chart, 5.0, 0, 1.0, "solidTop"))  # 3.25
print(getYBorderByChart(chart, 5.0, 0, 1.0, "solidTop", isReturnRealTime=True))
```

## 游戏区域与线宽

### `getGameScale()`

**函数声明**

```python
getGameScale(Xwidth: float, Ywidth: float,
             isPCVersion: bool = False,
             *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `Xwidth` | `float` | 是 | - | 屏幕 X 宽度，必须大于 `0` |
| `Ywidth` | `float` | 是 | - | 屏幕 Y 宽度，必须大于 `0` |
| `isPCVersion` | `bool` | 否 | `False` | 是否使用 PC 版缩放规则 |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

根据屏幕宽高比计算游戏区域缩放比例。

**计算方式**

```text
C = Xwidth / Ywidth
Sx = C * 16 / 9, C <= 18/29
   = 32/29,      C > 18/29 或 isPCVersion=True

Sc = C * 9 / 16, C <= 16/9 且 isPCVersion=True
   = 1,          C >= 16/9 且 isPCVersion=True
```

- 移动端返回 `Sx`。
- PC 端返回 `Sx * Sc`，即 `32Sc/29`。

**返回值**

成功返回 `float`；`Xwidth` / `Ywidth` 非正数或非有限数、`isPCVersion` 不是 bool 时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartValueError`；可能异常：`RizChartValueError`, `RizChartTypeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：纯标量计算。

**示例**

```python
from rizChartFunction import getGameScale

print(getGameScale(16, 9))          # 32/29
print(getGameScale(16, 9, True))    # 32/29
print(getGameScale(1, 1, True))     # 32/29 * 9/16
```

### `getLineWidth()`

**函数声明**

```python
getLineWidth(gamescale: float = 1.0,
             *, isReturnException: bool = False) -> float | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `gamescale` | `float` | 否 | `1.0` | 游戏区域缩放比例，必须大于 `0` |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

计算引导线宽，单位为 xPosition。

**计算方式**

```text
lineWidth = 1 / (125 * gamescale)
```

**返回值**

成功返回 `float`；`gamescale <= 0`、非有限数或类型非法时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartValueError`；可能异常：`RizChartValueError`, `RizChartTypeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：纯标量计算。

**示例**

```python
from rizChartFunction import getLineWidth

print(getLineWidth())    # 0.008
print(getLineWidth(2))   # 0.004
```

## 判定环半径

### `getRingRadius()`

**函数声明**

```python
getRingRadius() -> float
```

**参数**

无。

**用途**

查询判定环半径，单位为 `xPosition`。该值是固定的游戏视觉常量，不依赖谱面或当前画布。

**返回值**

始终返回 `float`，固定为 `1 / 18`，约 `0.05555555555555555`。

**异常**

无失败路径，因此不提供 `isReturnException`，也不会抛出异常。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(1)`；空间复杂度：`O(1)`
- 大参数提示：无参数、无扫描，直接返回常量。

**示例**

```python
from rizChartFunction import getRingRadius

print(getRingRadius())  # 0.05555555555555555
```

## 遮罩透明度

### `getShadeOpacity()`

**函数声明**

```python
getShadeOpacity(ratio: float,
                *, isReturnException: bool = False) -> int | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `ratio` | `float` | 是 | - | 从底部到顶部的相对比例，必须在 `0.0` 到 `1.0` 之间（包含两端） |
| `isReturnException` | `bool` | 否 | `False` | `True` 时失败改为抛出异常，不再返回失败值 |

**用途**

查询 `rizline_fade_side` 底部到顶部遮罩在相对比例处的透明度。

**数据来源**

数据来自底部到顶部遮罩透明度表 `fade_opacity_bottom_to_top.csv`。

内置数据位于：

```text
src/rizChartFunction/_shade_opacity_data.py
```

`SHADE_OPACITY_ALPHA[row]` 对应 CSV 中
`row_from_bottom_0based=row` 的 `round(alpha_mean_0_255)`。

**选取规则**

对每一个 `row`：

```text
row / 511 <= ratio < (row + 1) / 511
```

`ratio=1.0` 时取最后一行 `row=510`。返回该行的
`round(alpha_mean_0_255)`，即 `0..255` 的整数。

**返回值**

成功返回 `int`；`ratio` 不是有限数、类型非法或不在 `[0.0, 1.0]` 内时返回 `None`。

**异常**

`isReturnException=True` 时，上述失败不返回失败值，而是抛出 `RizChartError` 子类。默认异常为 `RizChartValueError`；可能异常：`RizChartValueError`, `RizChartTypeError`。完整规则见 [EXCEPTIONS.md](EXCEPTIONS.md)。

**性能**

- 相对开销：`0/10`
- 时间复杂度：`O(log 511)`，可视为 `O(1)`；空间复杂度：`O(1)`
- 大参数提示：内置表固定为 511 行，查询成本与输入无关。

**示例**

```python
from rizChartFunction import getShadeOpacity

print(getShadeOpacity(0.0))    # 255
print(getShadeOpacity(0.5))    # 该比例所在行的 alpha
print(getShadeOpacity(1.0))    # 0
```
