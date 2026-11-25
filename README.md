# rizChartFunction

`rizChartFunction` 是一个用于创建、读取、编辑、校验、查询和导出 Rizline 谱面
（JSON）的 Python 库。仓库按版本目录保存，每个版本目录都是一个可独立安装和
导入的完整快照。

## 版本目录

| 目录 | 状态 | 公开 API | 说明 |
| --- | --- | --- | --- |
| [`0.4.0/`](0.4.0/) | 当前版本 | 159 个函数 | 可选 C++ 几何加速、批量绘图优化、`getRingRadius()`、`xMirrorLine()` |
| [`0.3.0/`](0.3.0/) | 上一版本 | 157 个函数 | 新增 X/Y 边界、遮罩透明度、游戏缩放、线宽、颜色替换和统一异常模式 |
| [`0.2.0/`](0.2.0/) | 历史版本 | 149 个函数 | 新增 `getXYRatio()`、`getXYRatioByChart()`、`getRingColor()` |
| [`0.1.0/`](0.1.0/) | 历史版本 | 146 个函数 | 更早的 GitHub 快照 |

各版本的完整说明：

- [0.4.0 文档](0.4.0/docs/README.md)
- [0.3.0 文档](0.3.0/docs/README.md)
- [0.2.0 文档](0.2.0/docs/README.md)
- [0.1.0 文档](0.1.0/docs/README.md)

## 0.4.0 主要变化

- 新增可选 C++ 几何扩展 `rizChartFunction._rizchart_native`：
  - 多边形自交检测、批量射线区间、批量点在多边形内判断；
  - `drawPolygon()` / `drawEllipse()` 的填充和内部建线批量化；
  - native 不可用时自动回退纯 Python，公开 API、谱面格式和异常语义不变。
- 新增查询函数 `getRingRadius()`，返回判定环半径 `1 / 18`（单位为
  `xPosition`）。
- 新增 `xMirrorLine()` X 轴对称镜像：
  - `"Line"`：仅镜像线；
  - `"changePartCanvas"`：镜像线与受影响的画布局部；
  - `"changeCanvas"`：镜像线与整个受影响画布；
  - `"addCanvas"`：复制受影响画布，把镜像线迁移到新画布。
- 加入 native/纯 Python 构建配置、sdist/wheel 规则和跨平台 CI 配置。
- 保留 `0.3.0` 的异常模式、X/Y 边界、遮罩透明度、游戏缩放、线宽和颜色替换
  能力。

## 目录结构

```text
rizChartFunction_Library/
├── 0.1.0/                      # 历史版本快照
│   ├── src/rizChartFunction/
│   ├── docs/
│   ├── tools/
│   ├── pyproject.toml
│   └── README.md
├── 0.2.0/                      # 历史版本快照
│   ├── src/rizChartFunction/
│   ├── docs/
│   ├── tools/
│   ├── pyproject.toml
│   └── README.md
├── 0.3.0/                      # 上一版本快照
│   ├── src/rizChartFunction/
│   ├── docs/
│   ├── tools/
│   ├── pyproject.toml
│   └── README.md
├── 0.4.0/                      # 当前版本快照
│   ├── src/rizChartFunction/
│   ├── cpp/src/rizchart_native.cpp
│   ├── benchmarks/
│   ├── docs/
│   ├── tools/
│   ├── CMakeLists.txt
│   ├── CPP_PLAN.md
│   ├── pyproject.toml
│   └── README.md
├── .github/workflows/0.4.0-ci.yml
├── .gitignore
└── README.md
```

## 安装与导入

需要 Python 3.10 或更高版本。请先进入要使用的版本目录；不同版本是独立的
发行快照，同一个 Python 环境建议只安装其中一个版本。

### 安装当前版本

`0.4.0` 默认会尝试构建可选 C++ 几何扩展。需要 C++17 编译器、CMake 和 Ninja；
使用 `pip` 构建时会自动准备构建依赖。

```bash
git clone https://github.com/xp00000002/rizChartFunction_Library.git
cd rizChartFunction_Library/0.4.0
python -m pip install -e .
```

没有 C++ 编译器时，可以关闭 native 扩展，使用纯 Python 安装：

```powershell
$env:RIZCHART_BUILD_NATIVE = "OFF"
python -m pip install -e .
Remove-Item Env:RIZCHART_BUILD_NATIVE
```

```bash
# bash / zsh
RIZCHART_BUILD_NATIVE=OFF python -m pip install -e .
```

native 构建、纯 Python wheel 和平台说明见
[0.4.0 可选 C++ 加速](0.4.0/docs/NATIVE.md)。

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
cd rizChartFunction_Library/0.3.0
python -m pip install -e .
```

### 不安装直接导入

从仓库根目录运行 Python 时，可以把目标版本的 `src` 加入模块搜索路径：

```python
import sys
sys.path.insert(0, "0.4.0/src")

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

## 自定义异常

可失败函数默认返回原有失败值；传入 `isReturnException=True` 时改为抛出异常：

```python
from rizChartFunction import getRingColor

try:
    color = getRingColor(chart, 0, 1.0, isReturnException=True)
except Exception as error:
    print(error)
```

异常类位于 `rizChartFunction.exceptions`，完整说明见
[0.4.0 异常文档](0.4.0/docs/EXCEPTIONS.md)。

## 版本兼容性

- `0.4.0`：新增可选 C++ 几何加速、批量绘图优化、`getRingRadius()` 和
  `xMirrorLine()`；公开 API 共 159 个函数。
- `0.3.0`：新增边界、遮罩透明度、游戏缩放、线宽、颜色替换和异常模式；
  公开 API 共 157 个函数。
- `0.2.0`：新增 X/Y 视觉比例与判定环颜色查询；公开 API 共 149 个函数。
- `0.1.0`：保留更早行为和函数集合；公开 API 共 146 个函数。
- 需要 native 加速、镜像和最新查询功能时使用 `0.4.0/`；需要复现旧版行为时
  使用 `0.3.0/`、`0.2.0/` 或 `0.1.0/`。

## 示例文件

仓库不包含 `examples/` 目录。示例和测试输出属于本地生成内容，不会上传到
GitHub；如需保留，请放在本地任意位置，或在本地仓库中使用被忽略的
`examples/` 目录。

## 文档与工具

每个版本目录内都有独立文档和工具：

- [0.4.0 文档总览](0.4.0/docs/README.md)
- [0.4.0 自定义异常说明](0.4.0/docs/EXCEPTIONS.md)
- [0.4.0 可选 C++ 加速](0.4.0/docs/NATIVE.md)
- [0.4.0 性能标注说明](0.4.0/docs/PERFORMANCE.md)
- [0.4.0 内部实现说明](0.4.0/docs/TECHNICAL.md)
- [0.4.0 参数示意图工具](0.4.0/tools/chart-parameter-visualizer.html)
- [0.3.0 文档总览](0.3.0/docs/README.md)
- [0.2.0 文档总览](0.2.0/docs/README.md)
- [0.1.0 文档总览](0.1.0/docs/README.md)
