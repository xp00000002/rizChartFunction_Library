# rizChartFunction 技术细节

本文档面向需要维护或扩展本库的开发者，说明内部实现、关键不变量、调用时机与常见陷阱。

公开 API 的用法与参数说明见 [README.md](README.md) 及模块文档
[base.md](base.md)、[chart.md](chart.md)、[query.md](query.md)。

---

## 1. 模块结构

| 文件 | 职责 |
| --- | --- |
| `src/rizChartFunction/_internal.py` | 共享底层工具：类型判断、颜色解析、缓动、BPM 时间轴、`floorPosition` 计划、画布查找 |
| `src/rizChartFunction/base.py` | `new()` / `load()` / `export()` / `check()` / `refresh()`，格式描述表、递归清洗、默认结构 |
| `src/rizChartFunction/chart.py` | 所有修改、创建、节点编辑函数，颜色混合/拆分 |
| `src/rizChartFunction/query.py` | 所有查询函数，坐标反查、颜色查询 |
| `src/rizChartFunction/advanced.py` | 按规格 Dict 批量插入、复制、缓动入口，以及独立 Note 辅助线生成；只调用公开 API |
| `src/rizChartFunction/advanced_copy.py` | `copyXxx()` 的预演、规格转换与目标写入实现 |
| `src/rizChartFunction/advanced_ease.py` | `setXxxEase()` 的索引解析、缓动采样、拆分/模拟、recursion/priority 每 tick 48 节点上限与事务提交 |
| `src/rizChartFunction/advanced_draw.py` | `drawPolygon()` / `drawEllipse()` 的绘图实现（含填充孔洞遮罩），以及 `getClosedRegion()` 的线交图、闭合面提取与区域点重建 |
| `src/rizChartFunction/advanced_font.py` | `drawText()` / `drawThinText()` 的字体解析、字形 flatten、单行排版、边框、背景、填充与骨架提取 |
| `src/rizChartFunction/__init__.py` | 统一导出公开函数 |

依赖方向：

```text
query.py  ──> chart.py   （仅复用公开的 mixColor）
query.py  ──> _internal.py
chart.py  ──> _internal.py
base.py   ──> _internal.py
base.py   ──> chart.py   （refresh 的局部高度计算复用 _canvas_floor_position_at、_line_note_position）
advanced.py ──> advanced_copy.py （复制函数）
advanced.py ──> advanced_ease.py （缓动函数）
advanced.py ──> advanced_draw.py （绘图函数）
advanced.py ──> advanced_font.py （文字函数）
advanced_font.py ──> advanced_draw.py / chart.py / query.py（公开 API）
advanced_font.py ──> fontTools / shapely（可选字体与几何依赖）
advanced.py ──> base.py    （仅复用公开 refresh）
advanced.py ──> chart.py   （仅复用公开 add/set/delete 函数）
advanced.py ──> query.py   （复用公开查询函数与画布位置换算）
advanced_copy.py ──> base.py / chart.py / query.py（仅公开 API）
advanced_ease.py ──> base.py / chart.py / query.py（仅公开 API）
advanced_draw.py ──> base.py / chart.py / query.py（仅公开 API）
_internal.py ──> 标准库
```

`_internal.py` 不依赖任何项目模块，因此不存在循环导入。
`base.py` / `chart.py` / `query.py` 共享的底层逻辑必须放在 `_internal.py`，
不要在多个模块中各自实现。

---

## 2. 数据模型

### 2.1 根结构

```text
fileVersion       int
chartDelayMs      int
themes            list   常规主题 + 每个 Riztime 一个主题
challengeTimes    list   Riztime 起止时间
bPM               float  基准 BPM
bpmShifts         list   BPM 变化关键点
lines             list   引导线
canvasMoves       list   画布移动与流速
cameraMove        dict   摄像机移动与缩放
```

约定：

- 官方文件中的键名是 `bpmShifts`（小写 `p`），本库以它为标准，同时兼容读取 `bPMShifts`。
- `songsName`、`offset` 是官方谱面专有字段，本库面向自制谱面，**不写入**，`load()` 会删除它们，`export()` 会拒绝含这些键的谱面。
- `themes` 与 `challengeTimes` 必须满足 `len(themes) == len(challengeTimes) + 1`，`themes[0]` 是常规主题。
- `chartDelayMs` 在官方谱面中通常不存在，`load()` 会补 `0`。

### 2.2 color 与 keyPoint

```text
完整节点 color  {r, g, b, a}   四个 0-255 的 int
规格颜色        [r, g, b, a]
keyPoint        {time, value, easeType, floorPosition}
```

- 完整谱面 JSON 内部颜色仍是 RGBA Dict。
- `createXXX()`、对象查询和修改函数返回的规格中，颜色统一为 RGBA 列表。
- 所有颜色输入仍兼容 HEX、RGB(A) 列表和 RGBA Dict。
- `time` 单位是 tick。
- `value` 的含义随数组不同：BPM 倍率、画布流速、x 坐标、缩放倍率。
- `easeType` 只对 `linePoints`、`xPositionKeyPoints`（画布与摄像机）、`scaleKeyPoints` 有意义。
- `bpmShifts.easeType` 与 `speedKeyPoints.easeType` 按格式恒为 `0`。
- `xPositionKeyPoints`、`scaleKeyPoints`、`cameraMove` 下的 `floorPosition` 恒为 `0`。

覆盖色混合（`mixColor()`，见 Rizline Editor 的覆盖色公式）：

```text
R0' = R1' * (1 - A2') + R2' * A2'
G0' = G1' * (1 - A2') + G2' * A2'
B0' = B1' * (1 - A2') + B2' * A2'
A0 = A1
```

1 是基础色、2 是覆盖色，通道归一化到 0-1，RGB 四舍五入回 0-255。
输出 alpha 恒为基础色 alpha；覆盖色 alpha 只作为 RGB 混合系数，不参与
输出 alpha。`splitColor()` 是它的反推/校验入口：

- 已知覆盖色、求基础色：覆盖色 alpha < 255 时可从三元 RGB 方程反推。
  由于输出按整数四舍五入，覆盖色 alpha 接近 255 时可能有多个可行基础色；
  实现取最接近实数反解的值。覆盖色 alpha = 255 时基础色 RGB 不影响结果，
  不唯一，返回混合色本身作为规范基础色；若混合色 RGB 与覆盖色不一致则
  返回 `None`。
- 已知基础色、求覆盖色：数学上通常不唯一。实现选择“能复现混合色且
  alpha 最小”的覆盖色作为规范结果，再用正向 `mixColor()` 校验。

### 2.3 floorPosition 的两种含义（重要）

这是本库最容易搞错的地方：

| 位置 | 含义 | 计算方式 |
| --- | --- | --- |
| `bpmShifts[].floorPosition` | 从 tick 0 起算的**绝对秒数** | `Σ Δtick × 60 / (bPM × value)` |
| `canvasMoves[].speedKeyPoints[].floorPosition` | 画布高度累计值 | `Σ speed × Δ秒` |
| `lines[].linePoints[].floorPosition` | 该节点在所属画布中的高度 | 取该画布在节点 tick 处的高度 |
| `lines[].notes[].floorPosition` | 音符头部的画布高度 | 同上 |
| `lines[].notes[].otherInformations[2]` | Hold 尾部的画布高度 | 尾部落点 tick、尾部画布对应的高度 |

关键结论：

- **画布流速是对“秒”积分，不是对 tick 积分**。例如 200 BPM 下流速 99 持续 4.5 tick，高度是 `99 × 4.5 × 60 / 200 = 133.65`。
- BPM 节点本身的 `floorPosition` 是绝对秒数，和画布高度完全是两套公式，不能混用。
- `bpmShifts[0].time` 必须为 `0.0`。缺少时，所有需要时间轴的函数都会失败；唯一补节点入口是 `addBpmShift(chart, value, 0.0)`。
- 画布流速节点可以重复时间；在某个 tick 处取**最后一个时间相同的节点**。
- BPM 节点之间必须按时间非递减；与其它节点数组一样，相同时间允许，右侧节点生效。画布流速、画布位置、摄像机、线节点也允许时间相同。

### 2.4 themes / challengeTimes

- `themes[i + 1]` 与 `challengeTimes[i]` 一一对应。
- `load()` 中的 `_fix_theme_counts()` 会在 `themes` / `challengeTimes`
  为空或缺少时补默认值，并从末尾删除多余的一方，以满足上述关系；
  删除是**破坏性**的，但属于既定设计。
- `setRiztime()` / `addRiztime()` / `deleteRiztime()` 会同步移动两边，保持配对。
- `addRiztime()` 若发现当前**只有一个** Riztime，且该 Riztime 的
  `start == end`，会把它视为占位空 Riztime：先删除它及其配对主题
  `themes[1]`，再插入新的 Riztime。

### 2.5 notes

```text
{type, time, floorPosition, otherInformations}
type: 0=Tap, 1=Drag, 2=Hold
```

- `otherInformations`：
  - Tap / Drag：空列表、省略，或 3 个数字（官方谱面中存在这种占位写法）；
  - Hold：必须是 `[尾部 tick, 尾部画布, 尾部 floorPosition]`。
- 重算 `floorPosition` 时**只处理 type=2 的第三个值**。Tap/Drag 的三元素占位（例如 IN 中的 `[4.0, 0.0, 0.0]`）不能被改写。
- 音符没有 `xPosition`。音符头部与 Hold 尾部使用**不同**的画布边界规则：

```text
头部：[p_i.time, p_{i+1}.time)  → p_i.canvasIndex
      t == p_j.time             → p_j.canvasIndex（右侧节点，含尾节点）

尾部：(p_i.time, p_{i+1}.time]  → p_i.canvasIndex
      t == p_j.time             → p_{j-1}.canvasIndex（左侧节点/前一段）
```

