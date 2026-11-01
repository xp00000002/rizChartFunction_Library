# PLAN

> 最后更新：2026-10-25
> 状态：进行中

本文件跟踪 `query.py` 查询层的补全进度。每完成一个函数，就把对应的
`[ ]` 改成 `[x]`。

完成标准：

1. 在 `src/rizChartFunction/query.py` 中实现
2. 加入 `query.py` 的 `__all__`
3. 在 `src/rizChartFunction/__init__.py` 中导出
4. 在对应模块文档中补充说明（`query.md`，必要时同步 `README.md`）
5. 补充测试并通过

---

## 当前状态

- 已完成查询函数：54 个
- 待实现查询函数：0 个
- 高级组合层 `advanced.py`：12 个 `addXxxByDict()` + 13 个 `copyXxx()` + 9 个 `setXxxEase()` + `setLinePointColorByList()` + `drawPolygon()` / `drawEllipse()` / `getClosedRegion()` / `drawText()` / `drawThinText()` / `addIsolatedNote()` 已完成
- `chart.py` 返回值规格化：已完成
- 文档：`README.md` 总览 + `base.md` / `chart.md` / `query.md` / `advanced.md` 模块文档，已完成
- `base.py` 的 `refresh()`：已完成
- `refresh()` 的 mode/type/范围过滤与 NaN-only：已完成
- `isDelayCalculate` 延迟高度计算：已完成

---

## 一、已有查询函数（已完成）

- [x] `getFloorPosition(chart, time, canvasindex=None, isRealTime=False)`
- [x] `getCanvasPositionAt(chart, time, index=-1, isRealTime=False)`
- [x] `getLinePosition(chart, index, time, isAbsolutePosition=False, isRealTime=False)`
- [x] `getLineByPoint(chart, position=None, time=None, index=None, color=None, isAbsolutePosition=False, isRealTime=False)`
- [x] `getLineByNote(chart, position=None, time=None, type=None, isAbsolutePosition=False, isRealTime=False)`

---

## 二、第一批：对象查询与计数

目标：补完后不再需要直接索引谱面 dict 来读取基础数据。

数组类对象查询统一使用：

```python
getXxxs(chart, startindex, endindex=None)
```

- `endindex=None`：只查询 `startindex` 一个对象
- `endindex` 为 `int`：查询闭区间 `[startindex, endindex]`
- 查询全部使用 `getXxxs(chart, 0, -1)`
- 单数形式 `getXxx()` 不再单独提供

### 2.1 元数据

- [x] `getFileVersion(chart) -> int | None`
- [x] `getDelay(chart) -> int | None`
- [x] `getBaseBpm(chart) -> float | None`

### 2.2 计数

- [x] `getLineCount(chart) -> int | None`
- [x] `getCanvasCount(chart) -> int | None`
- [x] `getBpmShiftCount(chart) -> int | None`
- [x] `getRiztimeCount(chart) -> int | None`

### 2.3 BPM

- [x] `getBpmShift(chart, startindex, endindex=None) -> dict | list | None`

示例：

```python
getBpmShift(chart, 0)       # 第 1 个，dict
getBpmShift(chart, -1)      # 最后一个，dict
getBpmShift(chart, 0, 0)    # 第 1 个，list
getBpmShift(chart, 0, -1)   # 全部，list
```

### 2.4 画布

- [x] `getCanvas(chart, startindex, endindex=None) -> dict | list | None`
- [x] `getCanvasPosition(chart, canvasindex, startindex, endindex=None) -> dict | list | None`
- [x] `getCanvasSpeed(chart, canvasindex, startindex, endindex=None) -> dict | list | None`

`getCanvasPosition()` / `getCanvasSpeed()` 查询关键点规格；计算值查询分别
使用 `getCanvasPositionAt()` / `getCanvasSpeedAt()`。

### 2.5 摄像机

- [x] `getCamera(chart) -> dict | None`
- [x] `getCameraPosition(chart, startindex, endindex=None) -> dict | list | None`
- [x] `getCameraScale(chart, startindex, endindex=None) -> dict | list | None`

