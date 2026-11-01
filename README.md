# rizChartFunction

`rizChartFunction` 是一个用于创建、读取、编辑、校验、查询和导出 Rizline 谱面
（JSON）的 Python 库。

项目提供以下能力：

- 引导线、线节点、判定环、线色覆盖、Note、Hold、画布、摄像机、BPM 等对象的
  创建、修改、删除与查询
- 线节点位置/颜色的缓动设置、批量插入、跨谱面复制
- 多边形、椭圆、闭合区域和文字绘制
- 字形填充与细字骨架提取
- 严格的谱面导入、清洗、校验和导出
- 完整的函数文档与可离线运行的参数示意图工具

当前公开 API 共 146 个函数，完整说明见 [文档总览](docs/README.md)。

## 拉取、导入与声明

### 拉取

```bash
git clone https://github.com/xp00000002/rizChartFunction_Library.git
cd rizChartFunction_Library
```

### 安装

需要 Python 3.10 或更高版本。

```bash
python -m pip install -e .
```

字体相关功能需要可选依赖组 `font`：

```bash
python -m pip install -e ".[font]"
```

也可以手动安装：

```bash
python -m pip install fontTools shapely numpy Pillow scikit-image
```

### 导入

```python
import rizChartFunction as rcf
```

也可以按需导入具体函数：

```python
from rizChartFunction import new, addCanvas, addLine
from rizChartFunction import createLinePoint, createRingPoint, createNote
```

### 依赖声明

- Python：`>=3.10`
- 运行时核心：Python 标准库
- 可选字体依赖：`fontTools`、`shapely`、`numpy`、`Pillow`、`scikit-image`

可选依赖已经在 `pyproject.toml` 的 `font` 组中声明：

```toml
[project.optional-dependencies]
font = [
    "fontTools>=4.0",
    "shapely>=2.0",
    "numpy>=1.20",
    "Pillow>=9.0",
    "scikit-image>=0.20",
]
```

### 最小示例

```python
import rizChartFunction as rcf

chart = rcf.new(175.0)
rcf.addCanvas(chart)

p0 = rcf.createLinePoint(0.0, 0.0, 0, 0, "#FFFFFF")
p4 = rcf.createLinePoint(4.0, 1.0, 0, 0, "#FF0000")
ring = rcf.createRingPoint(0.0, "#FFFFFF")
notes = [rcf.createNote(1.0, "tap")]

rcf.addLine(chart, [p0, p4], ring, notes=notes)
rcf.export(chart, "chart.json")
```

## 项目结构

```text
rizChartFunction_Library/
├── src/
│   └── rizChartFunction/       # 核心库源码
│       ├── base.py             # new/load/export/check/refresh
│       ├── chart.py            # 对象创建、修改与删除
│       ├── query.py            # 对象、时间、颜色、几何查询
│       ├── advanced.py         # 批量插入、复制、缓动与绘图入口
│       ├── advanced_copy.py    # 跨谱面复制实现
│       ├── advanced_ease.py    # 缓动与批量颜色修改
│       ├── advanced_draw.py    # 多边形、椭圆、闭合区域
│       └── advanced_font.py    # 文字填充与细字骨架
│
├── docs/                       # 完整文档
│   ├── README.md               # 文档总览
│   ├── base.md                 # base 模块
│   ├── chart.md                # chart 模块
│   ├── query.md                # query 模块
│   ├── advanced.md             # advanced 模块
│   ├── TECHNICAL.md            # 内部实现与维护说明
│
├── tools/                      # 独立辅助工具
│   ├── README.md
│   └── chart-parameter-visualizer.html
│
├── examples/                   # 示例/测试输出 JSON
├── pyproject.toml              # 项目与依赖声明
└── README.md
```

### 文档入口

- [文档总览](docs/README.md)
- [base 模块](docs/base.md)
- [chart 模块](docs/chart.md)
- [query 模块](docs/query.md)
- [advanced 模块](docs/advanced.md)
- [内部实现说明](docs/TECHNICAL.md)
- [开发计划](docs/PLAN.md)

### 工具

[参数示意图工具](tools/chart-parameter-visualizer.html) 是一个单文件网页，
可直接用浏览器打开，用于观察缓动插点、填充线和细字骨架参数。