- 头部 `floorPosition` 用头部画布在头部时间计算。
- Hold 的 `otherInformations[1]` / `[2]` 用尾部时间按上述尾部规则重新确定
  画布并计算高度。
- `createNote()` 只生成 Note 规格 Dict，不计算 `floorPosition` /
  `otherInformations`；实际高度由 `addNote()` / `addLine()` 调用
  `_build_note()` 计算。

### 2.6 判定环与线色覆盖

`lines[].judgeRingColor` 与 `lines[].lineColor` 的元素结构相同：

```text
{startColor, endColor, time}
```

- `startColor` 在 `time` 处生效。
- `endColor` 是到下一个节点（或线结束）之前的颜色目标。
- 两个节点之间颜色均匀过渡。
- `judgeRingColor`：未添加判定环时，通常写一个 RGBA 全 0 的节点；
  格式要求至少 1 个。`load()` 遇到空数组会补一个
  `time=首节点时间`、RGBA 全 0 的默认节点，而不是删除该线。
- `lineColor`：可以为空；生效时会与节点颜色混合，并保留节点自身的
  alpha。
- `createRingPoint()` / `createLineColor()` 生成对应颜色节点；
  `addRingPoint()` / `setRingPoint()` / `deleteRingPoint()` 负责判定环
  增删改；`addLineColor()` / `setLineColor()` / `deleteLineColor()`
  负责线色覆盖增删改。
- 两者都不参与 `floorPosition` 计算。

### 2.7 addLine 的两种节点格式

`addLine()` 对 `linePoints`、`judgeRingColor`、`notes`、`lineColor`
都同时接受完整节点与规格 Dict。`createLinePoint()` / `createNote()` 生成
的就是规格 Dict；`createRingPoint()` / `createLineColor()` 生成颜色规格。
`addLine()` 是统一的物化入口。

- **完整节点**：包含 `floorPosition` / `otherInformations` 等派生字段，
  但仍然只作为输入形状。输入中的 `floorPosition` 只做格式校验，
  **不参与结果**。
- **规格 Dict**：省略派生字段。

两种格式都会经过 `_normalize_line_point()` / `_normalize_color_node()` /
`_normalize_note()`，并重新计算：

- `linePoints[].floorPosition`
- `notes[].floorPosition`
- Hold 尾部画布与尾部 `floorPosition`

因此 `addLine()` 要求谱面存在 `time=0.0` 的 BPM 节点；IN 这类首个 BPM
节点在 4.0 的谱面需要先调用 `addBpmShift(chart, value, 0.0)`。

完整 Note 的 `type` / `time` 会被使用；Hold 尾部时间取自
`otherInformations[0]`，但尾部画布和高度会重算。Tap / Drag 的三元素
`otherInformations` 占位会保留；缺少时补空列表。头部/尾部范围仍会按
新线校验。

`notes` / `linecolors` 是 `addLine()` 的 keyword-only 参数，可为空。
四类节点都会按 `time` 稳定排序后写入；任一项非法时整条线不插入。

---

## 3. 时间轴与缓动

### 3.1 tick 与秒

```text
1 tick = 60 / (bPM × bpmShifts.value) 秒
```

BPM 时间轴的计算：

```text
seconds[0] = 0
seconds[i] = seconds[i-1] + (time[i] - time[i-1]) × 60 / (bPM × value[i-1])
```

由于要求 `time[0] == 0`，上式的起点是确定的。

`_internal.py` 提供唯一实现：

- `_bpm_seconds()` → `(base_bpm, times, values, seconds)`
- `_seconds_at()`：tick → 秒
- `_seconds_to_tick()`：秒 → tick

`chart.py` 与 `query.py` 直接复用；查询中的 `_get_bpm_timeline()` /
`_tick_at_realtime()` 只是导入别名，不再各自实现。

### 3.2 缓动类型

`easeType` 取值 0-18：

| 值 | 名称 | f(t) |
| --- | --- | --- |
| 0 | Linear | `t` |
| 1 | In Quad | `t²` |
| 2 | Out Quad | `1 - (1-t)²` |
| 3 | InOut Quad | `2t²` / `1 - 2(1-t)²` |
| 4 | In Cubic | `t³` |
| 5 | Out Cubic | `1 - (1-t)³` |
| 6 | InOut Cubic | `4t³` / `1 - 4(1-t)³` |
| 7 | In Quart | `t⁴` |
| 8 | Out Quart | `1 - (1-t)⁴` |
| 9 | InOut Quart | `8t⁴` / `1 - 8(1-t)⁴` |
| 10 | In Quint | `t⁵` |
| 11 | Out Quint | `1 - (1-t)⁵` |
| 12 | InOut Quint | `16t⁵` / `1 - 16(1-t)⁵` |
| 13 | Zero | `0` |
| 14 | One | `1` |
| 15 | In Circle | `1 - √(1-t²)` |
| 16 | Out Circle | `√(1-(1-t)²)` |
| 17 | Sin | `sin(πt/2)` |
| 18 | Cos | `1 - cos(πt/2)` |

规则：

- 节点 `i` 的 `easeType` 作用于 `i → i+1` 这一段。
- 最后一个节点的 `easeType` 不影响任何区间。
- `Zero` / `One` 会产生阶跃效果。
- 查询时 `easeType` 不在 0-18 → 返回 `None`。
- 编辑时 `chart._ease_type()` 默认把越界值夹到 0-18。

---

## 4. 内部函数参考

### 4.1 _internal.py

`_internal.py` 只依赖标准库，集中存放多个模块共用的底层函数。其他模块只能
导入，不应在各自文件里重新实现。

| 函数 | 作用 | 使用方 |
| --- | --- | --- |
| `_is_int` / `_is_number` / `_is_finite_number` | 类型判断，排除 `bool`；有限性检查排除 `NaN` / `inf` | base / chart / query |
| `_canvas_ref(value)` | 把整数或整数值浮点数解析为画布索引 | base / chart / query |
| `_parse_color(value)` | HEX / RGB / RGBA → `{r,g,b,a}` | chart / query |
| `_round_color_channel(value)` | 颜色通道四舍五入 | chart / query |
| `_ease(ease_type, t)` | 0-18 缓动求值；非法返回 `None` | chart / query |
| `_canvas_x_at(canvas, tick)` | 画布中线 x 插值 | chart / query |
| `_find_canvas(chart, index)` | 按索引找画布，支持负数，要求索引连续 | chart / query |
| `_bpm_seconds(chart)` | 构建 BPM 时间轴（要求 `time[0] == 0`） | chart / query |
| `_seconds_at(tick, ...)` | tick → 绝对秒数 | chart / query |
| `_seconds_to_tick(seconds, ...)` | 秒 → tick | chart / query |
| `_make_floor_plan(chart)` | **批量**计算全谱所有 `floorPosition`，只读 | base / chart |
| `_apply_floor_plan(plan)` | 把计划写回谱面 | base / chart |

查询模块保留的 `_get_bpm_timeline` / `_tick_at_realtime` 只是上述函数的
导入别名，不再有第二套实现。

### 4.2 base.py

| 函数 | 作用 | 何时调用 |
| --- | --- | --- |
| `_sanitize(value, spec)` | 按格式描述递归清洗，删除非法键/类型 | `load()`、`export()` |
| `_sanitize_note(value)` | 单独处理音符的 `otherInformations` | `_sanitize()` |
| `_prepare_chart(chart, basebpm)` | 清洗 + 补根结构 + 修主题数量 + 固定键顺序 | `load()`、`export()` |
| `_fix_theme_counts(chart)` | 补空数组并强制 `len(themes) == len(challengeTimes) + 1` | `_prepare_chart()` |
| `_walk_schema` / `_walk_note` | 递归收集键/类型/长度问题 | `check()` |
| `_check_lengths` | 数组最小/精确长度检查 | `check()` |
| `_check_values` | 值、范围、引用、时间、颜色、画布检查 | `check()` |
| `_check_floor_positions` | 用 `_make_floor_plan()` 对比 `floorPosition` | `check()` |
| `check(chart)` | 只读检查；返回路径对象或 `None` | 导出前、用户自检 |
| `refresh(chart, mode="all", type="all", startindex, endindex, startlineindex, endlineindex, isOnlyRefreshNaN=False)` | 按模式/类型/范围重排并重算 `floorPosition`；返回 `True` / `False` / `None` | 修复顺序、重算高度 |
| `_sorted_time_items` / `_refresh_add_sort` | 校验并按 `time` 稳定排序选中切片 | `refresh()` |
| `_refresh_range` / `_is_nan` | 解析闭区间索引、判断 `NaN` | `refresh()` |
| `_refresh_pending_changed` / `_refresh_apply_pending` | 判断并写回待更新的高度 | `refresh()` |
| `_fix_bpm_shifts` / `_fix_time_fields` / `_fix_ease_fields` / `_fix_colors` | 逐项修正 | `load()` |
| `_delete_invalid_notes` / `_normalize_canvases` / `_validate_lines` | 删除无效音符、画布规范化、删线/补默认判定环 | `load()` |
| `_normalize_for_load(chart)` | `load()` 的规范化总入口 | `load()` |
| `new()` | 生成最小合法谱面 | 创建谱面、`load()` 补默认值 |
| `load()` | 读文件 + 清洗 + 规范化 | 读取 |
| `export()` | `check()` 通过后紧凑输出；**不修改**输入 | 保存 |

`export()` 现在先调用 `check()`；任何问题都会导致 `False`。之后再执行原有的“清洗结果必须与输入完全相等”校验。

### 4.3 chart.py

#### 校验、索引与时间

