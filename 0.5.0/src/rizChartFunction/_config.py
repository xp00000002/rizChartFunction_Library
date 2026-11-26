"""Global configuration for exception defaults and user settings.

The configuration module is independent of the chart modules. It reads a JSON
file with optional ``language`` and ``isReturnException`` fields. Invalid
settings produce warnings and safe defaults; importing the package never fails
because of a malformed user configuration.
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from threading import RLock
from typing import Any

DEFAULT_RETURN_EXCEPTION = False
_CONFIG_FILENAME = "config.json"
_PROJECT_CONFIG_FILENAME = ".rizchartfunction.json"
_USER_CONFIG_DIRECTORY = ".rizchartfunction"

_LOCK = RLock()
_runtime_override: bool | None = None
_config_data: dict[str, Any] = {}
_config_source = "default"
_environment_default: bool | None = None
_default_return_exception = DEFAULT_RETURN_EXCEPTION


def _warn(message: str) -> None:
    warnings.warn(message, RuntimeWarning, stacklevel=3)


def _config_path_from_environment() -> Path | None:
    value = os.environ.get("RIZCHART_CONFIG")
    if not value:
        return None
    return Path(value).expanduser()


def _selected_config_path() -> Path | None:
    env_path = _config_path_from_environment()
    if env_path is not None:
        return env_path

    project_path = Path.cwd() / _PROJECT_CONFIG_FILENAME
    if project_path.is_file():
        return project_path

    user_path = Path.home() / _USER_CONFIG_DIRECTORY / _CONFIG_FILENAME
    if user_path.is_file():
        return user_path

    return None


def _read_config(path: Path | None) -> tuple[dict[str, Any], str]:
    if path is None:
        return {}, "default"
    if not path.is_file():
        _warn(
            f"RizChartFunction: config file {path!s} does not exist. "
            "Using default settings."
        )
        return {}, str(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        _warn(
            f"RizChartFunction: cannot read config {path!s}: {error}. "
            "Using default settings."
        )
        return {}, str(path)
    if not isinstance(data, dict):
        _warn(
            f"RizChartFunction: config {path!s} must be a JSON object. "
            "Using default settings."
        )
        return {}, str(path)
    return data, str(path)


def _parse_environment_default() -> bool | None:
    raw = os.environ.get("RIZCHART_RETURN_EXCEPTION")
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    _warn(
        "RizChartFunction: invalid RIZCHART_RETURN_EXCEPTION="
        f"{raw!r}; using False."
    )
    return False


def _config_return_exception(data: dict[str, Any]) -> bool:
    if "isReturnException" not in data:
        return DEFAULT_RETURN_EXCEPTION
    value = data["isReturnException"]
    if not isinstance(value, bool):
        _warn(
            "RizChartFunction: config field isReturnException must be bool; "
            "using False."
        )
        return DEFAULT_RETURN_EXCEPTION
    return value


def _reload_state() -> bool:
    """Re-read config/environment and update the cached default."""
    global _config_data, _config_source, _environment_default
    global _default_return_exception

    path = _selected_config_path()
    data, source = _read_config(path)
    environment_default = _parse_environment_default()
    if _runtime_override is not None:
        enabled = _runtime_override
    elif environment_default is not None:
        enabled = environment_default
    else:
        enabled = _config_return_exception(data)

    with _LOCK:
        _config_data = data
        _config_source = source
        _environment_default = environment_default
        _default_return_exception = enabled
    return enabled


def get_config_data() -> dict[str, Any]:
    """Return the cached configuration dictionary.

    Complexity: O(1). This internal helper is used by the language manager.
    """
    with _LOCK:
        return dict(_config_data)


def get_config_source() -> str:
    """Return the selected config source for diagnostics.

    Complexity: O(1).
    """
    with _LOCK:
        return _config_source


def get_default_return_exception() -> bool:
    """Return the global default for ``isReturnException``.

    The value is resolved in this order: runtime
    :func:`set_default_return_exception` override, environment variable
    ``RIZCHART_RETURN_EXCEPTION``, config file field ``isReturnException``,
    then ``False``.

    Complexity: O(1). This function has no failure path and does not accept
    ``isReturnException``.
    """
    with _LOCK:
        return _default_return_exception


def set_default_return_exception(enabled: bool) -> bool:
    """Set a process-wide default for ``isReturnException``.

    Explicit per-call ``isReturnException=True`` or
    ``isReturnException=False`` always takes precedence over this setting.

    Parameters:
        enabled: New global default. Non-bool values are rejected with a
            warning; the previous value is kept unchanged.

    Returns:
        The active default. This function has no exception path and does not
        accept ``isReturnException``.

    Complexity: O(1).
    """
    global _runtime_override, _default_return_exception
    if not isinstance(enabled, bool):
        _warn(
            "RizChartFunction: set_default_return_exception() expects bool; "
            f"got {type(enabled).__name__}; keeping the current setting."
        )
        return get_default_return_exception()
    with _LOCK:
        _runtime_override = enabled
        _default_return_exception = enabled
    return enabled


def reload_config() -> bool:
    """Reload configuration files and environment settings.

    Clears the runtime exception-default override, re-reads the selected JSON
    config and environment variables, and refreshes the active language through
    :func:`rizChartFunction.reload_language` when that module is already
    imported.

    Returns:
        The active global exception default.

    Complexity: O(config file size + locale catalog size). This function has no
    exception path and does not accept ``isReturnException``.
    """
    global _runtime_override
    with _LOCK:
        _runtime_override = None
    enabled = _reload_state()
    try:
        from ._i18n import reload_language

        reload_language()
    except Exception:
        # Language loading is independent and may not be initialized during
        # early package bootstrap. Configuration must remain usable regardless.
        pass
    return enabled


# Initialize once at import. Warnings are non-fatal by design.
_reload_state()


__all__ = [
    "DEFAULT_RETURN_EXCEPTION",
    "get_config_data",
    "get_config_source",
    "get_default_return_exception",
    "reload_config",
    "set_default_return_exception",
]