`cameraMove` 只有一个对象，因此保留单数 `getCamera()`；两个关键点数组
使用范围查询。计算值查询分别使用 `getCameraPositionAt()` /
`getCameraScaleAt()`。

### 2.6 引导线与内容

- [x] `getNoteCount(chart, startindex, endindex=None) -> int | None`
- [x] `getLine(chart, startindex, endindex=None) -> dict | list | None`
- [x] `getLinePoint(chart, lineindex, startindex, endindex=None) -> dict | list | None`
- [x] `getRingPoint(chart, lineindex, startindex, endindex=None) -> dict | list | None`
- [x] `getLineColor(chart, lineindex, startindex, endindex=None) -> dict | list | None`
- [x] `getNote(chart, lineindex, startindex, endindex=None) -> dict | list | None`

`getNoteCount()` 统计指定线索引范围内的 Note 总数；`endindex=None`
时只统计 `startindex` 一条线。

### 2.7 主题与 Riztime

- [x] `getTheme(chart, startindex, endindex=None) -> dict | list | None`
- [x] `getThemeColor(chart, themeindex, startindex, endindex=None) -> dict | list | None`
- [x] `getChallengeTime(chart, startindex, endindex=None) -> dict | list | None`
- [x] `getRiztime(chart, startindex, endindex=None) -> dict | list | None`

`getRiztime()` 返回合并后的对象，避免用户自己配对
`themes[i + 1]` 与 `challengeTimes[i]`：

```python
{
    "themeIndex": int,
    "challengeIndex": int,
    "colorsList": [color1, color2, color3],
    "start": float,
    "end": float,
    "transTime": float,
    "checkPoint": float,
}
```

### 2.8 按时间查询（点元素）

只查询“点”元素，不查询 Riztime、线等“段”元素。

通用规则：

- `starttime` 必须大于等于 `0.0`
- `endtime=None`：查询所有时间 `>= starttime` 的元素
- `endtime == starttime`：精确查找该时间点
- `endtime > starttime`：闭区间查询
- `indexlist` 过滤叶索引；`None` 表示全局
- `isRealStartTime` / `isRealEndTime` 控制时间是否为实际秒数
- 单层元素返回 `[index, ...]`
- 多层元素返回 `[[父索引, 子索引], ...]`
- 无匹配返回 `[]`，失败返回 `None`

- [x] `getBpmShiftByTime(chart, starttime, endtime=None, indexlist=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getCanvasPositionByTime(chart, starttime, endtime=None, indexlist=None, canvasindex=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getCanvasSpeedByTime(chart, starttime, endtime=None, indexlist=None, canvasindex=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getCameraPositionByTime(chart, starttime, endtime=None, indexlist=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getCameraScaleByTime(chart, starttime, endtime=None, indexlist=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getLinePointByTime(chart, starttime, endtime=None, indexlist=None, canvasindex=None, lineindex=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getRingPointByTime(chart, starttime, endtime=None, indexlist=None, lineindex=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getLineColorByTime(chart, starttime, endtime=None, indexlist=None, lineindex=None, isRealStartTime=False, isRealEndTime=False)`
- [x] `getNoteByTime(chart, starttime, endtime=None, indexlist=None, lineindex=None, type=None, isRealStartTime=False, isRealEndTime=False)`

`getNoteByTime()` 的 `type` 额外支持 `3` / `"holdtail"`，按 Hold 尾部
时间筛选。

### 2.9 按颜色查询

允许查询 theme、line point、ring color、line color。

颜色区间规则：

- `startcolor` / `endcolor` 支持 HEX、RGB(A) 列表
- `endcolor=None`：精确匹配 `startcolor`
- 每个通道独立闭区间；缺少 alpha 时按 `255`
- 任一通道 `end < start` 视为非法
- Theme 每个颜色独立匹配，返回 `[themeindex, colorindex]`
- Ring / line color 的 `startColor` 或 `endColor` 任一匹配即可
- 无匹配返回 `[]`，失败返回 `None`