| 函数 | 作用 | 何时调用 |
| --- | --- | --- |
| `mixColor(basecolor, covercolor)` | 按覆盖色公式混合 RGB；输出 alpha 取基础色 | 颜色预览、`splitColor()` |
| `splitColor(mixcolor, basecolor, covercolor)` | 校验或反推缺失颜色；覆盖色取最小 alpha 规范解 | 颜色拆分、调试 |
| `_ease_type(value, clamp)` | 校验缓动；`clamp=True` 时夹到 0-18 | 编辑函数的 `easetype` 参数 |
| `_node_time(chart, time, is_real_time)` | 把用户时间转换为 tick；`real_time` 时查 BPM 时间轴 | 画布/摄像机/线节点的 add/set/create |
| `_resolve_existing_index(index, length)` | 解析已存在元素的索引，支持负数 | set/delete 类函数 |
| `_resolve_insert_position(index, length)` | 解析插入位置，`None`=末尾，支持负数 | `addCanvas()`、`addLine()` |
| `_collect_canvas_references(lines)` | 收集线节点/音符中的画布引用 | `deleteCanvas()` |

#### 节点数组读取与校验

| 函数 | 作用 |
| --- | --- |
| `_canvas_position_points(canvas)` | 读取 `xPositionKeyPoints`，要求 `time` 非递减 |
| `_canvas_speed_points(canvas)` | 读取 `speedKeyPoints`，要求 `time` 非递减 |
| `_camera_key_points(camera, key)` | 读取摄像机关键点数组 |
| `_line_points(line)` | 读取 `linePoints`，要求 `time` 非递减 |
| `_validate_line_points(points)` | 校验线节点列表本身 |
| `_ring_points(line)` | 读取 `judgeRingColor`，要求 `time` 非递减 |
| `_line_colors(line)` | 读取 `lineColor`，要求 `time` 非递减 |
| `_make_color_point(time, startcolor, endcolor)` | 组装判定环/线色节点 |
| `_create_color_point(...)` | 按 tick/秒转换后组装颜色节点 |
| `_validate_line_point(point, require_floor=True)` | 校验单个线节点的完整结构；延迟模式可暂不要求高度 |
| `_validate_color_point(point)` | 校验单个判定环/线色节点 |
| `_notes(line)` | 读取 `notes`，要求 `time` 非递减 |
| `_parse_note_type(value)` | 把 `0/1/2` 或 `tap/drag/hold` 解析为类型 |
| `_validate_note(note, require_floor=True)` | 校验单个 Note 的结构；延迟模式可暂不要求高度 |
| `_line_note_position(chart, line_points, tick, is_head, calculate_floor=True)` | 按头/尾规则确定画布；`calculate_floor=False` 时高度返回 `NaN` |
| `_build_note(chart, points, head_time, note_type, tail_time, calculate_floor=True)` | 按已换算的 tick 构造 Note；可延迟高度计算 |
| `_line_point_spec(value, chart=None)` | 归一化线节点规格，不计算 `floorPosition` |
| `_note_spec(value, chart=None)` | 归一化 Note 规格，不计算画布/高度 |
| `_normalize_line_point(chart, value, calculate_floor=True)` | 归一化线节点并按需计算 `floorPosition` |
| `_normalize_color_node(chart, value)` | 归一化颜色节点 |
| `_normalize_note(chart, line_points, value, calculate_floor=True)` | 归一化 Note 并按需计算头部/Hold 尾部派生字段 |

#### 时间轴与高度

| 函数 | 作用 | 何时调用 |
| --- | --- | --- |
| `_canvas_floor_position_at(chart, canvas, tick)` | 计算单个画布在 tick 处的高度 | `_build_line_point()` |
| `_build_line_point(chart, time, x, canvas, ease, color, calculate_floor=True)` | 组装线节点并计算 `floorPosition`；可延迟高度计算 | `_normalize_line_point()`、`addLinePoint()`、`setLinePoint()` |

#### 重要：两种高度计算的差别

- `_make_floor_plan()`：从 `speedKeyPoints` 的 `time` / `value` **从头积分**，会修复缓存中不一致的 `floorPosition`。
- `_canvas_floor_position_at()`：使用 `speedKeyPoints[].floorPosition` 作为缓存基准，与 `getFloorPosition()` 和游戏内表现一致；不会修复旧缓存。

因此如果外部文件中的缓存本身有误差，`addLine()` / `addNote()` /
`setNote()` 会继承这个误差；`addLinePoint()` / `setLinePoint()` /
`deleteLinePoint()` 会调用 `_make_floor_plan()`，从零重算并顺手修正
缓存。需要单独归一化时，先触发一次 BPM 或画布流速编辑。

#### 摄像机

| 函数 | 作用 |
| --- | --- |
| `_camera_move(chart)` | 取出 `cameraMove` |
| `_add_camera_key_point(...)` | 摄像机关键点插入 |
| `_set_camera_key_point(...)` | 摄像机关键点修改/重排 |
| `_delete_camera_key_point(...)` | 摄像机关键点删除/重置 |

摄像机节点不影响音符高度，`floorPosition` 恒为 0，因此这些函数**不会**触发全谱重算。

#### 修改函数返回值

成功返回节点的修改/删除函数统一通过 `_export_*` 系列函数返回规格 Dict：

- 返回的是**修改前/删除前**对象的规格，与原有“返回原对象”语义一致；
- 规格不引用谱面内部对象，省略 `floorPosition` / `otherInformations`；
- 颜色字段为 RGBA 列表 `[r,g,b,a]`；
- `setRiztime()` / `deleteRiztime()` 返回合并后的 Riztime 规格，而不是
  `[主题, challengeTime]`；
- `addXXX()` / `addCanvas()` 成功返回插入索引，失败返回 `None`；`advanced.py`
  的批量插入、复制和缓动函数统一返回 `list[int]`：成功为 `[]`，失败为原始输入
  索引；整体输入非法为 `[-1]`。这些函数默认 `isFailAddAllowed=False`，任一失败
  会回退整批并返回 `[失败索引]`；`True` 时跳过失败元素并返回全部失败索引；
  `copyCamera()` 没有 `indexlist`，失败固定返回 `[0]`；
- `drawPolygon()` / `drawEllipse()` 成功返回新建线索引列表；输入非法或任一建线失败返回 `None`；
  两个绘制开关都为 `False` 时返回 `[]`。
- `getClosedRegion()` 成功返回所有有界闭合区域；每个区域是顺时针排列的线节点规格
  列表；没有闭合区域、输入非法或无法形成简单区域时返回 `None`。
- `setBaseBpm()` / `setDelay()` / `setFileVersion()` 仍返回原始标量值。

### 4.4 query.py

公开查询函数分为两类：

- **对象查询**：元数据、计数、数组/单对象；只做局部结构校验，不调用
  `check()`，返回规格 Dict，不引用谱面内部对象；颜色字段为 RGBA 列表。
- **计算查询**：时间、BPM、画布/摄像机位置、线段几何等。

对象查询统一使用 `getXxx(chart, startindex, endindex=None)`：

- `endindex=None`：单值，严格索引，返回 `dict | None`
- `endindex` 为整数：闭区间范围查询，返回 `list`，使用切片语义
- 查询全部使用 `getXxx(chart, 0, -1)`
- 返回规格省略 `floorPosition` / `otherInformations` 等派生字段
- `getNoteCount()` 按线索引范围累计每条线的 `notes` 列表长度

命名约定：

- 索引查询使用 `getCanvasPosition()`、`getCameraPosition()`、
  `getCameraScale()`、`getCanvasSpeed()`
- 对应时刻的计算值使用 `getCanvasPositionAt()`、
  `getCameraPositionAt()`、`getCameraScaleAt()`、`getCanvasSpeedAt()`

按时间查询 `getXxxByTime()` 只处理“点”元素：

- `starttime` 必须大于等于 `0.0`
- `endtime=None`：查询 `[starttime, +∞)`
- `endtime == starttime`：精确查找该时间点
- `endtime > starttime`：查询闭区间 `[starttime, endtime]`
- `indexlist` 过滤叶索引；`canvasindex` / `lineindex` 过滤父级
- 单层返回 `[index, ...]`，多层返回 `[[父索引, 子索引], ...]`
- 无匹配返回 `[]`，参数/结构非法返回 `None`
- Note 的 `type=3` / `"holdtail"` 使用
  `otherInformations[0]` 的 Hold 尾部时间

按颜色查询 `getXxxByColor()` 支持 theme、line point、ring color、
line color：

- `startcolor` / `endcolor` 支持 HEX、RGB(A) 列表
- `endcolor=None` 精确匹配 `startcolor`
- 逐通道闭区间；缺少 alpha 按 `255`
- Theme 每个颜色独立匹配，返回 `[themeindex, colorindex]`
- Ring / line color 的 `startColor` 或 `endColor` 任一匹配即可
- `getThemeByColor()` 的 `indexlist` 过滤主题索引；其余过滤叶索引
- 无匹配返回 `[]`，参数/结构非法返回 `None`

