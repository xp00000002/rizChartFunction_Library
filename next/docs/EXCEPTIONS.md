# 自定义异常

[← 返回总览](README.md)

`rizChartFunction` 的所有可失败公开函数都额外接受一个 **keyword-only** 参数：

```python
isReturnException: bool = False
```

它不改变成功路径。默认 `False` 时，函数仍然返回原有失败值；设为 `True` 时，失败改为抛出 `RizChartError` 的子类。各函数的文档签名和参数表均列出这个 keyword-only 参数。

```python
from rizChartFunction import copyLine
from rizChartFunction.exceptions import RizChartBatchError

try:
    copyLine(chart, 99, isReturnException=True)
except RizChartBatchError as error:
    print(error.failed_indices)
    print(error.rolled_back)
```

异常类定义在独立模块中：

```python
from rizChartFunction.exceptions import RizChartError
```

异常类不计入包根的“函数数量”；包根仍然只导出函数。

## 基本语义

### `isReturnException=False`

保持兼容行为：

- 失败返回 `None`、`False`、`[-1]` 或失败索引列表；
- `getXYRatio()` 的除零仍返回 `NaN`。

### `isReturnException=True`

- 失败时抛出 `RizChartError` 子类。
- 有 `isFailAddAllowed` 的函数会强制按 `isFailAddAllowed=False` 执行，即整批原子处理。
- 先完成回退（或确认没有部分修改），再抛出异常。
- 成功结果不抛异常。

### 空结果 `[]` 不抛异常

以下情况仍然是成功：

- 批量插入、复制、缓动全部成功；
- 查询没有匹配对象；
- 绘图函数没有请求输出；
- 空字符串；
- `transColor()` 没有匹配颜色。

如需把“请求有输出但结果为空”视为失败，请由调用方自行检查返回值。库保留 `RizChartNoEffectError`，但默认不启用。

### 特殊函数

| 函数 | `isReturnException=True` 的行为 |
| --- | --- |
| `check()` | 发现问题时抛 `RizChartValidationError`；`.issues` 保存原问题 Dict。 |
| `export()` | 失败时抛 `RizChartExportError`。 |
| `splitColor()` | 输入非法抛 `RizChartColorError`；混合结果不匹配抛 `RizChartColorMismatchError`。 |
| `getXYRatio()` | `NaN` 除零抛 `RizChartDivisionByZeroError`；参数非法抛参数类异常。 |
| `getXYRatioByChart()` | 同上，并可能抛 BPM/画布相关异常。 |
| `refresh()` | 返回 `False` 表示成功但没有变化，不抛异常；失败才抛异常。 |

## 异常层次

```text
RizChartError
├── RizChartArgumentError
│   ├── RizChartTypeError
│   ├── RizChartValueError
│   ├── RizChartIndexError
│   └── RizChartRangeError
├── RizChartStructureError
├── RizChartReferenceError
├── RizChartTimeError
├── RizChartBpmError
├── RizChartCanvasError
├── RizChartEaseError
├── RizChartColorError
│   └── RizChartColorMismatchError
├── RizChartThemeError
├── RizChartFloorPositionError
├── RizChartMathError
│   └── RizChartDivisionByZeroError
├── RizChartBatchError
├── RizChartIOError
│   ├── RizChartLoadError
│   └── RizChartExportError
├── RizChartValidationError
├── RizChartTransactionError
├── RizChartDrawingError
│   ├── RizChartGeometryError
│   ├── RizChartFontError
│   └── RizChartTextLayoutError
└── RizChartNoEffectError
```

## 公共字段

所有异常继承 `RizChartError`，公共属性：

| 属性 | 说明 |
| --- | --- |
| `function` | 失败函数名 |
| `code` | 稳定错误码，例如 `RCF-INDEX` |
| `context` | 相关参数、索引、时间等结构化上下文 |
| `cause` | 底层异常或原始失败对象；可能为 `None` |

异常消息使用中文；机器处理应优先读取属性而不是解析消息。

## 异常类