- [x] `getThemeByColor(chart, startcolor, endcolor=None, indexlist=None)`
- [x] `getLinePointByColor(chart, startcolor, endcolor=None, indexlist=None, canvasindex=None, lineindex=None)`
- [x] `getRingPointByColor(chart, startcolor, endcolor=None, indexlist=None, lineindex=None)`
- [x] `getLineColorByColor(chart, startcolor, endcolor=None, indexlist=None, lineindex=None)`

返回格式：

- Theme：`[[themeindex, colorindex], ...]`
- Line point：`[[lineindex, pointindex], ...]`
- Ring / line color：`[[lineindex, nodeindex], ...]`

`getThemeByColor()` 的 `indexlist` 过滤主题索引；其余函数过滤叶索引。

---

## 三、第二批：计算查询

目标：在对象查询之上补齐时间、摄像机、几何、颜色与 Note 尾部查询。

### 3.1 BPM 与时间

- [x] `getBpmAt(chart, time, isRealTime=False) -> float | None`
- [x] `getSecondsAt(chart, tick) -> float | None`
- [x] `getTickAt(chart, seconds) -> float | None`

### 3.2 画布与摄像机

- [x] `getCanvasSpeedAt(chart, index, time, isRealTime=False) -> float | None`
- [x] `getCameraPositionAt(chart, time, isRealTime=False) -> float | None`
- [x] `getCameraScaleAt(chart, time, isRealTime=False) -> float | None`

### 3.3 线与 Note

- [x] `getLineTimeRange(chart, lineindex=-1, isRealTime=False) -> list | None`
- [x] `getNotePosition(chart, lineindex=-1, noteindex=-1, isAbsolutePosition=False) -> float | None`
- [x] `getNoteCanvas(chart, lineindex=-1, noteindex=-1, isHoldTail=False) -> int | None`

`getLineTimeRange()` 返回：

```python
[first_time, last_time]
```

`getNoteCanvas()` 默认返回 Note 头部画布；Hold 且 `isHoldTail=True` 时
返回 `otherInformations[1]` 中的尾部画布。`getNoteTail()` 不再提供，Hold
尾部时间直接由 `getNote()` 的 `endtime` 读取。

### 3.4 颜色查询

- [x] `getBaseColor(chart, index, time, position=None, isRealTime=False, isAbsolutePosition=False) -> list | None`
- [x] `getCoverColor(chart, index, time, isRealTime=False) -> list | None`
- [x] `getMixColor(chart, index, currenttime, querytime=None, position=None, isRealCurrentTime=False, isRealQueryTime=False, isAbsolutePosition=False) -> list | None`

---

## 四、对象查询约定

### startindex / endindex

- `endindex=None`：单值查询，返回 `dict | None`
- `endindex` 为 `int`：范围查询，返回 `list`（可以为空）
- 区间是**闭区间** `[startindex, endindex]`
- 两个索引都支持负数，从末尾计算
- 单值查询使用严格索引：越界 → `None`
- 范围查询使用切片语义：越界裁剪，`start > end` → `[]`
- 数组本身缺失或类型错误 → `None`
- 单值指向的元素不是 `dict` → `None`
- 范围内任一元素不是 `dict` → `None`

示例：

```python
getLine(chart, 0)          # 第一条线，dict
getLine(chart, -1)         # 最后一条线，dict
getLine(chart, 0, 0)       # 第一条线，list
getLine(chart, 0, -1)      # 全部线，list
getLine(chart, 1, -2)      # 第二条到倒数第二条，list
```

### 返回值

- 对象查询返回**规格 Dict**，不返回谱面内部引用
- 规格是输入用结构，省略派生字段：`floorPosition`、`otherInformations` 等
- 派生值通过计算查询获取：`getFloorPosition()`、`getNotePosition()`、
  `getNoteCanvas()`、`getSecondsAt()` 等
