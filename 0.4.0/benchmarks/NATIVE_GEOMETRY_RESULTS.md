# 阶段 1-4：C++ 几何加速验证结果

> 构建后端后来改为 setuptools + `setup.py`；纯 Python 安装不再需要
> CMake、Ninja 或 C++ 编译器。下面的性能结果仍是同一 native 扩展的验证数据。

## 已实现

- `0.4.0/CMakeLists.txt`
- `0.4.0/cpp/src/rizchart_native.cpp`
- `0.4.0/src/rizChartFunction/_native.py`
- `pybind11 + setuptools/setup.py` 构建配置

原生扩展：

```text
rizChartFunction._rizchart_native
```

当前提供：

- `ping()`
- `is_simple_polygon(coords)`
- `line_intervals(coords, origin, direction, start_t, end_t)`
- `line_intervals_many(coords, origin_coords, direction_coords, start_ts, end_ts)`
- `point_in_polygon_many(coords, points, include_boundary=True)`

Python 适配层在扩展不可用时可回退到现有纯 Python 几何实现。

## 一致性测试

新增外部测试：

```text
test/test-native-geometry.py
test/test-native-draw.py
```

覆盖：

- 凸多边形、凹多边形
- 自交、重复点、所有点共线
- 随机单射线和批量射线区间
- 2000 个点的多边形内外判断
- 五种 `fillerstyle` 下的 `drawPolygon()` / `drawEllipse()`
- 强制关闭 native 后的纯 Python 回退
- 与 released `0.3.0` 的确定性 JSON 输出逐线比较

测试通过。

## 内核性能

环境：Python 3.14.0，Windows 11，512 顶点圆多边形，5 次中位数。

| 内核 | Python | Native | 加速 |
| --- | ---: | ---: | ---: |
| `is_simple_polygon` | 0.0776 s | 0.00053 s | 约 145× |
| `line_intervals`（单个简单射线） | 0.00027 s | 0.00013 s | 约 2.1× |
| `line_intervals_many`（501 条射线） | 0.1366 s | 0.00216 s | 约 63× |
| `point_in_polygon_many`（2000 点） | 0.2509 s | 0.0051 s | 约 49× |

批量射线的“Python”列是逐条调用纯 Python `_line_intervals()` 的总时间，不是单次射线时间。

结论：

- 多边形自交检测和批量点在多边形内判断收益非常大；
- 单条简单射线的 `line_intervals` 收益较小，因为事件数很少；
- 一次转换多边形、批量处理几百条射线的收益非常明显。

## 阶段 3：接入实际绘图路径

已接入：

- `advanced_draw._is_simple_polygon()`
- `advanced_draw._line_intervals()`
- `advanced_draw._point_in_polygon_with_boundary()`

保持无扩展时自动回退纯 Python。

阶段 3 的完整绘图基准（512 顶点多边形，3 次中位数）：

| 函数 | Python | Native | 加速 |
| --- | ---: | ---: | ---: |
| `drawPolygon` | 0.339 s | 0.096 s | 约 3.5× |
| `drawEllipse` | 0.827 s | 0.414 s | 约 2.0× |

## 阶段 4：批量填充与批量建线

新增：

- C++ `line_intervals_many()`
- `_native.line_intervals_many()` 适配与纯 Python 回退
- `advanced_draw._line_intervals_many()`
- 线性填充、径向/锥形填充、椭圆锥形边框填充改用批量射线
- `_make_point()` 直接构造内部线节点
- `_append_lines()` 直接追加内部生成线，跳过逐线 `addLine()`

完整绘图基准（512 顶点多边形，3 次中位数）：

| 函数 | Python fallback | Native | 加速 |
| --- | ---: | ---: | ---: |
| `drawPolygon` | 0.317 s | 0.030 s | 约 10.7× |
| `drawEllipse` | 0.700 s | 0.019 s | 约 37.5× |

相比阶段 3，native `drawPolygon` 从约 0.096 s 降到约 0.030 s，
`drawEllipse` 从约 0.414 s 降到约 0.019 s。

说明：

- 实际谱面的全量 `refresh()` 仍然保留，用于维持原有的事务预演、
  排序和 floorPosition 修复语义；
- 没有为单点 API 增加 C++ 调用；
- `transColor()` / `setLinePointColorByList()` 已在阶段 0 的 Python
  批量颜色快路径中优化，阶段 4 不再重复处理。

## 下一步

- 阶段 5：构建兼容性、wheel/源码安装说明、跨平台测试
- 继续评估 `getYBorderByChart()` 的 Python 缓存
- 再根据 profile 决定是否扩大 native 覆盖范围