| 异常类 | 父类 | 错误码 | 自定义信息 | 典型场景 |
| --- | --- | --- | --- | --- |
| `RizChartError` | `Exception` | `RCF` | `function`, `code`, `context`, `cause` | 所有库异常的根类。 |
| `RizChartArgumentError` | `RizChartError` | `RCF-ARG` | `parameter` | 参数类异常父类，通常不直接抛出。 |
| `RizChartTypeError` | `RizChartArgumentError` | `RCF-TYPE` | `parameter`, `expected_type`, `actual_type`, `value` | 参数类型错误、`bool` 当数字、`chart` 不是 dict。 |
| `RizChartValueError` | `RizChartArgumentError` | `RCF-VALUE` | `parameter`, `value`, `allowed`, `reason` | 非有限数、负数、非正数、非法模式。 |
| `RizChartIndexError` | `RizChartArgumentError` | `RCF-INDEX` | `kind`, `index`, `resolved_index`, `length` | 索引越界或负数索引解析后越界。 |
| `RizChartRangeError` | `RizChartArgumentError` | `RCF-RANGE` | `start`, `end`, `minimum`, `maximum` | 起止时间/范围反转或非法。 |
| `RizChartStructureError` | `RizChartError` | `RCF-STRUCTURE` | `path`, `expected`, `actual`, `object_name` | 缺少键、嵌套类型错误、数组长度错误、顺序非法。 |
| `RizChartReferenceError` | `RizChartError` | `RCF-REFERENCE` | `kind`, `index`, `parent`, `path` | 线、画布、主题、Note 或父节点不存在。 |
| `RizChartTimeError` | `RizChartError` | `RCF-TIME` | `time`, `starttime`, `endtime`, `is_real`, `domain` | 时间为负、越界或查询时间非法。 |
| `RizChartBpmError` | `RizChartError` | `RCF-BPM` | `time`, `bpm`, `reason`, `bpm_shift_index` | 缺少 `time=0.0` BPM 节点、BPM 非正、tick/秒换算失败。 |
| `RizChartCanvasError` | `RizChartError` | `RCF-CANVAS` | `canvasindex`, `time`, `reason`, `path` | 画布不存在、画布 x 无法计算、关键点插值失败。 |
| `RizChartEaseError` | `RizChartError` | `RCF-EASE` | `easetype`, `allowed`, `path` | 缓动值非法或没有可用缓动区间。 |
| `RizChartColorError` | `RizChartError` | `RCF-COLOR` | `color`, `path`, `channel`, `expected` | HEX/RGB(A) 非法、通道越界、颜色数量不匹配。 |
| `RizChartColorMismatchError` | `RizChartColorError` | `RCF-COLOR-MISMATCH` | `mixcolor`, `basecolor`, `covercolor` | `splitColor()` 的混合结果不匹配。 |
| `RizChartThemeError` | `RizChartError` | `RCF-THEME` | `themeindex`, `colorindex`, `path`, `reason` | 主题索引或主题颜色结构非法。 |
| `RizChartFloorPositionError` | `RizChartError` | `RCF-FLOOR` | `tick`, `time`, `canvasindex`, `path`, `reason` | `floorPosition` 无法计算或误差超限。 |
| `RizChartMathError` | `RizChartError` | `RCF-MATH` | `expression`, `operands`, `function` | 其他数学失败。 |
| `RizChartDivisionByZeroError` | `RizChartMathError` | `RCF-DIV-ZERO` | `numerator`, `denominator`, `expression` | `getXYRatio()` 的除零 `NaN`。 |
| `RizChartBatchError` | `RizChartError` | `RCF-BATCH` | `failed_indices`, `errors`, `rolled_back`, `function` | 高级批量函数元素失败。 |
| `RizChartIOError` | `RizChartError` | `RCF-IO` | `filename`, `reason`, `cause` | 文件读写异常父类。 |
| `RizChartLoadError` | `RizChartIOError` | `RCF-LOAD` | `filename`, `reason`, `cause` | 文件、JSON 或结构读取失败。 |
| `RizChartExportError` | `RizChartIOError` | `RCF-EXPORT` | `filename`, `reason`, `issues` | 校验、路径或序列化失败。 |
| `RizChartValidationError` | `RizChartError` | `RCF-VALIDATION` | `issues` | `check()` 发现问题。 |
| `RizChartTransactionError` | `RizChartError` | `RCF-TRANSACTION` | `rollback_succeeded`, `cause`, `applied_changes` | 原子操作回退不完整。 |
| `RizChartDrawingError` | `RizChartError` | `RCF-DRAWING` | `operation`, `path`, `cause` | 绘图整体失败。 |
| `RizChartGeometryError` | `RizChartDrawingError` | `RCF-GEOMETRY` | `lineindexlist`, `region_index`, `reason`, `path` | 多边形、椭圆、闭合区域失败。 |
| `RizChartFontError` | `RizChartDrawingError` | `RCF-FONT` | `fontpath`, `character`, `codepoint`, `text_index`, `reason` | 字体不存在、格式不支持、缺字形。 |
| `RizChartTextLayoutError` | `RizChartDrawingError` | `RCF-TEXT-LAYOUT` | `text`, `fontsize`, `align`, `letterspacing`, `reason` | 换行、字距、对齐或边框布局失败。 |
| `RizChartNoEffectError` | `RizChartError` | `RCF-NO-EFFECT` | `operation`, `reason` | 预留；默认不用于空结果。 |

