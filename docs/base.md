# base 模块函数说明

[← 返回总览](README.md)

`base.py` 负责谱面的创建、读取、校验、导出与刷新。

## 目录

- [`new()`](#new)
- [`load()`](#load)
- [`export()`](#export)
- [`check()`](#check)
- [`refresh()`](#refresh)

## 函数说明

### `new()`

**函数声明**

```python
new(basebpm: float, delay: int = 0, version: int = 0) -> dict
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `basebpm` | `float` | 是 | - | 基准 BPM |
| `delay` | `int` | 否 | `0` | 谱面延迟，单位 ms，写入 `chartDelayMs` |
| `version` | `int` | 否 | `0` | 文件版本，写入 `fileVersion` |

**用途**

创建一份最小可用的空谱面。

**输入限制**

本函数不做显式校验：`basebpm` 会经 `float()` 转换，`delay` / `version`
原样写入。为保证后续 `check()` / `export()` 通过，建议使用正数 `basebpm`
和非负整数 `delay` / `version`。

**具体实现**

使用标准根结构和默认主题、画布、摄像机、BPM 节点初始化谱面。

**返回值**

成功返回谱面 `dict`，可直接交给 `json.dump()`、`export()` 或各类编辑函数。

根结构包含：

```text
fileVersion       int
chartDelayMs      int
themes            list   默认两个白色主题，每个 colorsList 含 3 个颜色
challengeTimes    list   默认含一个空的 Riztime 占位
bPM               float
bpmShifts         list   默认含 time=0.0, value=1.0 的节点
lines             list
canvasMoves       list   默认含 index=0 的画布
cameraMove        dict   默认含缩放与横向移动节点
```

**示例**

```python
from rizChartFunction import new

chart = new(175.0)
print(chart["bPM"])  # 175.0
```

### `load()`

**函数声明**

```python
load(filename: str, basebpm: float | None = None) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `filename` | `str` | 是 | - | 谱面文件路径（UTF-8 / UTF-8 BOM） |
| `basebpm` | `float \| None` | 否 | `None` | 指定基准 BPM；不为 `None` 时覆盖文件中的 `bPM` |

**用途**

读取谱面文件，清洗并规范化为本库标准结构。

**输入限制**

- 文件必须是可读取的 JSON，根节点必须是对象。
- 文件缺少 `bPM` 时必须提供正数 `basebpm`。
- 文件 `bPM <= 0` 时必须提供正数 `basebpm` 覆盖。

**具体实现**

1. 递归删除标准结构之外的键，删除类型不正确的值。
2. 补齐根结构第一层缺失的键，嵌套结构不主动补全。
3. 调整主题与 `challengeTimes` 数量，保证
   `len(themes) == len(challengeTimes) + 1`。
4. 兼容旧键名 `bPMShifts`，统一为 `bpmShifts`。
5. 补 `chartDelayMs=0`。
6. 执行 floorPosition、画布、时间、音符等规范化。

详细的 12 类规范化规则见 [TECHNICAL.md](TECHNICAL.md) 与源码。

**注意事项/细节**

- `bool` 不会被当作数字接受。
- 官方谱面的 `songsName`、`offset` 会被删除。
- `floorPosition` 误差阈值为 `1e-2`。
- 无法修复的严重结构问题会导致整份谱面读取失败。

**返回值**

- 成功：规范化后的谱面 `dict`。
- 文件不存在、读取失败、JSON 非法、根节点不是对象：`None`。
- 缺少 `bPM` 且未提供 `basebpm`：`None`。
- `bPM <= 0` 且未提供正数 `basebpm`：`None`。

**示例**

```python
from rizChartFunction import load

chart = load(r"E:\RizChartTool\input\20260109\Chart_IN")
if chart is None:
    raise RuntimeError("谱面读取失败")

chart = load(r"E:\RizChartTool\input\20260109\Chart_IN", basebpm=175.0)
```

### `export()`

**函数声明**

```python
export(chartlist: dict, filename: str) -> bool
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chartlist` | `dict` | 是 | - | 谱面 dict |
| `filename` | `str` | 是 | - | 导出路径 |

**用途**

校验谱面并按原始结构导出为紧凑 JSON 文件。

**输入限制**

- `chartlist` 必须已经符合标准格式；`export()` 不会像 `load()` 那样修复它。
- `check(chartlist)` 必须返回 `None`。
- 目标路径必须可写。

**具体实现**

1. 调用 `check()`，发现问题立即返回 `False`。
2. 使用与 `load()` 相同的清洗规则做只读校验；清洗结果必须与输入完全一致。
3. 以 UTF-8、紧凑 JSON 写出，键顺序保持不变。

**注意事项/细节**

- 导出不会修改输入字典。
- `load()` 能自动修复的问题（负数时间、越界颜色、重复画布索引、错误
  `floorPosition` 等）都会导致 `export()` 拒绝导出。
- `songsName`、`offset` 等官方专有字段不允许导出。

**返回值**

成功返回 `True`；结构非法、存在多余/缺失键、值越界、引用错误、路径不可写
或 JSON 序列化失败时返回 `False`。

**示例**

```python
from rizChartFunction import new, export

chart = new(175.0)
if not export(chart, r"E:\RizChartTool\output\chart.json"):
    raise RuntimeError("导出失败")
```

### `check()`

**函数声明**

```python
check(chart: dict) -> dict | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict |

**用途**

只读检查谱面是否符合标准格式。

**输入限制**

无额外输入限制；任意对象都可以传入，但非 `dict` 会报告结构问题。

**具体实现**

按 `load()` / `export()` 使用的 schema、长度、值、引用和
`floorPosition` 规则检查，不修改谱面。

**注意事项/细节**

返回对象包含三类路径：

- `unexpectedParts`：不允许的键/索引；
- `missingParts`：缺少的键/索引；
- `errorValues`：类型错误、值越界、引用错误、`floorPosition` 错误等。

路径只标注到最顶层的非法项。若 BPM/画布结构导致无法计算
`floorPosition`，会跳过这部分检查。`floorPosition` 误差阈值为 `1e-2`。

**返回值**

没有问题返回 `None`；发现问题返回：

```python
{
    "unexpectedParts": [["example"]],
    "missingParts": [["canvasMoves"]],
    "errorValues": [["themes", 0, "colorsList", 2, "r"]],
}
```

**示例**

```python
from rizChartFunction import check

issues = check(chart)
if issues is not None:
    print(issues["errorValues"])
```

### `refresh()`

**函数声明**

```python
refresh(chart: dict, mode: str = "all", type: str = "all",
        startindex: int = 0, endindex: int = -1,
        startlineindex: int = 0, endlineindex: int = -1,
        isOnlyRefreshNaN: bool = False) -> bool | None
```

**参数**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `chart` | `dict` | 是 | - | 谱面 dict，原地修改 |
| `mode` | `str` | 否 | `"all"` | 重置模式：`"all"` / `"floorPosition"` / `"order"` |
| `type` | `str` | 否 | `"all"` | 重置类型，见下表 |
| `startindex` | `int` | 否 | `0` | 起始节点索引 |
| `endindex` | `int` | 否 | `-1` | 结束节点索引 |
| `startlineindex` | `int` | 否 | `0` | 起始线索引，仅 `linePoints` / `notes` / `judgeRingColor` / `lineColor` 使用 |
| `endlineindex` | `int` | 否 | `-1` | 结束线索引，仅上述四种类型使用 |
| `isOnlyRefreshNaN` | `bool` | 否 | `False` | 只重算当前值为 `NaN` 的 `floorPosition`；`mode="order"` 时无效 |

`mode` 取值：

| 值 | 说明 |
| --- | --- |
| `"all"` | 重算 `floorPosition` 并调整顺序 |
| `"floorPosition"` | 只重算 `floorPosition`，不排序 |
| `"order"` | 只排序，不重算高度 |

`type` 取值：

| 值 | 说明 | 索引范围 |
| --- | --- | --- |
| *`"all"` | 整个谱面 | 忽略全部索引 |
| `"bpmShifts"` | BPM 变化节点 | `startindex` / `endindex` |
| `"lines"` | 选中引导线的全部子数组 | `startindex` / `endindex` 选择线 |
| #`"linePoints"` | 线节点 | `startlineindex` / `endlineindex` 选线，`startindex` / `endindex` 选节点 |
| #`"notes"` | Note | 同上 |
| #`"judgeRingColor"` | 判定环颜色节点 | 同上 |
| #`"lineColor"` | 线色覆盖节点 | 同上 |
| `"canvas"` | 选中画布的横向移动与流速数组 | `startindex` / `endindex` 选择画布 |
| `"canvasPosition"` | 画布横向移动节点 | `startindex` / `endindex` 为每个画布内的节点索引 |
| `"canvasSpeed"` | 画布速度节点 | `startindex` / `endindex` 为每个画布内的节点索引 |
| *`"camera"` | 摄像机全部关键点 | 忽略全部索引 |
| `"cameraPosition"` | 摄像机横向移动节点 | `startindex` / `endindex` |
| `"cameraScale"` | 摄像机缩放节点 | `startindex` / `endindex` |

带星号说明的类型（`"all"`、`"camera"`）忽略 `startindex` / `endindex`；
带井号说明的类型（`linePoints` / `notes` / `judgeRingColor` / `lineColor`）
同时使用线索引范围与节点索引范围。

**用途**

按指定范围重排时间数组，并按需重算 `floorPosition`。

**输入限制**

- `mode` / `type` 必须是上表中的值。
- 范围索引必须是 `int`。负数按 Python 习惯从末尾计算。
- 允许索引越界或交集为空：越界部分忽略，交集为空时不执行搜索。
- `mode="floorPosition"` 要求数据顺序已满足高度计算条件；不会自动排序。
- `mode="all"` / `"floorPosition"` 需要 BPM、画布等依赖结构可计算。

**具体实现**

1. 根据 `type` 选择对象，根据索引范围筛选。
2. `mode="all"` / `"order"` 时，对选中范围按 `time` 稳定排序；相同时间保持原顺序。
3. `mode="all"` / `"floorPosition"` 时计算选中对象的 `floorPosition`：
   - BPM 节点：绝对秒数。
   - 画布流速、线节点、Note 头部：画布高度。
   - Hold 尾部：尾部画布与高度。
   - 画布横向移动、摄像机节点：固定为 `0.0`。
4. 先完成所有计算，再写回高度；计算失败时恢复已调整的顺序。
5. `isOnlyRefreshNaN=True` 时，只写回当前值为 `NaN` 的选中高度；非 `NaN`
   值保持不变。

**注意事项/细节**

- 索引范围只影响选中元素；未选中的元素不会被排序或重算。
- 带节点范围时只排序选中的那一段；`lines` / `canvas` 选择父对象后排序其完整子数组。
- `lines` 与 `canvasMoves` 本身不按时间重排。
- 星号类型忽略索引；井号类型的行索引与节点索引是两组独立范围。
- `mode="order"` 时会忽略 `isOnlyRefreshNaN`。
- 比较 `floorPosition` 使用精确值；有顺序或高度变化返回 `True`。
- 失败时返回 `None`，并保证谱面保持调用前的状态。

**返回值**

- 选中范围内有顺序或高度变化：修改谱面并返回 `True`。
- 选中范围内无变化：返回 `False`。
- 参数非法、结构非法或无法重算：返回 `None`。

**示例**

```python
from rizChartFunction import refresh

# 全谱重排并重算
refresh(chart)

# 只重算全谱高度，不改变顺序
refresh(chart, "floorPosition")

# 只重排全谱顺序
refresh(chart, "order")

# 所有线的 linePoints[5] 至 linePoints[9]：
# 只修复其中为 NaN 的高度，并调整这一段顺序
refresh(chart, "all", "linePoints", 5, 9, 0, -1, True)

# 只重算第 0 条线的 notes
refresh(chart, "floorPosition", "notes", 0, -1, 0, 0)
```
