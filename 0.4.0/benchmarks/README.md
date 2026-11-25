# Baseline benchmark

阶段 0 的纯 Python 基准脚本。

## 运行

在仓库根目录执行：

```bash
python 0.4.0/benchmarks/benchmark_baseline.py --repeats 3
```

快速运行：

```bash
python 0.4.0/benchmarks/benchmark_baseline.py --quick
```

## 输出

输出目录：

```text
0.4.0/benchmarks/_output/
```

包括：

- `baseline.json`：每个场景的最小/中位/最大耗时
- `*.prof`：cProfile 原始文件
- `*_profile.txt`：cProfile 排序文本

该目录已在根 `.gitignore` 中屏蔽，不会提交：

```gitignore
**/benchmarks/_output/
```

## 场景

- `transColor`：40 条线 × 50 个线节点
- `setLinePointColorByList`：单条 2000 节点线
- `refresh`：40 条线 × 50 节点，延迟高度计算的谱面
- `drawPolygon`：512 顶点、填充 + 边框
- `drawEllipse`：填充 + 边框、`lineprecision=0.001`
- `getYBorderByChart`：1000 次查询，包含 BPM/流速/摄像机关键点

原生几何内核基准：

```bash
python 0.4.0/benchmarks/benchmark_native_geometry.py
python 0.4.0/benchmarks/benchmark_native_draw.py
```

这两个脚本会分别测量纯 Python 回退和 native 路径，因此需要先安装 `0.4.0/`。
安装与回退说明见 [docs/NATIVE.md](../docs/NATIVE.md)。

结果分析：

- [PHASE0_RESULTS.md](PHASE0_RESULTS.md)
- [NATIVE_GEOMETRY_RESULTS.md](NATIVE_GEOMETRY_RESULTS.md)
