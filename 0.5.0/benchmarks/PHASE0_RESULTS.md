# 阶段 0：纯 Python 基准结果

## 环境

- Python：3.14.0
- 平台：Windows 11
- 测试对象：`0.5.0/` 当前纯 Python 实现
- 运行次数：每个场景 3 次，取 min / median / max
- profile 时间包含 cProfile 插桩开销，只用于判断相对热点，不作为绝对耗时

## 结果

### 优化前：纯 Python 基准

| 场景 | min | median | max |
| --- | ---: | ---: | ---: |
| `transColor`，40 线 × 50 节点 | 2.621 s | 2.977 s | 3.009 s |
| `setLinePointColorByList`，2000 节点 | 3.608 s | 3.632 s | 3.646 s |
| `refresh`，40 线 × 50 节点 | 0.0023 s | 0.0024 s | 0.0026 s |
| `drawPolygon`，512 顶点，填充+边框 | 0.446 s | 0.448 s | 0.451 s |
| `drawEllipse`，填充+边框，precision=0.001 | 0.885 s | 0.903 s | 0.914 s |
| `getYBorderByChart` × 1000 | 0.406 s | 0.409 s | 0.414 s |

### 批量颜色优化后

本轮先优化了颜色批量路径：`setLinePoint()` 在只修改 `color` 时，
跳过整条线的重复校验和 `_make_floor_plan()`，因为颜色不影响
`floorPosition`。

| 场景 | 优化前中位数 | 优化后中位数 | 提升 |
| --- | ---: | ---: | ---: |
| `transColor`，40 线 × 50 节点 | 2.977 s | 0.0114 s | 约 261× |
| `setLinePointColorByList`，2000 节点 | 3.632 s | 0.0187 s | 约 194× |

这说明颜色批量的主要问题不是颜色插值，而是每个节点重复做全谱
`floorPosition` 计算。当前阶段不需要为颜色插值单独写 C++。

优化后当前完整结果：

| 场景 | median |
| --- | ---: |
| `transColor` | 0.0114 s |
| `setLinePointColorByList` | 0.0187 s |
| `refresh` | 0.0021 s |
| `drawPolygon` | 0.349 s |
| `drawEllipse` | 0.904 s |
| `getYBorderByChart` × 1000 | 0.411 s |

## 结论

### 1. 颜色批量操作曾是最大热点，已通过核心快路径解决

`transColor` 和 `setLinePointColorByList` 的主要成本不在颜色插值，而在每个节点都调用一次
`setLinePoint()`，每次又触发 `_make_floor_plan()` 和整条线校验。

优化前 profile 中：

- 2000 次 `setLinePoint`
- 2000 次 `_make_floor_plan`
- 约 4,000,000 次 `canvas_floor_position`
- 约 8,000,000 次 `seconds_at`

这说明：

- 把颜色插值本身改成 C++ 收益有限；
- 当前已先实现颜色 only 快路径，批量颜色操作已从秒级降到毫秒级；
- C++ 加速 `floorPosition` 仍可能有用，但颜色路径不需要优先迁移。

### 2. 绘图热点是几何循环

`drawPolygon` profile 主要耗时：

- `_is_simple_polygon`
- `_build_fill_linear`
- `_segments_intersect`
- `_line_intervals`
- `_build_border`
- `_offset_polygon`

`drawEllipse` 主要耗时：

- `_build_fill_linear`
- `_line_intervals`
- `_point_in_polygon`
- `_point_in_polygon_with_boundary`

这些是适合 C++ 的批量几何计算，但最终仍需要批量建线/减少 `addLine` 和 `refresh`
的重复开销。

### 3. `refresh` 单独并不慢

40 线 × 50 节点的延迟高度谱面，`refresh` 约 2.4 ms。现阶段不建议优先迁移
`refresh`。

### 4. Y 边界查询已有一定成本

1000 次 `getYBorderByChart` 约 0.41 秒。profile 主要花在：

- 每次重建 BPM/流速事件数组
- `_key_point_spec` / `_key_point_specs`
- `_y_border_sample`

这说明可以先做 Python 缓存/预计算，而不是立刻 C++ 化。

## 对后续计划的调整建议

优先级仍保持 C++ 为批量数值内核：

1. **批量颜色核心快路径**：已完成；只改颜色时不再重复校验整条线或重算 floorPosition。
2. **批量建线 API**：下一步让绘图生成的采样结果一次性写入，减少重复校验和刷新。
3. C++ 首批内核优先：
   - 多边形线段求交 / 偏移 / 采样
   - 椭圆/填充线几何
   - floorPosition 批量积分（作为后续候选）
4. `getYBorderByChart` 先考虑 Python 缓存，不急于 C++。
5. `refresh` 暂时不列为优先项。

## 完成状态

- 阶段 0 已完成
- 基准脚本和结果分析已保存
- 基准输出目录 `0.5.0/benchmarks/_output/` 已加入 `.gitignore`
- 没有把测试输出或 profile 文件加入版本控制
