"""Benchmark full drawPolygon/drawEllipse with and without native geometry."""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

import rizChartFunction as rcf
import rizChartFunction._native as native
import rizChartFunction.advanced_draw as draw


def _measure(function, repeats=3):
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


def _polygon_points(count=512):
    return [
        rcf.createLinePoint(
            5.0 + 0.25 * math.sin(2.0 * math.pi * index / count),
            0.25 * math.cos(2.0 * math.pi * index / count),
            0,
            0,
            "#FFFFFF",
        )
        for index in range(count)
    ]


def _polygon_action(points):
    def action():
        chart = rcf.new(180.0)
        result = draw.drawPolygon(
            chart,
            0,
            points,
            True,
            True,
            precision=0.001,
            bordersize=[1],
            fillerstyle="linear",
            fillerinfo=[45, ["#FF0000", 0.2], ["#00FF00", 0.8]],
        )
        if result is None:
            raise RuntimeError("drawPolygon failed")

    return action


def _ellipse_action():
    def action():
        chart = rcf.new(180.0)
        result = draw.drawEllipse(
            chart,
            0,
            rcf.createLinePoint(5.0, 0.0, 0, 0, "#FFFFFF"),
            0.25,
            0.20,
            True,
            True,
            lineprecision=0.001,
            colorList=["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"],
            fillerstyle="linear",
            fillerinfo=[45, ["#FF0000", 0.2], ["#00FF00", 0.8]],
        )
        if result is None:
            raise RuntimeError("drawEllipse failed")

    return action


def main():
    if not native.available():
        print(f"native extension unavailable: {native.native_error()}")
        return 1

    points = _polygon_points()
    actions = {
        "drawPolygon": (_polygon_action(points), 3),
        "drawEllipse": (_ellipse_action(), 3),
    }
    results = {}
    for name, (action, repeats) in actions.items():
        native_result = _measure(action, repeats)
        original = native._native
        try:
            native._native = None
            python_result = _measure(action, repeats)
        finally:
            native._native = original
        results[name] = {
            "native": native_result,
            "python": python_result,
            "speedup": python_result["median"] / native_result["median"],
        }

    output = {
        "python": sys.version,
        "native_version": native.native_version(),
        "results": results,
    }
    path = Path(__file__).parent / "_output" / "native_draw.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("native drawing benchmark")
    print(f"native version: {native.native_version()}")
    for name, result in results.items():
        print(
            f"  {name:16s} python={result['python']['median']:.6f}s "
            f"native={result['native']['median']:.6f}s "
            f"speedup={result['speedup']:.2f}x"
        )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
