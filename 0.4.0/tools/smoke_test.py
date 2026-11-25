"""Small install/import smoke test for the optional native build."""

from __future__ import annotations

import argparse
import math

import rizChartFunction as rcf
import rizChartFunction._native as native
import rizChartFunction.advanced_draw as draw


def _polygon_points(count: int = 32):
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


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--expect-native", action="store_true")
    mode.add_argument("--expect-fallback", action="store_true")
    args = parser.parse_args()

    if args.expect_native and not native.available():
        raise RuntimeError(
            f"native extension was not loaded: {native.native_error()}"
        )
    if args.expect_fallback and native.available():
        raise RuntimeError("native extension is loaded, expected pure Python")

    chart = rcf.new(180.0)
    points = _polygon_points()
    if draw.drawPolygon(
        chart,
        0,
        points,
        True,
        True,
        precision=0.02,
        bordersize=[1],
        fillerstyle="linear",
        fillerinfo=[45, "#FF0000", "#00FF00"],
    ) is None:
        raise RuntimeError("drawPolygon smoke test failed")
    if draw.drawEllipse(
        chart,
        0,
        rcf.createLinePoint(5.0, 0.0, 0, 0, "#FFFFFF"),
        0.25,
        0.20,
        True,
        True,
        lineprecision=0.02,
        colorList=["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"],
        fillerstyle="radial",
        fillerinfo=[0.0, 5.0, "#FF0000", "#00FF00"],
    ) is None:
        raise RuntimeError("drawEllipse smoke test failed")

    issues = rcf.check(chart)
    if issues is not None:
        raise RuntimeError(f"generated chart is invalid: {issues}")

    print(
        "smoke ok:",
        f"native={native.available()}",
        f"version={native.native_version()}",
        f"lines={rcf.getLineCount(chart)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