| 函数 | 作用 | 何时调用 |
| --- | --- | --- |
| `_get_bpm_timeline` / `_tick_at_realtime` | `_internal` 中 `_bpm_seconds` / `_seconds_to_tick` 的别名 | 所有 tick/秒换算 |
| `_bpm_floor_position(tick, ...)` | BPM 时间轴的绝对秒数 | `getFloorPosition(canvasindex=None)` |
| `_canvas_floor_position(chart, canvas, tick)` | 使用缓存流速节点计算画布高度 | `getFloorPosition(canvasindex=...)` |
| `_query_tick(chart, time, is_real_time)` | 单值时间 → tick | `getCanvasPositionAt()`、`getLinePosition()` |
| `_parse_range(value)` | 单值 / `[a,b]` / `None` 解析 | `getLineByPoint()`、`getLineByNote()` |
| `_query_tick_range(chart, value, is_real_time)` | 时间范围的 tick 化 | 同上 |
| `_value_matches` / `_time_matches` | 单值精确、闭区间、开放结束比较 | 同上 |
| `_line_x_at(line, tick)` | 线相对 x 与所在画布 | `getLinePosition()` |
| `_query_time_range` | start/end 时间校验与秒 → tick；`None`=开放结束，相等=精确 | 所有 `getXxxByTime()` |
| `_valid_index_list` / `_allowed_indices` | `indexlist` 叶索引过滤 | 所有 `getXxxByTime()` |
| `_selected_canvases` / `_selected_lines` | 画布/线父级过滤 | 按时间查询 |
| `_parse_note_by_time_type` | Note 类型解析（含 `holdtail`） | `getNoteByTime()` |
| `_parse_color_range` | 解析逐通道 RGBA 闭区间 | 所有 `getXxxByColor()` |
| `_color_in_range` | 判断单个 RGBA 是否在区间内 | 所有 `getXxxByColor()` |
| `_lerp_color(start, end, ratio)` | RGBA 四通道线性插值 | `getBaseColor()` / `getCoverColor()` |
| `_base_color_at_tick(chart, index, tick, position, is_absolute)` | 线节点基础色查询核心 | `getBaseColor()` / `getMixColor()` |
| `_cover_color_at_tick(chart, index, tick)` | 线色覆盖色查询核心 | `getCoverColor()` / `getMixColor()` |
| `_key_point_value_at(values, tick)` | 关键点数组缓动插值 | `getCameraPositionAt()` / `getCameraScaleAt()` |
| `_canvas_speed_at(values, tick)` | 画布流速阶梯取值，不插值 | `getCanvasSpeedAt()` |
| `_note_context(chart, lineindex, noteindex)` | 定位 Note 并返回头部时间、线节点与时间列表 | `getNotePosition()` / `getNoteCanvas()` |
| `_resolve_single_index` / `_resolve_range_indices` | 单值/范围索引解析 | `_query_items()` |
| `_query_items(items, start, end, builder)` | 单值/范围对象查询包装 | 所有对象查询函数 |
| `_key_point_spec` / `_color_change_spec` | 关键点/颜色规格化；颜色输出列表 | BPM、画布、摄像机、判定环、线色 |
| `_line_spec` / `_canvas_spec` / `_camera_spec` / `_riztime_specs` | 聚合对象规格化 | `getLine()` / `getCanvas()` / `getCamera()` / `getRiztime()` |

### 4.5 advanced.py

| 函数 | 作用 |
| --- | --- |
| `_as_indexed_specs(dictlist)` | 把单个规格 Dict 或列表统一为 `(原始索引, 规格)` 列表；非法返回 `None` |
| `_sorted_indexed_specs(specs, key)` | 按 `time` / `start` 稳定排序，同时收集时间字段非法的原始索引 |
| `_take_parent(spec, names)` | 读取并移除可选 `lineindex` / `canvasindex` 父索引 |
| `_rollback(actions)` | 按插入记录的逆序调用公开 delete 函数 |
| `_handle_failure(...)` | 原子模式回退整批并中止；允许失败模式只回退当前规格并记录索引 |
| `_add_line_point_spec` / `_add_color_spec` | 调用公开的 add 函数插入单个子节点 |
| `_add_canvas_positions` / `_add_canvas_speeds` | 添加画布后导入关键点；首个 `time=0` 节点替换默认节点 |
| `_resolve_canvas_index(chart, value)` | 解析并规范化画布索引，支持负数 |
| `addIsolatedNote(...)` | 用透明线节点和 `createNote()` 生成单 Note 辅助线 |

约束：

- 只调用 `base.py` / `chart.py` / `query.py` 的公开函数，不直接读写谱面内部数组。
- 父索引缺省为 `-1`（最后一条线/画布）。
- 除 `addLineByDict()` 外，批量输入先按时间稳定排序；不允许调用方自定义顺序。
- 所有 `addXxxByDict()` 的最后一个参数为 `isFailAddAllowed: bool = False`，统一返回
  `list[int]`。成功返回 `[]`；失败返回原始输入列表中的规格索引。
- `isFailAddAllowed=False` 为原子模式：任一规格失败时，按插入逆序回退本批全部
  节点，并返回 `[失败索引]`。
- `isFailAddAllowed=True`：失败规格自身已插入的部分也会回退，然后跳过该规格继续；
  已成功的其它规格保留，最终返回升序的失败索引列表。
- 原子回退 Riztime 时，如果原始谱面只有一个 `start == end` 的占位 Riztime，会在
  删除本批新增项后通过公开 `addRiztime()` 恢复该占位。
- `addBpmByDict()` 使用 `getBpmShift()` 的规格格式，`value` 默认按
  `bpmShifts[].value` 倍率处理；批内调用 `addBpmShift(..., isDelayCalculate=True)`，
  成功后执行一次 `refresh(mode="all", type="all")`，因为 BPM 会影响全谱所有
  `floorPosition`。
- 13 个 `copyXxx()` 位于 `advanced_copy.py`。复制前先快照源规格；原子模式先在
  `deepcopy(targetchart)` 上预演，成功后才写入真实目标，因此失败时目标不变。
- `copyLine()` 的 `replace` 会清空目标全部线；`copyCanvas()` 不允许 `replace`；
  `copyCamera()` 不允许 `part`。
- 带时间复制使用目标谱面 BPM 时间轴换算 `isRealOffsetTime`；`copyBpmShift()`
  结束后执行全谱 `refresh()`。
- 线子节点和画布子节点的破坏性复制在预演失败时整体回退；首节点不可删除的数组
  按“重置首节点 + 跳过最低索引的 time=0 节点 + set 首节点”处理。
- `addIsolatedNote()` 使用 `createNote()` / `createLinePoint()` /
  `createRingPoint()` 生成规格，再通过公开 `addLine()` 一次性写入；线节点和判定环
  均为透明色。Tap/Drag 的第二个节点时间固定为头部 tick `+ 1/16`。
- Hold 尾部正好落在节点时间时按左侧线段取画布，因此尾部画布与头部不同时，会在
  `endtime` 前插入一个尾前节点，保证尾部 Note 画布和位置正确。
- `position` / `endposition` 的绝对坐标通过公开 `getCanvasPositionAt()` 在对应
  tick 换算；`endposition=None` 沿用头部解析后的线位置，头部为绝对坐标时保持绝对
  x 不变。

### 4.6 advanced_ease.py

| 函数 | 作用 |
| --- | --- |
| `_ease_value(ease, t)` | 计算 `0..25` 或 Cubic Bezier 在归一化位置 `t` 的值 |
| `_make_samples(...)` | 根据 `inserttype` / `precision` 生成归一化插入位置 |
| `_normalized_curve_point(...)` | 构造时间 + 归一化数值/颜色通道的曲线点 |
| `_tick_values` / `_tick_counts` / `_can_insert` | 统计每个 tick 的节点数并执行 48 节点上限 |
| `_select_samples_for_capacity` | 按 tick 容量从采样点中按时间均匀挑选，避免整段丢弃 |
| `_select_samples` | `uniform` / `arc` / `curvature` 直接使用全部采样点；`recursion` / `priority` 才执行容量筛选 |
| `_run_ease_items(...)` | 原子/允许失败事务；预演成功后提交，BPM 额外执行全谱刷新 |
| `_line_entries` / `_canvas_entries` / `_flat_entries` | 解析与稳定倒序排列索引，快照当前/下一节点规格 |
| `_position_action` / `_step_action` / `_color_node_action` | 原生写入、`19..22` 拆分、`23..25`/Bezier 模拟及颜色/阶跃特殊值 |
| `setLinePointColorByList(...)` | 按索引区间和节点时间比例重设已有线节点颜色；不增删节点 |

约束与实现细节：

- 只调用 `base.py` / `chart.py` / `query.py` 的公开函数；索引解析、采样和事务均在
  本模块完成，不直接修改谱面内部数组。
- 有原生 `easeType` 的位置类节点（线节点位置、画布位置、摄像机位置/缩放）：
  - `0..18` 直接通过公开 set 函数写入。
  - `19..22` 在时间中点插入一个节点，精确拆成 `15+16`、`16+15`、`18+17`、`17+18`。
  - `23..25` 和 Cubic Bezier 通过采样插入节点，当前/插入节点写 `linear`。
- BPM、流速和颜色节点没有通用缓动字段：
  - BPM / 流速：`13` 为原生零阶保持，`14` 用 `math.nextafter()` 插入末端值；
    其它缓动按采样值插入节点。BPM 在所有实际修改后执行一次全谱 `refresh()`。
  - 判定环颜色 / 线色：`0` 原生线性，`13` 把当前 `endColor` 设为 `startColor`，
    `14` 用 `math.nextafter()` 插入末端颜色；其它缓动插入颜色节点并重接 `endColor`。
  - 线点颜色：`0` 仅把当前节点设为 `linear`；`13` 在下一节点前插入当前颜色；
    `14` 在当前节点后插入下一节点颜色；其它缓动插入颜色采样节点。当前和插入线
    节点统一写 `linear`，插入位置的 `xPosition` 从修改前的位置曲线采样。
- `uniform` / `arc` / `curvature` 的 `precision` 是正整数插入数量；
  `recursion` / `priority` 的 `precision` 是正浮点误差阈值。
- `arc` 使用时间 + 归一化数值/颜色通道的弧长；`curvature` 使用离散二阶差分
  曲率加权。`recursion` / `priority` 使用归一化曲线中点与弦线性插值点的距离
  与两端距离之比。
- `uniform` / `arc` / `curvature` 不限制插入数量，所有采样点都会尝试插入。
- `recursion` / `priority` 每个 tick 最多 48 个节点，整数时间节点同时计入左右
  相邻 tick；某个 tick 的采样点超过容量时，在该 tick 内按时间均匀挑选插入点，
  并继续处理后续 tick；已插入节点保留并视为成功。
