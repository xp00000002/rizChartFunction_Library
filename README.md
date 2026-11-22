# rizChartFunction

`rizChartFunction` 是一个用于创建、读取、编辑、校验、查询和导出 Rizline 谱面
（JSON）的 Python 库。仓库按版本目录保存，每个版本目录都是一个可独立安装和
导入的完整快照。

## 版本目录

| 目录 | 状态 | 公开 API | 说明 |
| --- | --- | --- | --- |
| [`0.2.0/`](0.2.0/) | 当前版本 | 149 个函数 | 新增 `getXYRatio()`、`getXYRatioByChart()`、`getRingColor()` |
| [`0.1.0/`](0.1.0/) | 历史版本 | 146 个函数 | 上一版 GitHub 快照 |

`0.2.0` 新增的查询函数在 `0.2.0` 之前的版本中不可用：

- `getXYRatio(bpm, canvasspeed, gamespeed, value=1.0, type="X")`
- `getXYRatioByChart(chart, index, time, gamespeed, value=1.0, type="X", isRealTime=False)`
- `getRingColor(chart, index, time, isRealTime=False)`

各版本的完整说明：

- [0.2.0 文档](0.2.0/docs/README.md)
- [0.1.0 文档](0.1.0/docs/README.md)

## 目录结构

```text
rizChartFunction_Library/
├── 0.1.0/                      # 历史版本快照
│   ├── src/rizChartFunction/   # 核心库源码
│   ├── docs/                   # 该版本的完整文档
│   ├── tools/                  # 参数示意图工具
│   ├── pyproject.toml
│   └── README.md
├── 0.2.0/                      # 当前版本快照
│   ├── src/rizChartFunction/
│   ├── docs/
│   ├── tools/
│   ├── pyproject.toml
│   └── README.md
├── .gitignore
└── README.md
```

## 安装与导入

需要 Python 3.10 或更高版本。请先进入要使用的版本目录；不同版本是独立的
发行快照，同一个 Python 环境建议只安装其中一个版本。

### 安装当前版本

```bash
git clone https://github.com/xp00000002/rizChartFunction_Library.git
cd rizChartFunction_Library/0.2.0
python -m pip install -e .
```

字体文字功能需要可选依赖组 `font`：

```bash
python -m pip install -e ".[font]"
```

也可以手动安装：

```bash
python -m pip install fontTools shapely numpy Pillow scikit-image
```

### 安装历史版本

```bash
cd rizChartFunction_Library/0.1.0
python -m pip install -e .
```

### 不安装直接导入

从仓库根目录运行 Python 时，可以把目标版本的 `src` 加入模块搜索路径：

```python
import sys
sys.path.insert(0, "0.2.0/src")

import rizChartFunction as rcf
```

也可以先进入版本目录，再使用该目录内的相对路径：

```python
import sys
sys.path.insert(0, "src")

import rizChartFunction as rcf
```

安装后即可直接导入：

```python
import rizChartFunction as rcf

chart = rcf.new(180.0)
```

## 版本与兼容性

- `0.2.0`：新增 `getXYRatio()`、`getXYRatioByChart()`、`getRingColor()`，并修正
  X/Y 视觉比例公式；公开 API 共 149 个函数。
- `0.1.0`：保留上一版行为和函数集合；公开 API 共 146 个函数。
- 需要新查询功能时请使用 `0.2.0/`；需要复现旧版行为时请使用 `0.1.0/`。

`0.2.0` 的 `getXYRatio()` 版本提示：

> 本函数自 `0.2.0` 起提供；在 `0.2.0` 之前的版本中不可用。

`getXYRatioByChart()` 和 `getRingColor()` 同样自 `0.2.0` 起提供。

## 示例文件

仓库不包含 `examples/` 目录。示例和测试输出属于本地生成内容，不会上传到
GitHub；如需保留，请放在本地任意位置，或在本地仓库中使用被忽略的
`examples/` 目录。

## 文档与工具

每个版本目录内都有独立文档和工具：

- [0.2.0 文档总览](0.2.0/docs/README.md)
- [0.2.0 性能标注说明](0.2.0/docs/PERFORMANCE.md)
- [0.2.0 内部实现说明](0.2.0/docs/TECHNICAL.md)
- [0.2.0 参数示意图工具](0.2.0/tools/chart-parameter-visualizer.html)
- [0.1.0 文档总览](0.1.0/docs/README.md)
