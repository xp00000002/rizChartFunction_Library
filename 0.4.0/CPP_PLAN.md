# C++ 加速开发计划

> 说明：本文件保留开发阶段记录。0.4.0 的安装构建后端已从
> `scikit-build-core` 改为 setuptools + `setup.py`；纯 Python 安装不再需要
> CMake、Ninja 或 C++ 编译器。

> 目标：在不改变现有公开 API、谱面 dict 结构、异常语义和纯 Python 回退能力的前提下，将高开销的数值计算和批量绘图采样迁移到可选 C++ 扩展。

## 当前状态

- 阶段 0：已完成，结果见 `benchmarks/PHASE0_RESULTS.md`
- 阶段 1：已完成，已建立 `pybind11 + scikit-build-core` 可选扩展
- 阶段 2：已完成，已实现并验证 `is_simple_polygon`、`line_intervals`、
  `point_in_polygon_many`
- 阶段 3：已完成，已将 native 几何内核接入 `advanced_draw.py` 的实际绘制路径
- 阶段 4：已完成，已加入批量射线区间和批量内部建线路径
- 阶段 5：已完成，已加入可选构建开关、wheel/sdist 配置、跨平台 CI 和安装文档

## 1. 范围与原则

### 保留在 Python 的部分

- 所有公开函数签名和参数校验
- 谱面 dict 结构及其 JSON 格式
- `isReturnException` 与 `RizChartError` 异常映射
- 原子执行、失败回退、目标谱面预演
- 字体文件、Pillow、skimage 等高层流程

### 优先迁移到 C++ 的部分

1. 缓动函数与 Cubic Bezier 批量求值
2. RGBA 颜色批量插值与舍入
3. BPM、floorPosition、画布高度积分
4. 多边形/椭圆/文字的批量几何采样
5. 批量颜色扫描与批量节点变换

### 不优先迁移的部分

- `addLine()`、`setLinePoint()` 等单个 dict 修改函数
- `load()` / `export()` 的 JSON 和结构清洗
- 每次只处理一个点的 C++ 小函数
- 直接让 C++ 拥有和修改 Python chart dict

---

## 2. 目标架构

```text
Python 公开 API
├── 参数校验
├── chart dict / 事务 / 回退
├── isReturnException 异常映射
└── 计算调度
    ├── Python 参考实现（默认回退）
    └── C++ 扩展（可选）
        ├── 批量数组计算
        ├── 批量几何采样
        └── 批量高度/积分计算
```

原则：

- C++ 只接收简单数组或数值参数；
- C++ 不直接操作 chart dict；
- C++ 内部错误转换为返回码或专用底层异常，再由 Python 映射为现有异常；
- 纯 Python 实现始终保留，用于无扩展环境和数值对照测试。

---

## 3. 分阶段计划

### 阶段 0：基准与 profile

**改动**

- 新增 `0.4.0/benchmarks/benchmark_baseline.py`
- 构造固定规模的测试谱面：
  - 大谱面 `refresh`
  - 大批量 `transColor`
  - `setLinePointColorByList`
  - 复杂 `drawPolygon` / `drawEllipse`
  - 多次 `getYBorderByChart`
- 记录 Python 版本的：
  - 总耗时
  - 每个阶段耗时
  - 峰值内存

**产出**

- `0.4.0/benchmarks/_output/baseline.json`
- `0.4.0/benchmarks/PHASE0_RESULTS.md`
- 明确真正的热点，避免迁移低收益函数。

**完成标准**

- 至少有一组可重复的大规模基准；
- 能说明绘图时间主要花在采样、dict 构造、校验还是 `addLine`/`refresh`。

---

### 阶段 1：建立可选扩展骨架（已完成）

**改动**

- 新增 `0.4.0/cpp/`：
  - `CMakeLists.txt`
  - `cpp/include/rizchart/`
  - `cpp/src/`
- 新增 Python 加载器 `0.4.0/src/rizChartFunction/_native.py`
  - 尝试导入扩展；
  - 失败时返回 `None`，由 Python 回退。
- 修改 `0.4.0/pyproject.toml`：
  - 增加 `scikit-build-core`
  - 增加 `pybind11`
  - 保留纯 Python 可安装路径
- 新增最小测试函数，例如：
  - `native.ping()`
  - `native.add_arrays()`

**产出**

- Windows 本地可构建的 `_rizchart_native` 扩展；
- 没有扩展时所有现有测试仍通过。

**完成标准**