- 批量索引按实际解析后的索引倒序处理，保证插入节点不会改变尚未处理的低索引；
  失败返回值仍使用原始 `indexlist` 位置。
- `isFailAddAllowed=False` 在 `deepcopy(chart)` 上预演全部索引后提交；`True` 逐索引
  预演并提交，失败索引不触碰真实谱面。
- BPM 的预演使用 `isDelayCalculate=True`，提交后统一全谱 `refresh()`，避免中途
  失效的 `floorPosition` 影响后续操作。
- `setLinePointColorByList()` 只修改区间内已有线节点的颜色，不调用 add/delete，
  也不改变节点 `easeType`、时间或位置。颜色归一化优先使用节点时间比例；首尾
  时间相同时退化为索引比例。先计算全部目标色，再逐点调用 `setLinePoint()`；
  若中途异常，按已改节点原色回滚。该函数成功返回 `[]`，失败返回 `None`。

### 4.7 advanced_draw.py

| 函数 | 作用 |
| --- | --- |
| `_parse_polygon(...)` | 校验线节点、凸包优先/输入顺序回退、保留顶点颜色 |
| `_convex_hull(...)` / `_polygon_area(...)` | 凸包构造、面积与退化检测 |
| `_is_simple_polygon(...)` / `_point_in_polygon(...)` | 简单多边形自交校验与一般点内判定 |
| `_line_intervals(...)` | 计算直线/射线在简单多边形内的多个可见区间 |
| `_build_gapped_line(...)` | 用一条线与透明节点表达多个可见区间和空隙；时间递减时预先反转记录顺序，避免硬切方向反转 |
| `_offset_polygon(...)` | 按有符号距离偏移凸/简单凹多边形，构造边框层 |
| `_border_layers(...)` | 把 `bordersize` 的 int/list 输入展开为层号集合 |
| `_boundary_samples(...)` | 从第一个顶点开始按边界弧长采样 `radialBorder` / `conicBorder` 射线 |
| `_ray_boundary(...)` | 从内部中心向多边形边界求射线交点 |
| `_gradient_color(...)` | 按颜色节点位置采样 RGBA；支持重复位置的颜色突变 |
| `_build_fill_linear(...)` | 线性填充线生成 |
| `_build_fill_radial_conic(...)` | 径向/锥形填充射线生成 |
| `_parse_holelist(...)` / `_mask_fill_lines(...)` | 孔洞校验与填充线孔洞遮罩 |
| `_hole_segment_ranges(...)` / `_mask_fill_line(...)` | 单条填充线的孔洞区间切分与 `holecolor` 硬切 |
| `_build_border(...)` | 多层闭合边框生成 |
| `_rotate_xy(...)` / `_ellipse_point(...)` | 椭圆局部坐标旋转与参数点计算 |
| `_ellipse_vertices(...)` / `_ellipse_low_high(...)` | 四个固定轴端点、时间最低/最高参数 |
| `_ellipse_color(...)` | 按上/右/下/左 `colorList` 做线性颜色插值 |
| `_sample_arc_s(...)` / `_ellipse_adaptive_s(...)` | 非 90° 半椭圆的 uniform/arc/curvature/recursion/priority 采样 |
| `_ellipse_force_mandatory(...)` | 把最低点、最高点与四个旋转轴端点强制并入半椭圆节点 |
| `_ellipse_limit_tick(...)` | recursion/priority 每个 tick 最多 48 个节点 |
| `_ellipse_border_layers_valid(...)` | 按 `lineprecision` 生成边框半轴并跳过退化方向 |
| `_build_ellipse_border_90(...)` / `_build_ellipse_border_curved(...)` | 90° 四线边框与非 90° 双半椭圆边框 |
| `_ellipse_polygon(...)` / `_ellipse_ray_parameter(...)` | 椭圆填充多边形与边界起始射线求交 |
| `_build_ellipse_fill(...)` / `_build_ellipse_conic_border_fill(...)` | 椭圆五种填充与锥形边界填充 |
| `_region_line_data(...)` | 读取并校验同一画布的线集合，保留 `lineindexlist` 顺序 |
| `_region_collect_intersections(...)` / `_region_build_graph(...)` | 线性/缓动线段求交、切分与平面图构建 |
| `_region_face_cycles(...)` / `_region_cycle_area(...)` | 半边遍历、闭合面循环与有界方向判定 |
| `_region_group_runs(...)` | 按原线方向合并连续半边，形成追踪段 |
| `_region_false_run(...)` | 不创建交点时的内部/外部节点替换 |
| `_region_true_run(...)` | 创建交点时的边界节点收集 |
| `_region_insert_fractions(...)` / `_region_expand_metas(...)` | 非线性缓动插入节点 |
| `_region_finish_metas(...)` | 去重、简单性校验、自交极角回退、顺时针排序与起点选择 |
| `getClosedRegion(...)` | 计算并返回所有有界闭合区域 |
| `_commit(...)` | 预演、延迟计算、实际建线与最终全谱 `refresh()` |

实现约束：

- 只调用 `base.py` / `chart.py` / `query.py` 的公开函数，不直接修改谱面内部数组。
- `pointlist` 只取 `time` / `xPosition` / `color`；忽略并重写 `canvasIndex` 与 `easeType`。
- 输入点优先尝试严格凸包；如果凸包不能包含全部输入点，则回退到输入顺序。
  凸包排序后会旋转到以输入第一个顶点为起点；回退的凹多边形必须通过简单多边形校验：
  无重复点、无零长度边、非相邻边不相交、面积非零。连续共线点允许。
- 线性填充使用 `normal=(cos(angle), sin(angle))` 作为颜色投影方向，填充线沿其垂直方向；
  从最小法向投影开始，以 `precision` 为间距裁剪。凹多边形会得到多个可见区间，
  用一条线加透明节点表达空隙。
- 径向/锥形填充使用 `angle=0` 指向屏幕上方、顺时针旋转的射线方向；
  径向颜色按 `半径 / 中心到最远顶点距离` 归一化，锥形颜色按从起始角开始的
  顺时针 360° 归一化。
- `drawPolygon()` 的 `timemultiple` 只缩放径向距离和锥形角度计算中的时间方向
  差值，用于颜色渐变；不缩放线性填充，也不改写输出节点的 `time`。默认 `1.65`。
- `drawEllipse()` 的有效 y 半轴为 `yLength * timemultiple`，几何、边框和填充都
  使用该值；`centerpoint["time"]` 本身不再额外缩放。默认 `1.65`。
- 当谱面流速为 `6.5`、画布流速为 `1` 时，`1.65` 约等于 x 轴与时间轴的视觉比例。
- `radialBorder` / `conicBorder` 仍从中心向边界建线，但射线起点改为沿多边形
  边界弧长采样：从第一个顶点开始，每 `precision` 距离取一点，下一次采样回到
  或越过第一点时停止；颜色规则分别沿用径向 / 锥形填充。
- 径向/锥形射线在简单凹多边形中也会用 `_line_intervals()` 找出多个可见区间；
  空隙用 alpha=0 节点硬切，仍是一条线。
- 边框偏移使用多边形绕向决定外法线；偏移后必须仍是简单多边形，且不能出现
  多个轮廓或负 `time`，否则跳过该层及同方向更远层。
- 径向射线的线节点包含中心、颜色节点位置和边界；边界颜色按实际半径单独采样。
- `drawPolygon()` 的 `holelist` 在填充线生成后统一做遮罩：逐条填充线与所有孔洞求交，
  孔洞内区间改为 `holecolor`，边界处加入相邻的可见色/孔洞色节点形成硬切。
  孔洞可超出外轮廓，超出部分没有填充线可遮罩；边框始终只由外轮廓生成。
  该遮罩与 `fillerstyle` 无关，因此五种填充方式都支持孔洞。判断线段是否完全
  位于孔洞内时使用严格内部判定，孔洞边界上的相切点不会导致整条填充线透明。
- `drawEllipse()` 的未旋转轴端点约定为上 `(x, time + yLength)`、右
  `(x + xLength, time)`、下 `(x, time - yLength)`、左
  `(x - xLength, time)`；`angle` 顺时针旋转。90° 倍数使用四个独立曲线，
  最低时间端到两个中间端点用 `easeType=16`（Out Circle），中间端点到最高
  时间端用 `easeType=15`（In Circle）。
- 非 90° 使用左右两条多节点半椭圆；最低点、最高点和四个旋转轴端点按参数
  落入的半弧强制加入。`uniform` / `arc` / `curvature` 的 `insertprecision`
  是每半弧总节点数（强制点已计入，过小时允许超出）；`recursion` / `priority`
  以弦高误差细分，并限制每 tick 最多 48 个节点。
- 椭圆边框第 `k` 层使用半轴 `xLength + k * lineprecision` /
  `yLength + k * lineprecision`；任一轴不大于 0 时跳过该层与同方向更远层。
- 椭圆填充使用高密度参数多边形复用线性/径向/锥形裁剪；`radialBorder` 从
  上方 0°、`conicBorder` 从 `fillerinfo` 角度开始，沿椭圆边界顺时针按
  `lineprecision` 采样射线。
- `getClosedRegion()` 对同一画布所选线构建平面图：线性模式直接使用节点直线段；
  插入模式下曲线段用实际 `easeType` 采样求交。交点、原节点和自交点切分线段后，
  用半边绕行提取闭合面；只保留有界方向，环形面拆成外圈/内圈独立区域。
- `isCreateCrossPoint=True` 时交点直接作为边界点；`False` 时交点由已有节点替换：
  交点节点优先；否则取交点内侧相邻节点，两个相邻交点之间的全部原节点保留；
  没有内侧节点时取交点的外侧相邻节点。替换后优先沿原线追踪，自交时对同一组
  替代节点按区域中心顺时针极角重排，仍不合法则失败。
