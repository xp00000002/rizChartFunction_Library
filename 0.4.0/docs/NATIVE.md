# 可选 C++ 加速

`0.4.0/` 包含一个可选的 C++ 几何扩展：

```text
rizChartFunction._rizchart_native
```

它不是公开 API，不改变任何函数签名、谱面 dict 结构或 `isReturnException`
语义。扩展不可用时，库自动使用纯 Python 实现。

## 作用范围

当前 native 只处理数值和几何热路径：

- `is_simple_polygon()`
- `line_intervals()`
- `line_intervals_many()`
- `point_in_polygon_many()`

绘图侧用于：

- 多边形/椭圆填充线求交
- 径向、锥形和边框填充的批量射线
- 多边形自交检测
- 批量点在多边形内判断

谱面修改、事务预演、异常映射、颜色解析和字体流程仍由 Python 完成。

## 安装

### 默认构建

需要 Python 3.10 或更高版本。默认会尝试构建 native 扩展：

```bash
python -m pip install -e .
```

字体文字功能：

```bash
python -m pip install -e ".[font]"
```

### 只安装纯 Python 版本

在没有 C++ 编译器，或希望固定使用纯 Python 回退时，可以关闭 native：

```powershell
$env:RIZCHART_BUILD_NATIVE = "OFF"
python -m pip install -e .
Remove-Item Env:RIZCHART_BUILD_NATIVE
```

bash / zsh：

```bash
RIZCHART_BUILD_NATIVE=OFF python -m pip install -e .
```

也可以直接通过 scikit-build-core 的配置项关闭：

```bash
python -m pip install -e . --config-settings=cmake.define.RIZCHART_BUILD_NATIVE=OFF
```

纯 Python 构建仍然需要安装 CMake、Ninja 等构建工具，因为项目使用
`scikit-build-core` 作为构建后端；只是不再需要 C++ 编译器。

## 检查是否启用

`_native` 是内部模块，仅用于诊断：

```python
from rizChartFunction import _native

print(_native.available())
print(_native.native_version())
print(_native.native_error())
```

- `available()` 为 `True`：已加载 native 扩展；
- 为 `False`：使用纯 Python 回退；
- `native_error()` 可显示扩展导入失败原因。

## 构建要求

| 项目 | 要求 |
| --- | --- |
| Python | `>=3.10` |
| C++ | C++17 |
| CMake | `>=3.15` |
| Ninja | `>=1.11` |
| pybind11 | `>=2.12` |
| scikit-build-core | `>=0.10` |
| Windows | MSVC 2022 Build Tools 或同等 Visual Studio C++ 工具链 |
| Linux | GCC 9+ 或 Clang 12+ |
| macOS | Xcode Command Line Tools / Clang |

这些构建依赖由 `pyproject.toml` 的 `[build-system]` 自动准备。普通用户不需要
手动安装 pybind11、CMake 或 Ninja。

## 构建 wheel / sdist

在 `0.4.0/` 目录执行：

```bash
python -m pip wheel . --no-deps -w dist
```

纯 Python wheel：

```powershell
$env:RIZCHART_BUILD_NATIVE = "OFF"
$env:SKBUILD_WHEEL_PLATLIB = "false"
python -m pip wheel . --no-deps -w dist-pure
Remove-Item Env:RIZCHART_BUILD_NATIVE
Remove-Item Env:SKBUILD_WHEEL_PLATLIB
```

```bash
# bash / zsh
RIZCHART_BUILD_NATIVE=OFF SKBUILD_WHEEL_PLATLIB=false \
  python -m pip wheel . --no-deps -w dist-pure
```

`SKBUILD_WHEEL_PLATLIB=false` 让纯 Python wheel 使用 `py3-none-any` 标签。
native wheel 与操作系统、CPU 架构、CPython ABI 绑定；纯 Python wheel 不绑定
这些条件。

## 回退路径

以下情况会自动回退，不需要修改业务代码：

- 安装时使用 `RIZCHART_BUILD_NATIVE=OFF`；
- 运行环境没有对应的 native `.pyd` / `.so` / `.dylib`；
- 扩展导入失败；
- native 调用抛出异常时，几何包装函数回退到 Python 参考实现。

## 测试与基准

本机验证环境：

- Windows 11
- Python 3.14.0
- MSVC 14.44 / Visual Studio 2022 Build Tools
- native 和强制关闭 native 的纯 Python 路径均通过外部回归测试

性能结果与逐线一致性验证见：

- [`benchmarks/NATIVE_GEOMETRY_RESULTS.md`](../benchmarks/NATIVE_GEOMETRY_RESULTS.md)
- `benchmarks/benchmark_native_geometry.py`
- `benchmarks/benchmark_native_draw.py`

跨平台 CI 配置见仓库根目录的 `.github/workflows/0.4.0-ci.yml`。CI 会分别验证：

- Windows / Linux / macOS 的 native 构建和导入；
- 关闭 native 后的纯 Python wheel 构建和导入；
- 一个固定的多边形/椭圆绘图 smoke test。

## 版本说明

本目录对应的 Python 包版本为 `0.4.0`。native 模块的 `__version__` 是内部
ABI/实现版本，当前与包版本保持一致为 `0.4.0`，但两者仍独立管理。

发布 `0.4.0` 时需要区分：

- 纯 Python wheel：`py3-none-any`，不绑定操作系统或 CPython ABI；
- native wheel：与操作系统、CPU 架构和 CPython ABI 绑定，需要按目标平台
  分别构建。