- 查询时完成字段与引用校验；非法 → `None`
- 不会修改原始谱面
- 颜色字段统一为 RGBA 列表 `[r, g, b, a]`；完整谱面 JSON 内部仍是 Dict
- 返回的规格可以由 `advanced.py` 的 `addXxxByDict()` 直接导入
- 单值查询返回 `dict | None`；范围查询返回 `list`（可以为空）

### 规格结构

| 类型 | 规格 Dict |
| --- | --- |
| BPM 节点 | `{time, value, easeType}` |
| 画布 | `{index, xPositionKeyPoints: [...], speedKeyPoints: [...]}` |
| 画布/摄像机关键点 | `{time, value, easeType}` |
| 摄像机 | `{scaleKeyPoints: [...], xPositionKeyPoints: [...]}` |
| 引导线 | `{linePoints: [...], notes: [...], judgeRingColor: [...], lineColor: [...]}` |
| 线节点 | `{time, xPosition, canvasIndex, easeType, color}` |
| 判定环 / 线色 | `{time, startColor, endColor}` |
| Note | Tap / Drag：`{type, time}`；Hold：`{type: 2, time, endtime}` |
| 主题 | `{colorsList: [...]}` |
| ChallengeTime | `{checkPoint, start, end, transTime}` |
| Riztime | `{themeIndex, challengeIndex, colorsList, start, end, transTime, checkPoint}` |

说明：

- `linePoints` / `notes` / `judgeRingColor` / `lineColor` 里的元素也使用
  上表的子规格。
- Hold 的 `endtime` 从 `otherInformations[0]` 取得，不返回尾部画布和
  尾部 `floorPosition`。
- `getLine()` 的返回值可以直接传给 `addLineByDict()`；
  其余数组规格可以传给对应的 `addXxxByDict()`。
- 引导线规格至少要有 2 个线节点和 1 个判定环节点，否则视为非法。
- 查询只保证规格字段和引用合法；目标谱面能否实际计算 `floorPosition`
  仍取决于目标谱面的 BPM / 画布结构（例如 `time=0.0` BPM 节点）。

### 时间

- 计算类查询统一支持 `isRealTime=False`
- 对象查询返回原始 tick 值，不做换算
- `getSecondsAt()` / `getTickAt()` 是显式换算入口

---

## 五、advanced.py（Dict 插入、复制、缓动、绘图与原子回退已完成）

`advanced.py` / `advanced_ease.py` 只调用 `base.py` / `chart.py` / `query.py` 的公开函数，不直接操作谱面 dict。

### Dict 插入

- [x] `addLineByDict(chart, dictlist, index=-1, isFailAddAllowed=False)`
- [x] `addLinePointByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addRingPointByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addNoteByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addLineColorByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addRiztimeByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addBpmByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addCanvasByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addCanvasPositionByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addCanvasSpeedByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addCameraPositionByDict(chart, dictlist, isFailAddAllowed=False)`
- [x] `addCameraScaleByDict(chart, dictlist, isFailAddAllowed=False)`

所有函数最后一个参数为 `isFailAddAllowed: bool = False`，统一返回
`list[int]`：成功 `[]`，失败为原始输入索引；整体输入非法返回 `[-1]`。
默认原子模式失败会回退本批全部插入并返回 `[失败索引]`；设为 `True` 时
跳过失败规格、回退该规格自身的部分插入，并返回全部失败索引。

线子节点与画布子节点可通过规格中的可选 `lineindex` / `canvasindex`
指定父对象，缺省为最后一条线 / 画布。

`addLineByDict()` 接收 `getLine()` 返回的引导线规格。
注意：查询规格省略派生字段；`addLine()` / `addNote()` 插入时仍会重新
计算 `floorPosition` 和 Hold 尾部信息。

### 复制