## 失败原因到异常类

| 失败原因 | 首选异常类 |
| --- | --- |
| `chart` 不是 dict | `RizChartTypeError` |
| 参数类型错误、`bool` 当数字 | `RizChartTypeError` |
| 非有限数、负数、非正数、非法模式 | `RizChartValueError` |
| 索引不是 int | `RizChartTypeError` |
| 索引越界或负数解析后越界 | `RizChartIndexError` |
| 起止范围反转 | `RizChartRangeError` |
| 缺少键、嵌套类型错误、数组长度错误、顺序错误 | `RizChartStructureError` |
| 引用对象不存在 | `RizChartReferenceError` |
| 时间为负或超出对象时间范围 | `RizChartTimeError` |
| BPM 时间轴缺失或 tick/秒换算失败 | `RizChartBpmError` |
| 画布 x/关键点/绝对坐标失败 | `RizChartCanvasError` |
| 缓动值或缓动区间非法 | `RizChartEaseError` |
| 颜色解析或通道非法 | `RizChartColorError` |
| `splitColor()` 混合不匹配 | `RizChartColorMismatchError` |
| 主题颜色/索引/数量失败 | `RizChartThemeError` |
| `floorPosition` 失败 | `RizChartFloorPositionError` |
| 除零 | `RizChartDivisionByZeroError` |
| 批量元素失败 | `RizChartBatchError` |
| 文件读取失败 | `RizChartLoadError` |
| 导出失败 | `RizChartExportError` |
| `check()` 发现问题 | `RizChartValidationError` |
| 回退失败 | `RizChartTransactionError` |
| 几何/区域失败 | `RizChartGeometryError` |
| 字体/字形失败 | `RizChartFontError` |
| 文本排版失败 | `RizChartTextLayoutError` |

复合操作在无法进一步细分时，会使用该函数的默认异常类；最具体可识别的原因优先。

## 批量函数

高级批量函数包括 `add*ByDict()`、`copy*()`、`set*Ease()` 等。

设置 `isReturnException=True` 时：

- `isFailAddAllowed` 被忽略，强制为 `False`；
- 任一元素失败会回退整批；
- 抛出 `RizChartBatchError`；
- `.failed_indices` 是原失败索引；
- `.errors` 保存可用异常列表；无法逐项细分时包含聚合原因；
- `.rolled_back` 表示是否已完成回退；
- `.cause` 保存首个/聚合原因。

```python
try:
    copyLine(source, [0, 99], target, isReturnException=True)
except RizChartBatchError as error:
    print(error.failed_indices)
    print(error.errors)
```

`copyCamera()` 的所有失败固定对应 `.failed_indices=[0]`。

## 原子回退

所有原本保证原子性的函数仍然先回退再抛异常。

如果回退本身失败，抛出 `RizChartTransactionError`：

```python
try:
    advanced_operation(...)
except RizChartTransactionError as error:
    print(error.rollback_succeeded)  # False
    print(error.cause)               # 原始失败
```

## 消息示例

```text
copyLine: 线索引 9 超出范围 [0, 4)
transColor: themes[0].colorsList 必须是长度 3 的列表，实际为 2
addLine: 无法计算 floorPosition：缺少 time=0.0 BPM 节点
getLinePosition: canvasIndex=3 不存在
transColor: 颜色通道 300 超出 0..255
getXYRatio: type="X" 时 canvasspeed=0.0 导致除零
copyLine: 3 个元素失败，索引 [0,2,4]；已回退=True
drawText: 字体缺少字符 "字" (U+5B57)
export: 无法导出 chart.json；check 报告 3 项问题
```

## 与 `isFailAddAllowed` 的关系

| `isReturnException` | `isFailAddAllowed` | 行为 |
| --- | --- | --- |
| `False` | `False` | 现有原子行为，失败返回失败索引 |
| `False` | `True` | 现有跳过失败元素行为 |
| `True` | 任意 | 忽略传入值，强制原子；失败抛异常 |

## 注意事项

- 异常类从 `rizChartFunction.exceptions` 导入。
- `isReturnException` 是 keyword-only 参数，建议始终使用关键字调用。
- 查询类函数“没有匹配”仍返回 `[]`，不是失败。
- 批量函数全部成功仍返回 `[]`，不是失败。
- `refresh()` 返回 `False` 表示没有变化，不是失败。
- 空文本、未请求绘制等空结果是成功。
- `NaN` 只有在 `isReturnException=True` 时转换为 `RizChartDivisionByZeroError`。
