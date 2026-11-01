# rizChartFunction

[← 返回项目入口](../README.md)

用于创建、读取、编辑、校验、查询和导出 Rizline 谱面（JSON）的 Python 库。

本文档是总览。函数文档拆分为五个文件：

| 文档 | 内容 |
| --- | --- |
| [README.md](README.md) | 总览、安装、快速开始、全局约定 |
| [base.md](base.md) | `new()` / `load()` / `export()` / `check()` / `refresh()` |
| [chart.md](chart.md) | 颜色、主题、画布、摄像机、引导线、Note、BPM 的创建与修改 |
| [query.md](query.md) | 元数据、对象、时间、颜色、几何与计算查询 |
| [advanced.md](advanced.md) | 按规格 Dict 批量插入、跨谱面复制、批量缓动修改与绘图的组合函数 |

当前 146 个导出函数均有对应模块文档。内部实现与维护说明见
[TECHNICAL.md](TECHNICAL.md)。

## 目录

- [安装与导入](#安装与导入)
- [快速开始](#快速开始)
- [模块与函数索引](#模块与函数索引)
- [规格化 Dict](#规格化-dict)
- [全局约定](#全局约定)
- [常见工作流](#常见工作流)

## 安装与导入

以下路径均相对于项目根目录（包含 `src/`、`docs/`、`tools/` 和 `pyproject.toml`
的目录，即上一级）。包位于 `src/rizChartFunction`。

```powershell
# 在项目根目录执行
$env:PYTHONPATH = "src"
python
```

```python
from rizChartFunction import (
    new, load, export, check,
    createLinePoint, createRingPoint, addLine,
    getLine, getNote, getBaseColor,
)
```

字体文字功能需要可选依赖：

```powershell
python -m pip install fontTools shapely numpy Pillow scikit-image
# 或安装项目可选组
python -m pip install -e ".[font]"
```


`src` 布局下也可以直接：

```python
import sys
sys.path.insert(0, r"src")
import rizChartFunction as rcf
```

## 快速开始

```python
from rizChartFunction import (
    new, addCanvas, addLine,
    createLinePoint, createRingPoint,
    createNote, getLine,
)

chart = new(175.0)
addCanvas(chart)

p0 = createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
p4 = createLinePoint(4.0, 1.0, 0, 0, "#FF0000")
ring = createRingPoint(0.0, "#FFFFFF")
notes = [createNote(1.0, "tap")]

addLine(chart, [p0, p4], ring, notes=notes)

line = getLine(chart, 0)
print(line["linePoints"][0]["color"])  # [255, 255, 255, 255]
```

## 模块与函数索引

### base

[base.md](base.md)：[`new()`](base.md#new) · [`load()`](base.md#load) ·
[`export()`](base.md#export) · [`check()`](base.md#check) ·
[`refresh()`](base.md#refresh)

### chart

[chart.md](chart.md)：

| 分类 | 函数 |
| --- | --- |
| 基础字段 | [`setBaseBpm()`](chart.md#setbasebpm) · [`setDelay()`](chart.md#setdelay) · [`setFileVersion()`](chart.md#setfileversion) |
| 颜色与主题 | [`rgb()`](chart.md#rgb) · [`rgba()`](chart.md#rgba) · [`mixColor()`](chart.md#mixcolor) · [`splitColor()`](chart.md#splitcolor) · [`setNormalTheme()`](chart.md#setnormaltheme) · [`setRiztime()`](chart.md#setriztime) · [`addRiztime()`](chart.md#addriztime) · [`deleteRiztime()`](chart.md#deleteriztime) |
| 画布 | [`addCanvas()`](chart.md#addcanvas) · [`deleteCanvas()`](chart.md#deletecanvas) |
| 画布位置 | [`addCanvasPosition()`](chart.md#addcanvasposition) · [`setCanvasPosition()`](chart.md#setcanvasposition) · [`deleteCanvasPosition()`](chart.md#deletecanvasposition) |
| 画布流速 | [`addCanvasSpeed()`](chart.md#addcanvasspeed) · [`setCanvasSpeed()`](chart.md#setcanvasspeed) · [`deleteCanvasSpeed()`](chart.md#deletecanvasspeed) |
| 摄像机 | [`addCameraPosition()`](chart.md#addcameraposition) · [`setCameraPosition()`](chart.md#setcameraposition) · [`deleteCameraPosition()`](chart.md#deletecameraposition) · [`addCameraScale()`](chart.md#addcamerascale) · [`setCameraScale()`](chart.md#setcamerascale) · [`deleteCameraScale()`](chart.md#deletecamerascale) |
| 引导线 | [`addLine()`](chart.md#addline) · [`deleteLine()`](chart.md#deleteline) |
| 线节点 | [`createLinePoint()`](chart.md#createlinepoint) · [`addLinePoint()`](chart.md#addlinepoint) · [`setLinePoint()`](chart.md#setlinepoint) · [`deleteLinePoint()`](chart.md#deletelinepoint) |
| 判定环 | [`createRingPoint()`](chart.md#createringpoint) · [`addRingPoint()`](chart.md#addringpoint) · [`setRingPoint()`](chart.md#setringpoint) · [`deleteRingPoint()`](chart.md#deleteringpoint) |
| 线色覆盖 | [`createLineColor()`](chart.md#createlinecolor) · [`addLineColor()`](chart.md#addlinecolor) · [`setLineColor()`](chart.md#setlinecolor) · [`deleteLineColor()`](chart.md#deletelinecolor) |
| 音符 | [`createNote()`](chart.md#createnote) · [`addNote()`](chart.md#addnote) · [`setNote()`](chart.md#setnote) · [`deleteNote()`](chart.md#deletenote) |
| BPM | [`addBpmShift()`](chart.md#addbpmshift) · [`setBpmShift()`](chart.md#setbpmshift) · [`deleteBpmShift()`](chart.md#deletebpmshift) |

### query

[query.md](query.md)：

| 分类 | 函数 |
| --- | --- |
| 元数据与计数 | [`getFileVersion()`](query.md#getfileversion) · [`getDelay()`](query.md#getdelay) · [`getBaseBpm()`](query.md#getbasebpm) · [`getLineCount()`](query.md#getlinecount) · [`getCanvasCount()`](query.md#getcanvascount) · [`getBpmShiftCount()`](query.md#getbpmshiftcount) · [`getRiztimeCount()`](query.md#getriztimecount) · [`getNoteCount()`](query.md#getnotecount) |
| 对象查询 | [`getBpmShift()`](query.md#getbpmshift) · [`getCanvas()`](query.md#getcanvas) · [`getCanvasPosition()`](query.md#getcanvasposition) · [`getCanvasSpeed()`](query.md#getcanvasspeed) · [`getCamera()`](query.md#getcamera) · [`getCameraPosition()`](query.md#getcameraposition) · [`getCameraScale()`](query.md#getcamerascale) · [`getLine()`](query.md#getline) · [`getLinePoint()`](query.md#getlinepoint) · [`getRingPoint()`](query.md#getringpoint) · [`getLineColor()`](query.md#getlinecolor) · [`getNote()`](query.md#getnote) · [`getTheme()`](query.md#gettheme) · [`getThemeColor()`](query.md#getthemecolor) · [`getChallengeTime()`](query.md#getchallengetime) · [`getRiztime()`](query.md#getriztime) |
| 按时间查询 | [`getBpmShiftByTime()`](query.md#getbpmshiftbytime) · [`getCanvasPositionByTime()`](query.md#getcanvaspositionbytime) · [`getCanvasSpeedByTime()`](query.md#getcanvasspeedbytime) · [`getCameraPositionByTime()`](query.md#getcamerapositionbytime) · [`getCameraScaleByTime()`](query.md#getcamerascalebytime) · [`getLinePointByTime()`](query.md#getlinepointbytime) · [`getRingPointByTime()`](query.md#getringpointbytime) · [`getLineColorByTime()`](query.md#getlinecolorbytime) · [`getNoteByTime()`](query.md#getnotebytime) |
| 按颜色查询 | [`getThemeByColor()`](query.md#getthemebycolor) · [`getLinePointByColor()`](query.md#getlinepointbycolor) · [`getRingPointByColor()`](query.md#getringpointbycolor) · [`getLineColorByColor()`](query.md#getlinecolorbycolor) |
| 颜色查询 | [`getBaseColor()`](query.md#getbasecolor) · [`getCoverColor()`](query.md#getcovercolor) · [`getMixColor()`](query.md#getmixcolor) |
| BPM 与时间 | [`getBpmAt()`](query.md#getbpmat) · [`getSecondsAt()`](query.md#getsecondsat) · [`getTickAt()`](query.md#gettickat) |
| 画布与摄像机 | [`getCanvasSpeedAt()`](query.md#getcanvasspeedat) · [`getCameraPositionAt()`](query.md#getcamerapositionat) · [`getCameraScaleAt()`](query.md#getcamerascaleat) |
| 计算与搜索 | [`getFloorPosition()`](query.md#getfloorposition) · [`getCanvasPositionAt()`](query.md#getcanvaspositionat) · [`getLinePosition()`](query.md#getlineposition) · [`getLineByPoint()`](query.md#getlinebypoint) · [`getLineByNote()`](query.md#getlinebynote) · [`getLineTimeRange()`](query.md#getlinetimerange) · [`getNotePosition()`](query.md#getnoteposition) · [`getNoteCanvas()`](query.md#getnotecanvas) |

### advanced

[advanced.md](advanced.md)：

| 分类 | 函数 |
| --- | --- |
| 引导线 | [`addLineByDict()`](advanced.md#addlinebydict) |
| 线子节点 | [`addLinePointByDict()`](advanced.md#addlinepointbydict) · [`addRingPointByDict()`](advanced.md#addringpointbydict) · [`addNoteByDict()`](advanced.md#addnotebydict) · [`addIsolatedNote()`](advanced.md#addisolatednote) · [`addLineColorByDict()`](advanced.md#addlinecolorbydict) |
| Riztime | [`addRiztimeByDict()`](advanced.md#addriztimebydict) |
| BPM | [`addBpmByDict()`](advanced.md#addbpmbydict) |
| 画布 | [`addCanvasByDict()`](advanced.md#addcanvasbydict) · [`addCanvasPositionByDict()`](advanced.md#addcanvaspositionbydict) · [`addCanvasSpeedByDict()`](advanced.md#addcanvasspeedbydict) |
| 摄像机 | [`addCameraPositionByDict()`](advanced.md#addcamerapositionbydict) · [`addCameraScaleByDict()`](advanced.md#addcamerascalebydict) |
| 复制引导线 | [`copyLine()`](advanced.md#copyline) · [`copyLinePoint()`](advanced.md#copylinepoint) · [`copyRingPoint()`](advanced.md#copyringpoint) · [`copyNote()`](advanced.md#copynote) · [`copyLineColor()`](advanced.md#copylinecolor) |
| 复制其它对象 | [`copyBpmShift()`](advanced.md#copybpmshift) · [`copyRiztime()`](advanced.md#copyriztime) · [`copyCanvas()`](advanced.md#copycanvas) · [`copyCanvasPosition()`](advanced.md#copycanvasposition) · [`copyCanvasSpeed()`](advanced.md#copycanvasspeed) · [`copyCamera()`](advanced.md#copycamera) · [`copyCameraPosition()`](advanced.md#copycameraposition) · [`copyCameraScale()`](advanced.md#copycamerascale) |
| 缓动 BPM / 流速 | [`setBpmShiftEase()`](advanced.md#setbpmshiftease) · [`setCanvasSpeedEase()`](advanced.md#setcanvasspeedease) |
| 缓动线节点 | [`setLinePointPositionEase()`](advanced.md#setlinepointpositionease) · [`setLinePointColorEase()`](advanced.md#setlinepointcolorease) · [`setLinePointColorByList()`](advanced.md#setlinepointcolorbylist) |
| 缓动颜色 | [`setRingColorEase()`](advanced.md#setringcolorease) · [`setLineColorEase()`](advanced.md#setlinecolorease) |
| 缓动画布 / 摄像机 | [`setCanvasPositionEase()`](advanced.md#setcanvaspositionease) · [`setCameraPositionEase()`](advanced.md#setcamerapositionease) · [`setCameraScaleEase()`](advanced.md#setcamerascaleease) |
| 绘图 / 区域 | [`drawPolygon()`](advanced.md#drawpolygon) · [`drawEllipse()`](advanced.md#drawellipse) · [`getClosedRegion()`](advanced.md#getclosedregion) |
| 文字 | [`drawText()`](advanced.md#drawtext) · [`drawThinText()`](advanced.md#drawthintext) |

所有批量函数和缓动函数的最后一个参数为 `isFailAddAllowed: bool = False`。默认原子模式，
失败时回退本批全部修改；设为 `True` 时跳过失败元素并继续。返回值统一为
失败元素的原始索引列表（成功为 `[]`）。缓动函数的 `easetype` 支持 `0..25`
与 Cubic Bezier 列表，其中原生 `easeType` 只覆盖 `0..18`。

`addBpmByDict()` 批内使用延迟计算，结束后统一执行一次全谱 `refresh()`，
因此所有受 BPM 影响的 `floorPosition`（线节点、Note、Hold 尾部、画布流速等）
都会重算。

## 规格化 Dict

本库把谱面对象分成两种形式：

- **完整节点**：谱面 JSON 内部的完整结构，包含派生字段。
- **规格 Dict**：创建、查询和修改函数输入/输出使用的结构，省略派生字段。

`createXXX()`、对象查询 `getXxx()` 和修改函数返回值都使用规格 Dict；
`addLine()` 接收规格 Dict。插入时再根据谱面上下文计算 `floorPosition`、
Hold 尾部画布和高度。

### 通用规则

- `time` 都是 tick；`isRealTime` 只用于输入换算，不出现在规格中。
- 规格中的颜色统一为 RGBA 列表 `[r, g, b, a]`；完整谱面 JSON 内部仍是
  RGBA Dict `{"r", "g", "b", "a"}`。
- 颜色输入支持 HEX、`[r,g,b]`、`[r,g,b,a]` 和 RGBA Dict。
- 规格是新建对象，不引用谱面内部 Dict/List。
- 规格不包含 `floorPosition`；Note 规格不包含 `otherInformations`。
- Hold 规格只保留 `endtime`。
- 查询函数会先校验字段和引用，非法时返回 `None`。
- 规格能否实际插入取决于目标谱面的 BPM/画布结构。

### 关键点

BPM、画布位置、画布流速、摄像机位置/缩放的关键点规格：

```python
{
    "time": float,
    "value": float,
    "easeType": int,
}
```

### 线节点

```python
{
    "time": float,
    "xPosition": float,
    "canvasIndex": int,
    "easeType": int,
    "color": [r, g, b, a],
}
```

### 颜色节点

判定环与线色覆盖共用：

```python
{
    "time": float,
    "startColor": [r, g, b, a],
    "endColor": [r, g, b, a],
}
```

### Note

```python
# Tap / Drag
{"type": 0, "time": float}   # type 也可为 1

# Hold
{"type": 2, "time": float, "endtime": float}
```

### 引导线

```python
{
    "linePoints": [线节点规格, ...],
    "notes": [Note 规格, ...],
    "judgeRingColor": [颜色节点规格, ...],
    "lineColor": [颜色节点规格, ...],
}
```

至少需要 2 个线节点和 1 个判定环节点；`lineColor` 可以为空。

### 主题与 Riztime

```python
# 主题
{"colorsList": [[r, g, b, a], [r, g, b, a], [r, g, b, a]]}

# Riztime（getRiztime() 合并规格）
{
    "themeIndex": int,
    "challengeIndex": int,
    "colorsList": [[r, g, b, a], [r, g, b, a], [r, g, b, a]],
    "checkPoint": float,
    "start": float,
    "end": float,
    "transTime": float,
}
```

### 使用关系

- `createXXX()` 生成规格。
- 按索引对象查询 `getXxx()` 返回规格；范围查询返回规格列表。
- 按时间/颜色查询返回索引列表，不返回对象。
- 计算查询返回数值。
- 修改/删除函数返回修改前/删除前的规格。
- `addLine()` 接收线节点、判定环、Note、线色的规格列表。

## 全局约定

### 谱面根结构

```text
fileVersion       int
chartDelayMs      int
themes            list
challengeTimes    list
bPM               float
bpmShifts         list
lines             list
canvasMoves       list
cameraMove        dict
```

`themes` 与 `challengeTimes` 必须满足
`len(themes) == len(challengeTimes) + 1`。

### 时间

- tick 是谱面内部时间单位；实际秒数通过 BPM 时间轴换算。
- `getXxxByTime()` 的 `starttime` 必须大于等于 `0.0`。
- `endtime=None` 表示查询 `[starttime, +∞)`。
- `endtime == starttime` 表示精确查询该时间点。
- `endtime > starttime` 表示闭区间 `[starttime, endtime]`。
- `endtime < starttime` 返回 `None`。

### 失败返回值

- 创建函数：规格 Dict；参数非法返回 `None`
- 添加函数（含 `addCanvas()`）：成功返回插入索引，失败返回 `None`；索引可能为
  `0`，判断成功请用 `is not None`，不要用真假值
- `advanced.py` 批量插入、复制和缓动函数：统一返回失败元素的原始索引列表；
  全部成功返回 `[]`。默认 `isFailAddAllowed=False` 为原子模式，失败会回退本批
  全部修改并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引。
  整体输入非法返回 `[-1]`。复制函数及缓动函数的 `indexlist` 位置同样用于失败
  索引；`copyCamera()` 失败固定返回 `[0]`。
- `drawPolygon()` / `drawEllipse()`：成功返回新建线索引列表，全部绘制失败或输入非法返回 `None`；
  两个绘制开关都为 `False` 时返回 `[]`。`drawPolygon()` 支持 `holelist` / `holecolor`
  孔洞填充，孔洞只影响填充，不影响边框。
- `getClosedRegion()`：成功返回所有有界闭合区域的线节点规格列表；没有闭合区域、
  输入非法或无法形成简单区域时返回 `None`。
- `drawText()`：成功返回新建线索引列表；字体/字形/参数非法或绘制失败返回 `None`。
  只绘制单行，不支持换行；支持按索引的多层线框和 `isFillGraph=False` 只画框模式。
  字体功能需要安装可选依赖 `font`。
- `drawThinText()`：成功返回新建的骨架线索引列表；只会画细线，不填充、不描边、
  不画背景。`smoothness` 控制骨架细节，非时间单调的分支会拆成多条线。
- `addIsolatedNote()`：创建一条透明辅助线并放置单个 Note；成功返回新线索引，
  失败返回 `None`。Tap / Drag 会自动在头部上方 1/16 节拍处补线节点，Hold
  按 `endtime` / `endposition` / `endcanvasindex` 放置尾部。
- `setLinePointColorByList()`：只重设索引区间内已有线节点的颜色，不增删节点；
  成功返回 `[]`，失败返回 `None`。节点稀疏时分段颜色过渡可能较粗。
- 修改、删除、按索引对象查询：规格或 `None`
- 按时间/颜色/位置查询：索引列表；无匹配返回 `[]`
- 计算查询：数值、颜色或坐标；失败返回 `None`

### 校验与导出

- `load()` 宽松：清洗、补默认值并执行规范化。
- `export()` 严格：先 `check()`，再要求清洗结果与输入完全一致。
- `check()` 只读，返回 `unexpectedParts` / `missingParts` / `errorValues`。
- `floorPosition` 检查误差阈值为 `1e-2`。

### BPM 与 floorPosition

- 依赖 `floorPosition` 的操作要求 `bpmShifts[0].time == 0.0`。
- 首个 BPM 节点不在 0 的谱面，需要先调用
  `addBpmShift(chart, value, 0.0)`。
- BPM 节点时间按非递减排列；相同时间允许，右侧节点生效。
- 画布流速是对**秒**积分，不是对 tick 积分。
- 画布流速关键点虽然保留 `easeType` 字段，但流速按阶梯变化，不使用缓动插值。
- 摄像机位置/缩放和画布位置节点按 `easeType` 插值。
- `bpmShifts[].floorPosition` 是从 tick 0 起算的绝对秒数。

### 刷新与重算

- `refresh()` 支持按模式、类型和索引范围刷新，详见
  [`refresh()`](base.md#refresh)。
- `mode`：`"all"` 重排并重算高度；`"floorPosition"` 只重算高度；
  `"order"` 只重排。
- `type` 支持全谱、BPM、线、线子数组、画布、摄像机及各自的节点类型。
- `"all"` 与 `"camera"` 忽略索引；`linePoints` / `notes` /
  `judgeRingColor` / `lineColor` 使用线索引与节点索引两组范围。
- 允许索引越界或交集为空；时间相同的节点保持原顺序。
- 有更改返回 `True`；无更改返回 `False`；结构非法或无法重算返回 `None`，
  并尽量恢复调用前状态。

### 延迟计算

- `addCanvasSpeed()`、`setCanvasSpeed()`、`deleteCanvasSpeed()`、BPM 节点编辑、
  `addNote()`、`setNote()`、`addLinePoint()`、`setLinePoint()`、`addLine()`
  支持 `isDelayCalculate=True`。
- 开启后会跳过 `floorPosition` 的计算/全谱重算；新增或修改的节点高度写为 `NaN`。
- 调用结束后需要执行 `refresh()` 修复高度；未修复前 `check()` / `export()` 会失败。
- 仅建议在批量修改量较大时使用。

## 常见工作流

### 从零创建谱面

```python
from rizChartFunction import new, addCanvas, addLine
from rizChartFunction import createLinePoint, createRingPoint

chart = new(175.0)
addCanvas(chart)

p0 = createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
p4 = createLinePoint(4.0, 1.0, 0, 0, "#FF0000")
ring = createRingPoint(0.0, "#FFFFFF")
addLine(chart, [p0, p4], ring)
```

### 读取、查询并导出

```python
from rizChartFunction import load, export, getLine, getNoteByTime

chart = load("input.json")
if chart is None:
    raise RuntimeError("读取失败")

line = getLine(chart, 0)
notes = getNoteByTime(chart, 0.0, 4.0)

if not export(chart, "output.json"):
    raise RuntimeError("导出失败")
```

### 按颜色查询

```python
from rizChartFunction import getLinePointByColor

matches = getLinePointByColor(chart, "#FF0000", canvasindex=0)
```

### 计算时间与高度

```python
from rizChartFunction import getSecondsAt, getFloorPosition

seconds = getSecondsAt(chart, 4.0)
height = getFloorPosition(chart, 4.0, canvasindex=0)
```

完整的内部设计、异常处理和扩展说明见 [TECHNICAL.md](TECHNICAL.md)。