- `isInsertPoint=True` 时交点/闭合判断使用实际缓动；插入节点不参与
  `isCreateCrossPoint=False` 的替换选择，而是在边界确定后按 `inserttype` /
  `precision` 对每个原节点区间补点。线性段不补点。
- `getClosedRegion()` 返回区域点统一 `easeType=0`，颜色优先复用原节点颜色；
  新交点取 `lineindexlist` 中靠前线的插值色，插入点取两端颜色线性插值。
  仅对射线边界时间小于中心时间、需要调整节点顺序的一侧，把重复位置颜色节点
  展开到极小的径向区间内，并让列表首个颜色靠近中心，避免同时间节点被
  `addLine()` 排序后造成突变位置偏移；同时把径向突变中心向多边形中心补偿
  `0.008` 个谱面坐标单位。其它方向保持原位置不变。
- `bordersize` 的 int 输入展开为 `0..n`（正数）或 `n..0`（负数）的全部层；
  list 输入精确指定层号；`[]` 无边框。默认使用 `[1]` 而不是第 0 层，避免边界线
  与填充线重合导致遮挡。层号正数向外、负数向内偏移 `layer * precision`。
  某一层偏移退化时，跳过该层及同方向更远的层。
  向外偏移若产生负 `time` 也按退化处理并停止更外层。每条多边形边独立成线。
- 生成线使用全透明判定环；横向线段允许同 `time` 的两个节点。
- 提交前在 `deepcopy(chart)` 上预演全部建线并执行一次 `refresh()`；成功后实际建线，
  最后统一执行 `refresh(mode="all", type="all")`。任一建线失败返回 `None`。

### 4.8 advanced_font.py

`drawText()` 使用可选依赖 `fontTools` / `shapely`；`drawThinText()` 还使用
`numpy` / `scikit-image`。对应依赖缺失时返回 `None`。

| 函数 | 作用 |
| --- | --- |
| `_FlattenPen(...)` | 将 TrueType 二次曲线 / CFF 三次曲线按容差展开为闭合折线轮廓 |
| `_glyph_infos(...)` | cmap 查字形、提取轮廓与 advance width |
| `_rings_to_geometry(...)` | 按嵌套深度区分外轮廓与孔洞，合并为 Shapely 几何 |
| `_layout_text_geometry(...)` | 统一计算字距、对齐、X/Y 缩放与谱面坐标几何 |
| `_text_border_layers(...)` | 按 `drawPolygon()` 语义展开 `bordersize` |
| `_text_border_geometries(...)` / `_offset_text_geometry(...)` | 按 `layer * precision` 生成每层偏移几何并跳过失效方向 |
| `_outline_edges(...)` / `_draw_outline(...)` | 将每层外轮廓和孔洞边界拆成普通线段并建线 |
| `_draw_parts(...)` | 将 Shapely Polygon/MultiPolygon 转成 `drawPolygon()` 调用 |
| `_rasterize_geometry(...)` | 将带孔几何按方形象素栅格化 |
| `_skeleton_pixel_paths(...)` | 将八连通骨架拆成端点/交叉点之间的路径 |
| `_simplify_path(...)` / `_simplify_closed_path(...)` | 用迭代 RDP 简化开放折线和闭环 |
| `_split_monotonic(...)` | 按时间极值拆分骨架折线；下降段反转后输出为 `time` 非递减的线 |
| `drawText(...)` | 单行字体排版、填充、线框、背景与整体提交/回退 |
| `drawThinText(...)` | 单行骨架线排版、平滑、拆分与整体提交/回退 |

实现约束：

- 只支持单个字体文件；可变字体有 `wght` 轴时应用 `weight`，静态字体忽略 `weight`。
- 字体 Y 向上对应谱面 `time` 增大，不做 Y 翻转；`time` 对齐字形填充轮廓底部。
- `fontsize` 控制 X 缩放；`timemultiple` 把 Y 缩放设为 X 缩放的倍数，且不改变
  `time` 定位值。
- `letterspacing` 按 em 解释，实际位移为 `letterspacing * fontsize`。
- 字形填充只使用 `linear`。`precision` 为填充线间距，同时作为边框层偏移距离；
  未提供时按 `max(0.001, fontsize * 0.01)` 自适应。一个字符的多个轮廓/组件分别
  转为带孔简单多边形，再调用 `drawPolygon()`；文字孔洞使用 `backgroundcolor`
  或透明色。
- 边框使用 `bordersize` 的 `drawPolygon()` 层号语义。每层几何由
  `glyph_geometry.buffer(layer * precision)` 生成；失效层及同方向更远层跳过。
  边框不再生成填充环，而是将每层外轮廓和孔洞边界拆成普通线段，调用 `addLine()`。
- `isFillGraph=True` 时填充、背景和线框可以同时绘制；`isFillGraph=False` 时跳过
  文字填充和背景，只绘制线框。
- 背景为“文字/线框外接框 + padding”的矩形减去文字填充几何；扣除后按多边形
  分量分别绘制，避免依赖谱面层级。`backgroundcolor` 同时用作文字孔洞填充色。
- `isFlipX=True` 以整段文字中心为轴镜像所有几何；`align` 先决定正常排版锚点。
- 任意多段绘制失败时删除本次已创建线并返回 `None`。
- `drawThinText()` 复用 `_layout_text_geometry()`，但 `time` 对齐最终骨架最低点，
  不绘制填充、边框或背景。
- 薄字栅格密度固定为 `fontsize / 192` 的方形象素；超长文字把最长边限制在
  2048 像素。`smoothness` 同时控制 RDP 容差和平滑次数，范围 `0..1`。
- 骨架按端点/交叉点拆成路径；闭环用分段 RDP 简化。非时间单调路径在时间极值处
  拆成多条单调段，下降段反转节点顺序后写入。
- 单像素骨架用短线段近似；所有细字线使用透明判定环并在最后统一 `refresh()`。
- 字体功能依赖可通过 `pyproject.toml` 的可选组 `font` 安装。

---

## 5. floorPosition 重算链路

```text
bPM + bpmShifts
      │
      ▼
  _bpm_seconds() ──► seconds(t)
      │
      ├──► canvasMoves[].speedKeyPoints[].floorPosition
      │           │
      │           ├──► lines[].linePoints[].floorPosition
      │           ├──► lines[].notes[].floorPosition
      │           └──► lines[].notes[].otherInformations[2]
      │
      └──► bpmShifts[].floorPosition（绝对秒数，另一套公式）
```

`_make_floor_plan()` 对 Note 的处理：

- 头部：`bisect_right(point_times, note.time) - 1`，正好在节点上时取右侧节点。
- Hold 尾部：`bisect_left(point_times, tail_time) - 1`，正好在节点上时取左侧节点；
  并**重新写入** `otherInformations[1]`（尾部画布）与 `[2]`（尾部高度）。
- 因此线节点变化后，Hold 尾部的画布也会被纠正到当前线段。

**必须调用 `_make_floor_plan()` 的情况**

| 操作 | 是否重算 |
| --- | --- |
| `addBpmShift()` / `setBpmShift()` / `deleteBpmShift()` | 是 |
| `setBaseBpm()` | 是（两种模式） |
| `addCanvasSpeed()` / `setCanvasSpeed()` / `deleteCanvasSpeed()` | 是 |
| `addCanvasPosition()` / `setCanvasPosition()` / `deleteCanvasPosition()` | 否（x 节点 `floorPosition` 恒为 0） |
| 所有摄像机函数 | 否（摄像机不参与高度） |
| `addLine()` | 是（只重算新线节点，不影响已有线） |
| `deleteLine()` | 否（只是删除容器） |
| `createRingPoint()` / `createLineColor()` | 否（颜色节点不参与高度） |
| `addRingPoint()` / `setRingPoint()` / `deleteRingPoint()` | 否（判定环颜色不参与高度） |
| `addLineColor()` / `setLineColor()` / `deleteLineColor()` | 否（线色覆盖不参与高度） |
| `createLinePoint()` / `createNote()` | 否（只生成规格 Dict，不计算高度） |
| `addLinePoint()` / `setLinePoint()` / `deleteLinePoint()` | 是（线段/画布可能变化，需同步 Note） |
| `addNote()` / `setNote()` | 只计算该 Note |
| `deleteNote()` | 否（其余 Note 高度不变） |

**原子性模式**

修改类函数通常遵循：

1. 校验所有参数与结构；
2. 在副本或临时列表中构造新数据；
3. 需要重算时先 `_make_floor_plan()`；
4. 计划失败 → 恢复原数据并返回失败；
5. 计划成功 → `_apply_floor_plan()`，再写回节点/列表。

新增修改函数时请沿用这个顺序，避免留下“改了一半”的谱面。

**不要重算的场景**

- 对**线节点**而言，只改 `xPosition`、`color`、`easeType` 不影响高度；但如果同时改了 `time` 或 `canvasIndex`，必须重算。
- 摄像机、画布横移、线色、判定环色都与 `floorPosition` 无关。

---

## 6. 索引、绑定与线段归属

### 6.1 画布索引

- 画布索引是 `canvasMoves[].index`，编辑类函数要求它**连续且等于列表位置**。
- `_find_canvas()` 支持负数：`-1` 表示最后一个画布。
- `addCanvas()` / `deleteCanvas()` 插入/删除后，会同步修改：
  - 后续画布的 `index`
  - `lines[].linePoints[].canvasIndex`
  - `lines[].notes[].otherInformations[1]`（Hold 尾部画布）

### 6.2 音符属于哪条画布

音符本身没有画布字段。头部与 Hold 尾部使用不同的边界规则：