- [x] `copyLine()`
- [x] `copyLinePoint()`
- [x] `copyRingPoint()`
- [x] `copyNote()`
- [x] `copyLineColor()`
- [x] `copyBpmShift()`
- [x] `copyRiztime()`
- [x] `copyCanvas()`
- [x] `copyCanvasPosition()`
- [x] `copyCanvasSpeed()`
- [x] `copyCamera()`
- [x] `copyCameraPosition()`
- [x] `copyCameraScale()`

注意：

- `addNoteByDict()` 走 `addNote()`，Tap / Drag 的三元素
  `otherInformations` 占位会被归一为空列表
- `copyLine()` 走 `addLine()`，会保留完整节点里的占位
- `copyLine()` 会重算 `floorPosition`，不是逐字节复制

### 缓动

- [x] `setBpmShiftEase()`
- [x] `setLinePointPositionEase()`
- [x] `setLinePointColorEase()`
- [x] `setRingColorEase()`
- [x] `setLineColorEase()`
- [x] `setCanvasPositionEase()`
- [x] `setCanvasSpeedEase()`
- [x] `setCameraPositionEase()`
- [x] `setCameraScaleEase()`

所有缓动函数最后一个参数为 `isFailAddAllowed: bool = False`，统一返回
`list[int]`：成功 `[]`，失败为原始 `indexlist` 位置；整体输入非法返回
`[-1]`。位置类节点直接写 `0..18`；`19..22` 精确拆分；`23..25` 与 Cubic
Bezier 通过节点采样模拟。`uniform` / `arc` / `curvature` 不限制插入数量；
`recursion` / `priority` 每个 tick 最多 48 个节点。BPM / 流速 / 颜色节点
按各自原生阶跃或颜色过渡插入节点。

### 绘图

- [x] `drawPolygon()`：凸包优先、简单凹多边形回退、线性/径向/锥形/径向边界/
  锥形边界填充、透明空隙硬切、int/list 边框层（支持向内层、自交/退化跳过）、
  透明判定环、原始 `pointlist` 顶点颜色、重复颜色位置突变、径向边界颜色单独采样；
  支持 `holelist` / `holecolor` 多孔洞填充遮罩，五种填充统一生效，边框不受影响；
  `timemultiple` 只参与径向/锥形渐变计算。
- [x] `drawEllipse()`：半轴旋转、90° 四线 `Out/In Circle`、非 90° 左右半椭圆
  双线、四种轴端点强制节点、五种插入策略、int/list 边框层、五种填充、四向
  `colorList` 插值与径向/锥形边界起始射线；`timemultiple` 缩放有效 `yLength`。
- [x] `getClosedRegion()`：同一画布线集合求交、平面图闭合面提取、所有有界区域
  返回、环形面拆分为独立边界、交点/已有节点/缓动插入点重建、Venn 最小区域。
- [x] `drawText()`：单字体文件、可变字重、单行排版、em 字间距、线性填充、
  按索引的多层线框、`isFillGraph` 只画框模式、扣除文字的背景、`timemultiple`
  与 `isFlipX`。
- [x] `drawThinText()`：字体骨架提取、单行排版、`smoothness` 细节控制、
  非时间单调分支拆分、单像素点近似、细线建线与整体提交/回退。
- [x] `addIsolatedNote()`：透明辅助线、Tap/Drag 1/16 节拍补线、Hold 尾部
  画布/位置、绝对坐标与真实时间换算。
- [x] `setLinePointColorByList()`：按索引区间和节点时间比例重设已有线节点颜色，
  支持 0-25 / Cubic Bezier 缓动、边界原色回退与失败回滚。

---

## 六、chart.py 返回值规格化（已完成）

查询层完成后，修改 `chart.py` 中“成功时返回原生对象”的修改函数，统一
返回规格 Dict。失败时的返回值保持不变。

统一规则：

- 返回新建的规格 Dict，不引用谱面内部对象
- 颜色字段为 RGBA 列表
- 派生字段省略：`floorPosition`、`otherInformations` 等
- 单对象返回 `dict | None`
- 多对象返回值需要定义统一结构；建议 `setRiztime()` /
  `deleteRiztime()` 返回合并后的 Riztime 规格，而不是
  `[原生主题对象, 原生 challengeTimes 对象]`