- `pip install -e .` 能构建扩展；
- 删除/重命名扩展后，库仍能走纯 Python 回退；
- 不改变任何公开 API。

---

### 阶段 2：第一组几何内核（已完成）

阶段 0 profile 显示颜色批量问题已由 Python 快路径解决，剩余主要热点在几何循环，
因此把首批 C++ 内核调整为几何内核。

**改动**

- C++ 实现：
  - `is_simple_polygon(coords)`
  - `line_intervals(coords, origin, direction, start_t, end_t)`
  - `point_in_polygon_many(coords, points, include_boundary)`
- Python 适配层：
  - `0.4.0/src/rizChartFunction/_native.py`
  - 有扩展时调用 native；
  - 无扩展时回退现有 Python 实现。
- 使用 double，保持与 Python 相同的 `1e-9` 容差和边界语义。

**测试**

- 外部测试 `test/test-native-geometry.py`
- 凸/凹/自交/重复点/共线多边形
- 随机射线区间
- 批量点在多边形内判断
- 强制关闭 native 后的 Python 回退

**基准结果**

- `is_simple_polygon`：约 142×
- `point_in_polygon_many`（2000 点）：约 47×
- 单条简单射线的 `line_intervals`：约 2.2×，但真实填充场景会重复调用数百次

**完成标准**

- 数值结果与 Python 参考实现一致；
- Python 回退可用；
- 实际调用点已在阶段 3 接入。

---

### 阶段 3：几何内核接入实际绘图（已完成）

**改动**

- 将 `advanced_draw._is_simple_polygon()` 接入 native；
- 将 `advanced_draw._line_intervals()` 接入 native；
- 将 `advanced_draw._point_in_polygon_with_boundary()` 接入 native；
- 保留 native 不可用时的纯 Python 回退；
- 完整 `drawPolygon()` / `drawEllipse()` 输出对比通过。

**后续阶段 4 已补上**

- 批量射线区间接口；
- 批量内部建线，减少逐线 `addLine()` 调用；
- 多边形/椭圆生成结果直接追加。

**重点**

- 保持当前点顺序、颜色顺序、边框层顺序和线索引返回顺序；
- 保持 `isReturnException` 和失败回滚；
- 不改变公开函数参数。

**测试**

- 对固定图形和随机图形比较 Python/native 输出；
- 对比导出 JSON 的结构、节点顺序和颜色；
- 绘制大图形做性能基准。

**完成标准**

- 典型绘图场景有明确加速；
- 输出与 Python 版本逐节点一致（浮点误差范围内）；
- 失败路径仍能完整回退。

---

### 阶段 4：批量填充与批量建线（已完成）

阶段 3 的完整绘图 profile 显示，剩余主要开销在：

- 每条填充线都重新把整圈多边形 dict 转成坐标数组；
- 每条生成线都走一次公开 `addLine()` 的完整归一化；
- 实际谱面提交后再次做全量 refresh。

**改动**

- C++ 新增 `line_intervals_many()`：
  - 一次转换多边形坐标；
  - 批量传入射线起点、方向、可选起止距离；
  - 返回每条射线的区间列表。
- `_native.py` 增加对应适配函数和纯 Python 回退。
- `_build_fill_linear()`、`_build_fill_radial_conic()`、
  `_build_ellipse_conic_border_fill()` 改为批量射线调用。
- `_make_point()` 直接构造内部线节点，避免 `createLinePoint()` 的
  导出/再解析往返。
- `_append_lines()` 直接追加内部生成线，跳过逐线 `addLine()` 的
  颜色解析和排序；最终仍由 `refresh()` 完成排序和 floorPosition，
  保留原来的事务预演和失败回滚。
- 保留实际谱面的全量 refresh，以继续修复已有节点状态。

**未重复处理**

- `transColor()` / `setLinePointColorByList()` 已在阶段 0 的批量
  颜色快路径中优化，当前不再作为阶段 4 重点。
- 单点 API 不增加 C++ 调用。

**测试与结果**

- `test/test-native-geometry.py` 增加批量射线一致性测试；
- `test/test-native-draw.py` 覆盖五种 `fillerstyle` 的
  `drawPolygon()` / `drawEllipse()`，逐线比较 native 和纯 Python 回退；
- 与 released `0.3.0` 的确定性 JSON 输出逐线一致；
- 512 顶点线性绘图中 native `drawPolygon` 约 0.030 s（阶段 3 约
  0.094 s），`drawEllipse` 约 0.019 s（阶段 3 约 0.414 s）；