```text
头部：
  point[i].time <= note.time < point[i+1].time  → point[i].canvasIndex
  note.time == point[j].time                    → point[j].canvasIndex
  note.time == 最后一个节点时间                  → 最后一个节点自己的画布

尾部：
  point[i].time < tail.time <= point[i+1].time  → point[i].canvasIndex
  tail.time == point[j].time                    → point[j-1].canvasIndex
  tail.time == 最后一个节点时间                  → 倒数第二个节点（最后一段）的画布
```

实现：

- 头部：`bisect_right(times, t) - 1`
- 尾部：`bisect_left(times, t) - 1`

注意二者在节点时间上的结果正好相反。`addNote()` / `setNote()` 与
`_make_floor_plan()` 使用同一套规则。`getNoteCanvas()` 的头部查询使用
头部规则；Hold 尾部直接返回 `otherInformations[1]` 中记录的绑定画布。

### 6.3 时间相同的节点

- `addXxx()`：新节点插到已有同时间节点**之后**。
- 查询正好落在同时间节点上：取**最右侧**节点。
- 查询在重复节点**之前**：插值目标是该组重复节点中的**第一个**。
- 查询在重复节点**之后**：从该组重复节点中的**最后一个**继续插值。

这样能正确表达“同一时刻的横向跳变”。

---

## 7. 查询实现细节

### getBpmAt / getSecondsAt / getTickAt

- 三者都要求 `_get_bpm_timeline()` 成功，即 `bpmShifts[0].time == 0.0`
  且 BPM 节点按时间非递减。
- `getBpmAt()` 返回 `bPM * bpmShifts[].value`；用二分查找取 tick
  之前（含等于）的最后一个 BPM 节点，晚于最后节点时保持最后值。
- `getBpmAt(..., isRealTime=True)` 先通过 `_tick_at_realtime()` 把秒数
  换算成 tick，再查询 BPM。
- `getSecondsAt()` 使用 `_seconds_at()` 计算绝对秒数。
- `getTickAt()` 使用 `_tick_at_realtime()`，是 `getSecondsAt()` 的逆运算。
- 两者都要求输入非负；晚于最后一个节点时按最后一个 BPM 节点继续外推。

### getCanvasSpeedAt

- 使用 `_canvas_speed_at()`，先通过 `_key_point_specs()` 校验数组。
- 画布流速是阶梯式突变，**不使用 `easeType` 插值**；节点之间保持左侧
  节点的值，直到下一个节点时间才切换。
- 查询时间早于首个关键点 → `None`；晚于最后一个关键点 → 保持最后值。
- 正好命中节点 → 取该节点值；同时间多个节点 → 取最右侧节点。
- `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。

### getCameraPositionAt / getCameraScaleAt

- 两者共用 `_key_point_value_at()`，先通过 `_key_point_specs()` 校验数组。
- 查询时间早于首个关键点 → `None`；晚于最后一个关键点 → 保持最后值。
- 正好命中节点 → 取该节点值；同时间多个节点 → 取最右侧节点。
- 节点之间 → 使用左侧节点的 `easeType` 对值做缓动插值。
- `isRealTime=True` 时先用 BPM 时间轴把秒数换算为 tick。

### getCanvasPosition

- 按 `xPositionKeyPoints` 插值。
- 查询时间晚于最后一个关键点 → 保持最后值。
- 早于第一个关键点 → `None`。
- 同一时间有多个关键点 → 取最右侧。

### getLinePosition

- 先定位线段：`bisect_right(times, tick) - 1`。
- 正好在节点上 → 直接返回该节点 x（重复时最右侧）。
- 线段之间 → 用左侧节点的 `easeType` 插值。
- 查询时间超出 `[首节点, 末节点]` → `None`。
- `isAbsolutePosition=True` → 加上该线段所属画布在该 tick 的 `getCanvasPositionAt()`。

### getLineByPoint

- `position` / `time` 支持单值、闭区间、`None`。
- `isAbsolutePosition=True` 时，**每个候选节点用自己的 `time`** 查询所在画布的 `getCanvasPositionAt()`。
- `color` 按 RGBA 精确比较，未给 alpha 视为 255。
- 没有匹配节点返回 `[]`；参数或结构非法返回 `None`。

### getLineByNote

- 先用时间与类型筛选 Note。
- 再用 `getLinePosition()` 计算 Note 时刻的线 x 坐标，与 `position` 比较。
- Hold 只用头部时间。
- 绝对坐标时同样走 `getLinePosition(..., isAbsolutePosition=True)`。
- 没有匹配 Note 返回 `[]`；参数或结构非法返回 `None`。

### getLineTimeRange

- 用 `_line_points_spec()` 校验线节点。
- 返回首尾节点 tick；`isRealTime=True` 时用 `getSecondsAt()` 换算成秒。
- 线结构非法、索引不存在或秒换算失败 → `None`。

### getNotePosition

- 用 `_note_context()` 定位 Note，校验类型、头部时间和线节点。
- 返回 `getLinePosition(chart, lineindex, head_time, isAbsolutePosition=...)`。
- Hold 只使用头部时间。

### getNoteCanvas

- 用 `_note_context()` 定位 Note。
- 默认按头部规则 `bisect_right(times, head_time) - 1` 取线节点画布。
- `isHoldTail=True` 且 Note 是 Hold 时，读取
  `otherInformations[1]` 的绑定画布，并校验尾部时间、画布索引和画布存在性。
- 非 Hold 忽略 `isHoldTail`，仍返回头部画布。

### getBaseColor

- 先用 `_line_points_spec()` 校验线节点，并检查 tick 在
  `[首节点时间, 末节点时间]` 内。
- 查询时间没有节点：二分查找定位到右侧节点，左侧取 `index - 1`。
  因此进入重复节点组时目标组内**第一个**节点，离开重复节点组时从
  组内**最后一个**节点继续插值。
- 查询时间正好一个节点：直接返回该节点颜色。
- 查询时间有多个节点：用左右二分边界圈出同时间节点组；必须提供
  `position`，按存储顺序构造同时间横向线段。
  - 每段在 x 区间内按比例对 RGBA 插值；
  - 后面的段覆盖前面的段，保留最后一个包含 `position` 的段；
  - 零宽段按后一个节点颜色处理。
- `isAbsolutePosition=True` 时，每个线段端点分别加上自身
  `canvasIndex` 对应画布在该 tick 的 `getCanvasPositionAt()`。
- 颜色插值不读取 `easeType`，统一逐通道线性插值并四舍五入。

### getCoverColor

- `lineColor` 用 `_color_change_specs(..., non_empty=True)` 校验，空数组
  直接返回 `None`。
- tick 只要求非负，不使用引导线头尾时间做范围限制。
- 早于首节点 → 首节点 `startColor`。
- 正好命中节点或晚于末节点 → 对应节点（重复时最右）的 `startColor`。
- 中间段 → 当前节点 `startColor` 到 `endColor`，按到下一节点的时间比例
  插值。
- 因此最后一个节点的 `endColor` 不会出现在查询结果中。

### getMixColor

- `currenttime` / `querytime` 分别用对应的 `isReal...` 参数换算为 tick。
- `querytime=None` 时直接复用 `currenttime` 的 tick。
- 基础色走 `_base_color_at_tick()`，覆盖色走 `_cover_color_at_tick()`。
- 任一结果为空则返回 `None`；否则调用 `chart.mixColor()`。
- 输出 alpha 取基础色 alpha，覆盖色 alpha 只参与 RGB 混合。

### 比较精度

单值查询使用**精确相等**（`==`）。原谱中的坐标是 float32 量级，若用计算结果查询，建议用 `[a, b]` 区间而不是单值。

---

## 8. 校验与错误处理约定

- **数字类型**：`bool` 永远不被当作 `int` / `float`。
- **有限性**：编辑函数使用 `_is_finite_number()` 排除 `NaN` / `inf`。
- **失败返回**：
  - 添加类 → `False`
  - 修改/删除类 → `None`
  - 查询类 → `None`
  - 列表查询无结果 → `None`（不是空列表）
- **不部分修改**：先校验、后写入；重算失败会回滚。
- **`load()` 宽松，`export()` 严格**：
  - `load()` 删除非法键、补默认值，并执行 12 项规范化；
  - `export()` 先 `check()`，再要求输入已完全符合标准结构。
- **`load()` 规范化顺序**：
  1. `bPM <= 0` → 失败（除非 `basebpm` 提供正数）；
  2. `bpmShifts[].value <= 0` → `1.0`；
  3. 负数时间 → `0.0`；
  4. `easeType` 夹取 0-18；
  5. 颜色通道夹取 0-255；
  6. 删除 `type` 不在 0-2 的音符；
  7. 画布去重（保留第一个）、负索引移到末尾、重编号 0..n-1；
  8. 删除 `<2` 个线节点、引用不存在画布、音符头/尾超出线范围的线；
     空的 `judgeRingColor` 补一个默认节点（`time=首节点时间`、RGBA 全 0）；
  9. 尝试 `_make_floor_plan()` 并写回（失败则跳过）。
- **`check()` 的 `floorPosition` 检查**：只有 `_make_floor_plan()` 能成功时才检查；
  误差范围 `1e-2`。BPM/画布结构有问题时自动跳过。
- **`refresh()` 的 `floorPosition` 比较**：按精确数值比较；按 `mode` / `type`
  选择对象，`all` 先排序再计算，`floorPosition` 只算不排序，`order` 只排序。
  有变化返回 `True`，无变化 `False`，无法重算 `None` 并恢复顺序。
- **`refresh()` 索引范围**：`"all"` / `"camera"` 忽略索引；`linePoints` /
  `notes` / `judgeRingColor` / `lineColor` 用 `startlineindex` / `endlineindex`
  选线、用 `startindex` / `endindex` 选节点；其余类型用后两者选自身数组。
  负索引从末尾计算，越界部分忽略，空交集不执行。
- **`refresh()` 排序范围**：只对选中切片排序；`"lines"` / `"canvas"` 选择父对象后
  排序其完整子数组，`"all"` / `"camera"` 排序完整数组。
- **`isOnlyRefreshNaN=True`**：只写回选中的 `NaN` 高度；`mode="order"` 时忽略。
- **`isDelayCalculate=True`**：跳过 `floorPosition` 计算/全谱重算；新增或
  修改节点的高度写为 `NaN`，必须随后调用 `refresh()`。仅用于批量修改优化。
- **`check()` 路径**：`unexpectedParts` / `missingParts` / `errorValues`，
  只定位到最顶层非法项；数组元素级缺失/多余也会报告。
- **BPM 0 节点**：除 `addBpmShift()` 的补节点入口外，所有依赖 BPM 时间轴的操作都要求 `bpmShifts[0].time == 0.0`。
- **画布索引连续**：编辑函数与大部分查询函数（`getCanvasPositionAt()`、`getLinePosition()`、`getLineByPoint()`）基于 `_find_canvas()`，索引不连续会失败；`getFloorPosition()` 例外，它按 `index` 字段搜索。

---

## 9. 常见工作流

### 9.1 从零建立谱面

```python
from rizChartFunction import (
    new, createLinePoint, createRingPoint, addLine, export,
)