- `setBaseBpm()` / `setDelay()` / `setFileVersion()` 返回原始值，
  不在本次范围
- `addCanvas()` 返回索引；其余 `addXxx()` 成功也返回插入索引，失败返回 `None`

### 主题与 Riztime

- [x] `setNormalTheme()` 返回主题规格
- [x] `setRiztime()` / `deleteRiztime()` 返回 Riztime 规格

### 画布

- [x] `deleteCanvas()` 返回画布规格
- [x] `setCanvasPosition()` / `deleteCanvasPosition()` 返回关键点规格
- [x] `setCanvasSpeed()` / `deleteCanvasSpeed()` 返回关键点规格

### 摄像机

- [x] `setCameraPosition()` / `deleteCameraPosition()` 返回关键点规格
- [x] `setCameraScale()` / `deleteCameraScale()` 返回关键点规格

### 引导线与节点

- [x] `deleteLine()` 返回引导线规格
- [x] `setLinePoint()` / `deleteLinePoint()` 返回线节点规格
- [x] `setRingPoint()` / `deleteRingPoint()` 返回颜色规格
- [x] `setLineColor()` / `deleteLineColor()` 返回颜色规格

### Note 与 BPM

- [x] `setNote()` / `deleteNote()` 返回 Note 规格
- [x] `setBpmShift()` / `deleteBpmShift()` 返回 BPM 节点规格

### 收尾

- [x] 更新 `README.md` / 模块文档的返回值说明
- [x] 更新 `TECHNICAL.md` 的返回值约定
- [x] 更新测试，覆盖“返回规格不引用谱面内部对象”

---

## 七、进度记录

