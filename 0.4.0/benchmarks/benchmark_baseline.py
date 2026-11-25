"""Phase 0 baseline benchmark for the pure-Python implementation.

Run from the repository root:

    python 0.4.0/benchmarks/benchmark_baseline.py

Benchmark outputs are written to benchmarks/_output and are gitignored.
"""

from __future__ import annotations

import argparse
import copy
import cProfile
import json
import math
import platform
import pstats
import statistics
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve()
NEXT_ROOT = HERE.parents[1]
sys.path.insert(0, str(NEXT_ROOT / "src"))

import rizChartFunction as rcf  # noqa: E402


def _line_chart(lines: int, nodes: int, delayed: bool = False) -> dict:
    chart = rcf.new(180.0)
    for line_index in range(lines):
        base = line_index * 2.0
        points = [
            rcf.createLinePoint(
                base + point_index * 0.05,
                math.sin(point_index * 0.3) * 0.5,
                0,
                0,
                "#FFFFFF" if point_index % 2 else "#FF0000",
            )
            for point_index in range(nodes)
        ]
        result = rcf.addLine(
            chart,
            points,
            [rcf.createRingPoint(base, "#FFFFFF")],
            isDelayCalculate=delayed,
        )
        if result is None:
            raise RuntimeError(f"failed to create benchmark line {line_index}")
    return chart


def _wide_line_chart(nodes: int) -> dict:
    chart = rcf.new(180.0)
    points = [
        rcf.createLinePoint(
            index * 0.01,
            math.sin(index * 0.1) * 0.5,
            0,
            0,
            "#FFFFFF",
        )
        for index in range(nodes)
    ]
    if rcf.addLine(chart, points, [rcf.createRingPoint(0, "#FFFFFF")]) is None:
        raise RuntimeError("failed to create wide benchmark line")
    return chart


def _polygon_points(count: int) -> list[dict]:
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


def _draw_polygon_state() -> tuple[dict, list[dict]]:
    return rcf.new(180.0), _polygon_points(512)


def _draw_ellipse_state() -> tuple[dict, dict]:
    return (
        rcf.new(180.0),
        rcf.createLinePoint(5.0, 0.0, 0, 0, "#FFFFFF"),
    )


def _event_chart() -> dict:
    chart = rcf.new(180.0)
    for index in range(1, 101):
        rcf.addBpmShift(
            chart,
            180.0 + (index % 7) * 3.0,
            index * 4.0,
        )
    for index in range(1, 101):
        rcf.addCanvasSpeed(
            chart,
            0,
            index * 4.0,
            1.0 + (index % 5) * 0.1,
        )
    for index in range(1, 101):
        rcf.addCameraScale(
            chart,
            index * 5.0,
            scale=1.0 + (index % 3) * 0.1,
        )
    return chart


def _y_border_chart() -> dict:
    return _event_chart()


SCENARIOS = {
    "trans_color_40x50": {
        "description": "transColor over 40 lines x 50 line points",
        "prepare": lambda: copy.deepcopy(_line_chart(40, 50)),
        "operation": lambda chart: rcf.transColor(
            chart,
            ["#FF0000", "#FFFFFF"],
            ["#00FF00", "#0000FF"],
            type="linePoint",
        ),
    },
    "set_line_point_color_by_list_2000": {
        "description": "setLinePointColorByList over a 2000-point line",
        "prepare": lambda: copy.deepcopy(_wide_line_chart(2000)),
        "operation": lambda chart: rcf.setLinePointColorByList(
            chart,
            0,
            0,
            1999,
            "#FF0000",
            "#0000FF",
        ),
    },
    "refresh_40x50_delayed": {
        "description": "refresh a 40-line x 50-point chart built with delayed floor calculation",
        "prepare": lambda: _line_chart(40, 50, delayed=True),
        "operation": lambda chart: rcf.refresh(chart),
    },
    "draw_polygon_512": {
        "description": "drawPolygon with 512 vertices, fill + border",
        "prepare": _draw_polygon_state,
        "operation": lambda state: rcf.drawPolygon(
            state[0],
            0,
            state[1],
            True,
            True,
            precision=0.001,
            bordersize=[1],
            fillerstyle="linear",
            fillerinfo=[45, ["#FF0000", 0.2], ["#00FF00", 0.8]],
        ),
    },
    "draw_ellipse_0_001": {
        "description": "drawEllipse with fill + border and lineprecision=0.001",
        "prepare": _draw_ellipse_state,
        "operation": lambda state: rcf.drawEllipse(
            state[0],
            0,
            state[1],
            0.25,
            0.20,
            True,
            True,
            lineprecision=0.001,
            colorList=["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"],
            fillerstyle="linear",
            fillerinfo=[45, ["#FF0000", 0.2], ["#00FF00", 0.8]],
        ),
    },
    "get_y_border_1000": {
        "description": "getYBorderByChart called 1000 times",
        "prepare": _y_border_chart,
        "operation": lambda chart: [
            rcf.getYBorderByChart(
                chart,
                40.0 + index * 0.05,
                0,
                1.0,
                "solidTop",
            )
            for index in range(1000)
        ],
    },
}


def _profile(operation, state, prof_dir: Path, name: str) -> None:
    profile = cProfile.Profile()
    profile.enable()
    operation(state)
    profile.disable()
    prof_path = prof_dir / f"{name}.prof"
    profile.dump_stats(prof_path)
    txt_path = prof_dir / f"{name}_profile.txt"
    with txt_path.open("w", encoding="utf-8") as file:
        stats = pstats.Stats(profile, stream=file)
        stats.sort_stats("cumulative").print_stats(30)


def _run_scenario(name: str, spec: dict, repeats: int, profile: bool, output: Path) -> dict:
    times = []
    for _ in range(repeats):
        state = spec["prepare"]()
        started = time.perf_counter()
        spec["operation"](state)
        times.append(time.perf_counter() - started)

    result = {
        "name": name,
        "description": spec["description"],
        "repeats": repeats,
        "min_seconds": min(times),
        "median_seconds": statistics.median(times),
        "max_seconds": max(times),
        "all_seconds": times,
    }
    if profile:
        profile_state = spec["prepare"]()
        _profile(spec["operation"], profile_state, output, name)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-profile", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE.parent / "_output",
    )
    args = parser.parse_args()
    repeats = 1 if args.quick else max(1, args.repeats)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"Output: {output}")

    results = []
    for name, spec in SCENARIOS.items():
        print(f"\n[{name}] {spec['description']}")
        result = _run_scenario(
            name,
            spec,
            repeats,
            not args.no_profile,
            output,
        )
        results.append(result)
        print(
            "  min={:.6f}s median={:.6f}s max={:.6f}s".format(
                result["min_seconds"],
                result["median_seconds"],
                result["max_seconds"],
            )
        )

    payload = {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "repeats": repeats,
        "scenarios": results,
    }
    result_path = output / "baseline.json"
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