- 501 条射线的批量区间约 0.0021 s，逐条调用 native 约 0.053 s。

---

### 阶段 5：构建、兼容性与发布（已完成）

**改动**

- `CMakeLists.txt` 增加 `RIZCHART_BUILD_NATIVE` 构建开关：
  - 默认 `ON`：构建 native；
  - `OFF`：只安装纯 Python 包，不需要 C++ 编译器；
  - 构建过程使用 `project(... LANGUAGES NONE)`，关闭 native 时不会探测 C++。
- `pyproject.toml` 清理旧 setuptools 配置，补充 scikit-build sdist 文件清单。
- 增加纯 Python wheel 构建方式：
  - `RIZCHART_BUILD_NATIVE=OFF`
  - `SKBUILD_WHEEL_PLATLIB=false`，生成 `py3-none-any` wheel。
- 增加 `0.4.0/tools/smoke_test.py`，检查安装后的 native 或回退路径。
- 增加 `.github/workflows/0.4.0-ci.yml`：
  - Windows / Linux / macOS；
  - Python 3.10 / 3.13 native 构建；
  - Python 3.13 纯 Python 回退构建。
- 增加 `0.4.0/docs/NATIVE.md`，记录构建要求、wheel/sdist 命令、回退和平台说明。
- 更新 `0.4.0/README.md`、`0.4.0/docs/README.md`、`0.4.0/docs/TECHNICAL.md`、
  `0.4.0/docs/PERFORMANCE.md` 和绘图函数性能说明。

**本地验证**

- Windows 11 / Python 3.14 / MSVC 14.44：native wheel 构建、安装、smoke test 通过；
- 同一环境纯 Python wheel：`py3-none-any` 构建、安装、`--expect-fallback`
  smoke test 通过；
- 源目录测试：22 个外部回归脚本全部通过；
- sdist 包含 `CMakeLists.txt`、`cpp/src/rizchart_native.cpp`、`docs/NATIVE.md`。

**测试矩阵说明**

- 本地实际验证：Windows 11 / Python 3.14；
- CI 配置覆盖 Windows / Linux / macOS 和 Python 3.10 / 3.13；
- CI 尚未在远程运行；首次推送后需要检查矩阵结果。

**完成标准**

- 无扩展环境功能完整；
- 有扩展环境性能有稳定收益；
- 打包和导入流程可重复。

---

## 4. 建议的首批 C++ 接口

```text
ease_values(ease_type, ratios) -> list[float]
lerp_colors(start_rgba, end_rgba, ratios) -> list[list[int]]
floor_position_many(...) -> list[float]
sample_polygon(points, precision, ...) -> flat array
sample_ellipse(...) -> flat array
```

注意：

- 不使用单个点一次调用的接口；
- 不通过 C++ 直接返回 Python dict；
- 颜色和坐标尽量使用连续数组或列表，减少对象转换。

---

## 5. 风险控制

| 风险 | 应对 |
| --- | --- |
| C++ 与 Python 数值不一致 | 保留 Python 参考实现，golden test + 容差测试 |
| 扩展构建失败 | 自动回退纯 Python；发布 wheel |
| dict 转换开销抵消收益 | 只做批量接口，先 profile |
| 异常语义变化 | C++ 底层错误由 Python 层统一映射 |
| 回退不完整 | 继续使用 Python 事务层，C++ 不直接改 chart |
| 平台兼容性 | Windows 优先本地验证，再补 wheel/CI |
| 版本结构混乱 | 在 `0.4.0/` 开发，稳定后再定为下一版本 |

---

## 6. 验收指标

不承诺固定倍数，先设定可检查目标：

- 数值内核在批量输入下明显快于 Python 循环；
- 复杂绘图函数在实际场景中有可测加速；
- 无扩展时功能、返回值、异常和回退行为完全一致；
- 所有现有测试和新增一致性测试通过；
- 性能提升不是靠减少校验或牺牲回滚保证换来的。

建议只有在阶段 0 和阶段 2 证明有实际收益后，再进入完整绘图迁移；否则优先优化 Python 批量化接口。

---

## 7. 已确认

- 首批以 Windows 本地验证为主，并加入 Windows / Linux / macOS CI。
- C++ 扩展作为可选安装项；无扩展时自动使用纯 Python。
- 首批完整绘图优化优先覆盖 `drawPolygon` / `drawEllipse`。
- 本版本发布为 `0.4.0`。
