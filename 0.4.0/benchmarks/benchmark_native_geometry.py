"""Benchmark native geometry kernels against the Python reference."""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

import rizChartFunction._native as native
import rizChartFunction.advanced_draw as draw


def _measure(function, repeats=5):
    values = []
    for _ in range(repeats):
        started = time.perf_counter()
        function()
        values.append(time.perf_counter() - started)
    return {
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "all": values,
    }


def main():
    if not native.available():
        print(f"native extension unavailable: {native.native_error()}")
        return 1

    count = 512
    points = [
        (math.cos(2.0 * math.pi * index / count), math.sin(2.0 * math.pi * index / count))
        for index in range(count)
    ]
    specs = [{"x": x, "y": y} for x, y in points]
    origin = (0.0, 0.0)
    direction = (1.0, 0.123)
    queries = [
        (
            math.cos(2.0 * math.pi * index / 2000),
            math.sin(2.0 * math.pi * index / 2000),
        )
        for index in range(2000)
    ]
    batch_count = 501
    batch_origins = [
        (-1.0 + index * 2.0 / (batch_count - 1), 0.0)
        for index in range(batch_count)
    ]
    batch_directions = [(0.0, 1.0)] * batch_count

    original = native._native
    try:
        native._native = None
        python_benchmarks = {
            "is_simple_polygon": _measure(
                lambda: draw._is_simple_polygon(specs),
            ),
            "line_intervals": _measure(
                lambda: draw._line_intervals(specs, origin, direction),
            ),
            "line_intervals_501_per_call": _measure(
                lambda: [
                    draw._line_intervals(specs, origin, direction)
                    for origin, direction in zip(
                        batch_origins,
                        batch_directions,
                    )
                ],
                repeats=3,
            ),
            "point_in_polygon_2000": _measure(
                lambda: [
                    draw._point_in_polygon(specs, {"x": x, "y": y})
                    for x, y in queries
                ],
            ),
        }
    finally:
        native._native = original

    native_benchmarks = {
        "is_simple_polygon": _measure(
            lambda: native.is_simple_polygon(points),
        ),
        "line_intervals": _measure(
            lambda: native.line_intervals(points, origin, direction),
        ),
        "line_intervals_501_per_call": _measure(
            lambda: native.line_intervals_many(
                points,
                batch_origins,
                batch_directions,
            ),
        ),
        "point_in_polygon_2000": _measure(
            lambda: native.point_in_polygon_many(points, queries),
        ),
    }

    output = {
        "python": sys.version,
        "native_version": native.native_version(),
        "polygon_points": count,
        "queries": len(queries),
        "batch_rays": batch_count,
        "python_kernels": python_benchmarks,
        "native_kernels": native_benchmarks,
        "speedup": {
            name: python_benchmarks[name]["median"]
            / native_benchmarks[name]["median"]
            for name in python_benchmarks
        },
    }

    path = Path(__file__).parent / "_output" / "native_geometry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("native geometry benchmark")
    print(f"native version: {native.native_version()}")
    for name in python_benchmarks:
        py = python_benchmarks[name]["median"]
        nt = native_benchmarks[name]["median"]
        print(
            f"  {name:28s} python={py:.6f}s native={nt:.6f}s "
            f"speedup={py / nt:.2f}x"
        )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