chart = new(175.0)

p0 = createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
p4 = createLinePoint(4.0, 1.0, 0, 5, "#FFFFFF")
ring = createRingPoint(0.0, "#FFFFFF")

addLine(chart, [p0, p4], ring)

export(chart, "chart.json")
```

### 9.2 修改 BPM 后自动重算

```python
from rizChartFunction import addBpmShift, setBaseBpm

addBpmShift(chart, 200.0, 16.0)      # tick 16 变为 200 BPM
setBaseBpm(chart, 180.0, isFixedBpm=True)  # 保持实际 BPM
```

两者都会触发 `_make_floor_plan()`，画布、线、音符、Hold 尾部一起更新。

### 9.3 添加画布流速

```python
from rizChartFunction import addCanvasSpeed

addCanvasSpeed(chart, 0, 8.0, 1.5)
# 自动重算整份谱面的相关 floorPosition（包括该画布与所有线/音符高度）
```

### 9.4 修复缺少 0 节点的时间轴

```python
from rizChartFunction import addBpmShift

addBpmShift(chart, chart["bPM"], 0.0)  # 补一个 1 倍节点
```

之后 `getFloorPosition()`、`setBaseBpm()` 等才能正常工作。

---

## 10. 扩展指南

### 新增一个修改函数

1. 明确它是否改变高度（BPM、画布流速、线节点 time/canvas）。
2. 校验参数和结构；不要在校验完成前修改谱面。
3. 在副本/临时列表上构造结果。
4. 需要全局重算时：
   ```python
   plan = _make_floor_plan(chart)
   if plan is None:
       # 回滚临时结果
       return None
   _apply_floor_plan(plan)
   ```
5. 单节点重算用 `_build_line_point()` / `_canvas_floor_position_at()`。
6. 成功返回原对象的规格 Dict（颜色为 RGBA 列表）或插入索引，失败按既有
   约定返回 `None`。

### 新增一个查询函数

优先复用：

- `_query_tick()` / `_query_tick_range()`：时间换算
- `_ease()`：缓动
- `_canvas_x_at()` / `_line_x_at()`：坐标插值
- `_parse_range()`：单值/区间参数

### 新增节点类型

如果它影响高度：

- 参与 `_make_floor_plan()` 的校验与计划；
- 明确它的 `floorPosition` 是绝对秒数还是画布高度；
- 明确重复时间的处理规则。

如果只是横向/颜色属性：

- 不需要进入 `_make_floor_plan()`；
- 查询端单独实现插值。

### 音符编辑

已实现 `addNote()` / `setNote()` / `deleteNote()`。扩展时注意：

- 头部用 `bisect_right - 1`，尾部用 `bisect_left - 1`，两者在节点时间上相反；
- Tap/Drag 的 `otherInformations` 保留原值（可能是 `[]`、省略或 3 个占位数字）；
- Hold→Tap/Drag 清空 `otherInformations`；Tap/Drag→Hold 必须提供 `endtime`；
- Hold 必须同步 `[tail_time, tail_canvas, tail_fp]`；
- 改动线节点后必须调用 `_make_floor_plan()`，让 Note 头部与 Hold 尾部重新归属；
- 同线同时间的 Note 允许存在，插入时放在已有 Note 之后。

### 测试建议

可用样本：

- `E:\RizChartTool\input\20260109\Chart_EZ` / `Chart_HD` / `Chart_IN`（官方格式）
- `E:\riz谱\AP\Chart_IN.json`（自制格式，节点数量大，适合压力测试）

回归重点：

1. 所有 `floorPosition` 与独立积分脚本一致；
2. 同时间节点的插入/查询顺序；
3. 失败路径不修改谱面；
4. `export()` → `load()` 往返稳定；
5. 无 `time=0.0` BPM 节点的谱面（IN）按严格规则失败。

---

## 11. 已知限制与注意事项

- **IN 谱面**的首个 BPM 节点在 `time=4.0`，因此 BPM 相关操作、画布高度查询、`addNote()`、`addLine()` 等默认会失败；需要先 `addBpmShift(chart, value, 0.0)`。若设置 `isDelayCalculate=True`，这些单节点/单线操作会跳过高度计算并写入 `NaN`，随后执行 `refresh()`。`createLinePoint()` / `createNote()` 的 tick 规格可以正常生成，因为不再计算高度。
- `addNote()` / `setNote()` 要求线的 `linePoints` 至少 2 个且时间非递减。
- 同线同时间的 Note 允许存在，插入时放在已有 Note 之后。
- `notes` 可以为空；`deleteNote()` 允许删除最后一个 Note。
- Hold 的尾部画布由尾部时间与线节点重新推导，不完全信任文件里已有的 `otherInformations[1]`。
- `setNote()` 中 Tap/Drag 保持 Tap/Drag 时会保留旧 `otherInformations`（包括 3 个占位数字）。
- `addLine()` 要求 `linepointslist` 长度 **≥ 2**，并且 `ringpointslist` 至少包含 1 个判定环颜色节点；`notes` / `linecolors` 可选。
- `addLine()` 默认重算新线的 `linePoints[].floorPosition`、`notes[].floorPosition` 与 Hold 尾部画布/高度；输入中的 `floorPosition` 只做格式校验，不参与结果。因此默认要求 `time=0.0` 处有 BPM 节点；`isDelayCalculate=True` 时新节点高度写为 `NaN`，不要求能完成高度计算。
- `deleteLinePoint()` 在线只剩 2 个或更少节点时拒绝删除。
- `deleteRingPoint()` 在线只剩 1 个判定环颜色节点时拒绝删除。
- `setRingPoint()` / `setLineColor()` 的 `endcolor=None` 表示**不修改**，与 `addRingPoint()` / `addLineColor()` / `createRingPoint()` 的“与起始颜色相同”不同。
- `lineColor` 可以为空；`deleteLineColor()` 允许删除最后一个节点。但
  `getCoverColor()` / `getMixColor()` 把空 `lineColor` 视为查询失败，
  返回 `None`。
- `load()` 会删除 `linePoints` 少于 2 个的线。
- `load()` 对空的 `judgeRingColor` **不再删除线**，而是补一个
  `time=首节点时间`、RGBA 全 0 的默认判定环节点。官方谱面中的
  无环装饰线因此会保留，线索引基本不变。
- `load()` 对重复画布索引保留第一个；负索引画布移到末尾并统一重编号，
  同时更新 `linePoints[].canvasIndex` 与 Hold 尾部画布。
- `load()` 在 `bPM <= 0` 时失败，除非显式传入正数 `basebpm`。
- `load()` 只有在 BPM/画布结构足够完整、`_make_floor_plan()` 能成功时
  才重算 `floorPosition`；例如 `bpmShifts[0].time != 0` 的谱面会跳过。
- `check()` 的 `floorPosition` 误差范围为 `1e-2`。
- `addLinePoint()` 默认会因为画布首个 `speedKeyPoint` 晚于目标时间而失败（无法计算高度）；`isDelayCalculate=True` 时跳过高度计算，可先插入再 `refresh()`。
- `addLinePoint(..., isAbsolutePosition=True)` 会先减去目标时刻该节点画布的
  `_canvas_x_at()` 再写入相对 `xPosition`；画布 x 无法计算时返回 `None`，
  且不修改谱面。
- `splitColor()` 的覆盖色反推不唯一；返回的是最小 alpha 的规范解，不保证
  等于最初的覆盖色。覆盖色 alpha 为 255 时基础色 RGB 也不唯一，返回
  混合色本身作为规范基础色。
- `export()` 非常严格：缺少默认值、存在多余键、主题数量不匹配都会返回 `False`。
- `load()` 会删除 `songsName`、`offset` 等官方专有字段（面向自制谱面）。
- `load()` 的 `_fix_theme_counts()` 会**删除**多余的 theme / challengeTime，并在数组为空时补默认值。
- 查询单值使用精确相等；需要容差时用区间。
- 原谱 `floorPosition` 常是 float32 精度，`_make_floor_plan()` 重算后是 float64，数值可能有约 `1e-3` 的差异。
- `_canvas_floor_position_at()` / `getFloorPosition()` 使用缓存的关键点 `floorPosition`；缓存不一致时不会自动修复。
- `getCanvasPositionAt()` 在第一个关键点之前返回 `None`，在最后一个之后保持最后值。
- 摄像机、画布横移、线色、判定环色都不参与 `floorPosition`。
- 编辑类函数与 `getCanvasPositionAt()` / `getLinePosition()` / `getLineByPoint()` 的画布查找要求 `canvasMoves[].index` 连续；`getFloorPosition()` 按索引字段搜索，不要求连续。