| 日期 | 内容 |
| --- | --- |
| 2026-10-24 | 创建 PLAN.md，整理查询层待实现函数 |
| 2026-10-24 | 完成 2.1 元数据 3 个函数；完成 2.2 计数 4 个函数（`getNoteCount()` 移至 2.6） |
| 2026-10-24 | 对象查询改为 `startindex` / `endindex` 范围查询 |
| 2026-10-24 | 对象查询改为返回输入规格（省略派生字段）；advanced 增加 `addLineByDict()` |
| 2026-10-25 | 完成 16 个按索引查询函数；计算版 `getCanvasPosition()` 改名为 `getCanvasPositionAt()`，计算版摄像机查询预留在 `getCameraPositionAt()` / `getCameraScaleAt()` |
| 2026-10-25 | 完成 `getNoteCount(chart, startindex, endindex=None)`，按线索引范围统计 Note 总数 |
| 2026-10-25 | 完成 9 个点元素 `getXxxByTime()` 查询函数，支持时间范围、索引过滤、画布/线过滤与 `holdtail` |
| 2026-10-25 | 完成 4 个 `getXxxByColor()` 查询函数，支持逐通道颜色区间、主题/线节点/判定环/线色 |
| 2026-10-25 | 完成 3 个颜色查询函数：`getBaseColor()`、`getCoverColor()`、`getMixColor()` |
| 2026-10-25 | 完成 3.1 的 `getBpmAt()`、`getSecondsAt()`、`getTickAt()` |
| 2026-10-28 | 完成 9 个 `setXxxEase()`：原生 `0..18`、`19..22` 精确拆分、`23..25`/Cubic Bezier 模拟、五种插入策略与原子/允许失败事务 |
| 2026-10-29 | 缓动插入限制调整：`uniform`/`arc`/`curvature` 不限插入数量；`recursion`/`priority` 每 tick 上限改为 48，并修复满 tick 后整段丢弃后续 tick 的问题 |
| 2026-10-29 | 新增 `drawPolygon()`：凸包排序、线性/径向/锥形填充、多层边框、重复颜色位置突变与原子建线 |
| 2026-10-30 | 修复径向渐变重复颜色切换位置：仅对边界时间小于中心时间的一侧展开重复色标，并将切换中心向多边形中心内缩 0.008 个谱面坐标单位；其它方向不变 |
| 2026-10-30 | `drawPolygon()` 支持 int/list 边框层与负层内缩；新增 `radialBorder` / `conicBorder`，按边界弧长 `precision` 采样射线 |
| 2026-10-30 | `drawPolygon()` 支持简单凹多边形：凸包优先、输入顺序回退、填充透明空隙、边框自交/多轮廓跳过 |
| 2026-10-30 | 修复凹多边形填充空隙在射线/填充线时间递减时的透明硬切方向反转 |
| 2026-10-30 | 新增 `drawEllipse()`：旋转半轴、90° 四线、非 90° 双半椭圆、轴端点强制节点、插入策略、边框层与五种填充 |
| 2026-10-31 | 新增 `getClosedRegion()`：线集合求交、有界闭合面、`isCreateCrossPoint` 节点替换、缓动插入与所有区域返回 |
| 2026-10-31 | `drawPolygon()` 新增 `holelist` / `holecolor`：五种填充均支持孔洞遮罩，边框不受影响 |
| 2026-10-31 | 修复孔洞与填充线相切时整条线被透明化的问题；孔洞内部判定改为严格内部判定 |
| 2026-10-31 | 新增 `drawText()`：fontTools/shapely 字形排版、线性填充、边框、背景、变体字重、`timemultiple` 与 `isFlipX` |
| 2026-10-31 | `drawText()` 边框改为按 `bordersize` 索引的多层轮廓线，弃用填充环；新增 `isFillGraph`，支持只画线框 |
| 2026-10-31 | 统一 `drawText()` 参数名：`position` / `fontsize` / `letterspacing`；`drawPolygon()` / `drawEllipse()` 默认边框层改为 `[1]`，避免第 0 层与填充线重合遮挡 |
| 2026-10-31 | 新增 `drawThinText()`：字形栅格化、骨架提取、`smoothness` 细节控制、非时间单调分支拆分与细线提交 |
| 2026-11-01 | 新增 `addIsolatedNote()`：透明辅助线、Tap/Drag 1/16 节拍补线、Hold 尾部画布与绝对坐标换算 |
| 2026-11-01 | 新增 `setLinePointColorByList()`：按节点索引区间重设已有线节点颜色，不增删节点 |
| 2026-11-01 | `drawPolygon()` / `drawEllipse()` 新增 `timemultiple`（默认 1.65）：多边形用于径向/锥形渐变计算，椭圆额外缩放有效 `yLength` |
| 2026-10-25 | 完成 3.2 的 `getCanvasSpeedAt()`、`getCameraPositionAt()`、`getCameraScaleAt()` |
| 2026-10-25 | `getXxxByTime()` 的 `endtime=None` 改为开放结束；`endtime == starttime` 表示精确查询 |
| 2026-10-25 | 完成 3.3：`getLineTimeRange()`、`getNotePosition()`、`getNoteCanvas()`；移除 `getNoteTail()` 待办 |
| 2026-10-25 | 规格颜色改为 `[r,g,b,a]`；完成 `chart.py` 修改函数的返回值规格化 |
| 2026-10-24 | 新增待办：查询层完成后将 `chart.py` 修改函数的成功返回值统一为规格 Dict |
| 2026-10-26 | `addXxx()` 成功返回插入索引、失败返回 `None`；`addBpmShift()` 同时间节点改为追加到右侧，BPM 节点允许非递减时间 |
| 2026-10-26 | advanced 批量函数增加 `isFailAddAllowed`，统一返回失败索引列表；默认原子回退，允许失败时跳过并继续 |
| 2026-10-26 | advanced 增加 `addBpmByDict()`；批内延迟写入并在结束后全谱 `refresh()` |
| 2026-10-27 | advanced 增加 13 个 `copyXxx()`，支持 insert/replace/part、时间/位置偏移、画布映射与原子预演 |
