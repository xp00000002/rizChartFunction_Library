"""Optional native-extension build for the setuptools backend.

The pure-Python installation path must not require CMake, Ninja, or a C++
compiler. Set ``RIZCHART_BUILD_NATIVE=OFF`` to skip the extension entirely.
"""

from __future__ import annotations

import os

from setuptools import Extension, setup


def _native_enabled() -> bool:
    value = os.environ.get("RIZCHART_BUILD_NATIVE", "ON")
    return value.strip().lower() not in {"0", "false", "off", "no"}


def _extensions() -> list[Extension]:
    if not _native_enabled():
        return []
    try:
        import pybind11
    except ImportError as error:
        raise RuntimeError(
            "RIZCHART_BUILD_NATIVE is enabled but pybind11 is not installed. "
            "Set RIZCHART_BUILD_NATIVE=OFF for a pure-Python install."
        ) from error

    if os.name == "nt":
        compile_args = ["/std:c++17"]
    else:
        compile_args = ["-std=c++17"]

    return [
        Extension(
            "rizChartFunction._rizchart_native",
            ["cpp/src/rizchart_native.cpp"],
            include_dirs=[pybind11.get_include()],
            language="c++",
            extra_compile_args=compile_args,
        )
    ]


setup(ext_modules=_extensions())
