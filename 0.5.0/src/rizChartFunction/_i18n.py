"""Internal language manager for runtime messages and documentation.

The manager is deliberately small and standard-library only. It discovers
bundled language files under ``rizChartFunction/locales`` and reads optional
user configuration at import time.

Language selection never makes package import fail. Missing or malformed
configuration, unknown languages, and missing catalog entries fall back to
English and then to a stable visible key.
"""

from __future__ import annotations

import inspect
import json
import os
import warnings
from importlib import resources
from pathlib import Path
from threading import RLock
from typing import Any

DEFAULT_LANGUAGE = "en"
_LOCALE_PACKAGE = "rizChartFunction"
_LOCALE_DIRECTORY = "locales"
_CONFIG_FILENAME = "config.json"
_PROJECT_CONFIG_FILENAME = ".rizchartfunction.json"
_USER_CONFIG_DIRECTORY = ".rizchartfunction"

_LOCK = RLock()
_current_language = DEFAULT_LANGUAGE
_current_catalog: dict[str, Any] = {}
_explicit_language: str | None = None
_language_source = "default"
_catalog_cache: dict[str, dict[str, Any]] = {}
_doc_namespaces: list[dict[str, Any]] = []
_doc_namespace_ids: set[int] = set()


def _warn(message: str) -> None:
    warnings.warn(message, RuntimeWarning, stacklevel=3)


def _locale_root():
    return resources.files(_LOCALE_PACKAGE).joinpath(_LOCALE_DIRECTORY)


def _discover_languages() -> dict[str, str]:
    """Return ``normalized code -> canonical code`` for bundled files."""
    result: dict[str, str] = {}
    try:
        root = _locale_root()
        entries = list(root.iterdir())
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError):
        entries = []
    for entry in entries:
        name = entry.name
        if not name.endswith(".json"):
            continue
        code = name[:-5]
        result[code.lower()] = code
    if DEFAULT_LANGUAGE not in result.values():
        result[DEFAULT_LANGUAGE] = DEFAULT_LANGUAGE
    return result


def _normalize_language(value: object) -> str | None:
    """Normalize a user language code to a bundled canonical code."""
    if not isinstance(value, str):
        return None
    raw = value.strip().replace("_", "-")
    if not raw:
        return None
    languages = _discover_languages()
    lowered = raw.lower()
    if lowered in languages:
        return languages[lowered]
    base = lowered.split("-", 1)[0]
    if base in languages:
        return languages[base]
    for normalized, canonical in languages.items():
        if normalized.startswith(base + "-"):
            return canonical
    return None


def _read_config_language(path: Path) -> str | None:
    """Read one JSON config file.

    A missing file returns ``None``. An existing but invalid file returns the
    default language so an explicitly selected broken config cannot silently
    select a lower-priority file.
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        _warn(
            f"RizChartFunction: cannot read language config {path!s}: {error}. "
            "Falling back to English."
        )
        return DEFAULT_LANGUAGE
    if not isinstance(data, dict):
        _warn(
            f"RizChartFunction: language config {path!s} must be a JSON object. "
            "Falling back to English."
        )
        return DEFAULT_LANGUAGE
    language = data.get("language")
    if not isinstance(language, str) or not language.strip():
        _warn(
            f"RizChartFunction: language config {path!s} must contain a non-empty "
            '"language" string. Falling back to English.'
        )
        return DEFAULT_LANGUAGE
    return language


def _config_path_from_environment() -> Path | None:
    value = os.environ.get("RIZCHART_CONFIG")
    if not value:
        return None
    return Path(value).expanduser()


def _resolve_configured_language() -> tuple[str, str]:
    """Resolve language from environment and config files.

    Precedence is documented in ``I18N_PLAN.md``. Invalid values fall back to
    English rather than raising during import.
    """
    env_language = os.environ.get("RIZCHART_LANGUAGE")
    if env_language:
        normalized = _normalize_language(env_language)
        if normalized is None:
            _warn(
                f"RizChartFunction: unknown RIZCHART_LANGUAGE={env_language!r}. "
                "Falling back to English."
            )
            return DEFAULT_LANGUAGE, "environment-invalid"
        return normalized, "environment"

    env_config = _config_path_from_environment()
    if env_config is not None:
        raw = _read_config_language(env_config)
        if raw is None:
            _warn(
                f"RizChartFunction: RIZCHART_CONFIG file {env_config!s} does not "
                "exist. Falling back to English."
            )
            return DEFAULT_LANGUAGE, "config-environment-missing"
        normalized = _normalize_language(raw)
        if normalized is None:
            _warn(
                f"RizChartFunction: unsupported language {raw!r} in {env_config!s}. "
                "Falling back to English."
            )
            return DEFAULT_LANGUAGE, "config-environment-invalid"
        return normalized, str(env_config)

    project_config = Path.cwd() / _PROJECT_CONFIG_FILENAME
    if project_config.is_file():
        raw = _read_config_language(project_config)
        if raw is not None:
            normalized = _normalize_language(raw)
            if normalized is not None:
                return normalized, str(project_config)
            _warn(
                f"RizChartFunction: unsupported language {raw!r} in "
                f"{project_config!s}. Falling back to English."
            )
            return DEFAULT_LANGUAGE, "project-invalid"

    user_config = (
        Path.home() / _USER_CONFIG_DIRECTORY / _CONFIG_FILENAME
    )
    if user_config.is_file():
        raw = _read_config_language(user_config)
        if raw is not None:
            normalized = _normalize_language(raw)
            if normalized is not None:
                return normalized, str(user_config)
            _warn(
                f"RizChartFunction: unsupported language {raw!r} in "
                f"{user_config!s}. Falling back to English."
            )
            return DEFAULT_LANGUAGE, "user-invalid"

    return DEFAULT_LANGUAGE, "default"


def _load_catalog(language: str) -> dict[str, Any]:
    """Load one bundled catalog, returning an empty catalog on failure."""
    if language in _catalog_cache:
        return _catalog_cache[language]
    path = _locale_root().joinpath(f"{language}.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError, OSError, ValueError) as error:
        _warn(
            f"RizChartFunction: cannot load locale {language!r}: {error}. "
            "Falling back to English."
        )
        data = {}
    if not isinstance(data, dict):
        _warn(
            f"RizChartFunction: locale {language!r} must be a JSON object. "
            "Falling back to English."
        )
        data = {}
    _catalog_cache[language] = data
    return data


def _activate(language: str, *, source: str) -> str:
    """Activate a canonical language. Caller holds no lock requirement."""
    global _current_language, _current_catalog, _language_source
    normalized = _normalize_language(language) or DEFAULT_LANGUAGE
    catalog = _load_catalog(normalized)
    if not catalog and normalized != DEFAULT_LANGUAGE:
        normalized = DEFAULT_LANGUAGE
        catalog = _load_catalog(DEFAULT_LANGUAGE)
    with _LOCK:
        _current_language = normalized
        _current_catalog = catalog
        _language_source = source
    return normalized


def _lookup(catalog: dict[str, Any], section: str, key: str) -> str | None:
    values = catalog.get(section)
    if not isinstance(values, dict):
        return None
    value = values.get(key)
    return value if isinstance(value, str) else None


def _message_text(key: str) -> str | None:
    """Look up a message template in the active catalog, then English."""
    with _LOCK:
        catalog = _current_catalog
        language = _current_language
    text = _lookup(catalog, "messages", key)
    if text is None and language != DEFAULT_LANGUAGE:
        text = _lookup(_load_catalog(DEFAULT_LANGUAGE), "messages", key)
    return text


def _format_message(text: str, values: dict[str, Any]) -> str:
    if not values:
        return text
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError):
        return text


def translate_message(key: str, **values: Any) -> str:
    """Return a localized message template result.

    Missing keys fall back to English and then to ``key`` itself. This helper
    is used by the exception layer.
    """
    text = _message_text(key)
    if text is None:
        return key
    return _format_message(text, values)


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


def _text_value(value: object) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return repr(value)
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return repr(value)


def _path_text(path: object) -> str:
    if isinstance(path, (list, tuple)):
        return ".".join(str(item) for item in path)
    return str(path)


_EXPECTED_TRANSLATIONS = {
    "有效的画布索引": "a valid canvas index",
    "HEX 字符串或 RGB(A) 列表": "a HEX string or RGB(A) list",
    "有限数、>= 0，且 BPM 时间轴可用": (
        "a finite number >= 0 with a usable BPM timeline"
    ),
    "可用的 BPM、画布和节点结构": "usable BPM, canvas and node structures",
    "HEX 字符串、RGB(A) 列表或 RGBA dict": (
        "a HEX string, RGB(A) list or RGBA dict"
    ),
    "包含有限数 time 的规格 dict": "a spec dict with a finite time",
    "有效插入类型和正数精度": "a valid insert type and positive precision",
    "有效嵌套索引且目标节点存在后续节点": (
        "valid nested indices and a following target node"
    ),
    "有限数且 > 0": "a finite number > 0",
    "可重算 floorPosition 的谱面结构": (
        "a chart structure that can recalculate floorPosition"
    ),
    "所有选中项均可复制": "all selected items can be copied",
    "至少一个有效项": "at least one valid item",
    "有限数": "a finite number",
    "int（负索引从末尾计算）": "int (negative indices count from the end)",
    "time 有限且 value 为有限正数": "a finite time and a finite positive value",
    "可换算的非负 tick": "a convertible non-negative tick",
    "包含有效整数 lineindex/lineIndex 的规格": (
        "a spec with an integer lineindex/lineIndex"
    ),
    "有效 HEX/RGB(A) 颜色": "a valid HEX/RGB(A) color",
    "有限数且 >= 0": "a finite number >= 0",
    "new_time >= 前一节点 time": "new_time >= previous node time",
    "颜色或等长颜色列表": "a color or an equal-length color list",
    "非空关键点列表或 None": "a non-empty key-point list or None",
    "包含有效整数 canvasindex/canvasIndex 的规格": (
        "a spec with an integer canvasindex/canvasIndex"
    ),
    "目标画布在尾部时间有有效位置": (
        "target canvas has a valid position at the tail time"
    ),
    "可映射的画布索引、时间和偏移": (
        "mappable canvas indices, times and offsets"
    ),
    "所有选中线节点均可复制": "all selected line points can be copied",
    "所有线组均可写入谱面": "all line groups can be written to the chart",
    "int 或 list[int]": "int or list[int]",
    "填充参数列表": "a fill parameter list",
    "所有选中节点均可应用缓动": "all selected nodes can accept easing",
    "子节点列表": "a child-node list",
    "存在且可读取的字体文件": "an existing readable font file",
    "可解析的字形和有效布局参数": "parseable glyphs and valid layout parameters",
    "可插入的 Riztime 时间顺序": "an insertable Riztime time order",
    "有效的 chart、cameraMove 和索引": (
        "a valid chart, cameraMove and index"
    ),
    "int（越界会夹取到 0..18）": "int (clamped to 0..18)",
    "所有选中节点均可写入缓动": "all selected nodes can accept easing",
    "所有选中 BPM 节点均可复制": "all selected BPM nodes can be copied",
    "所有选中 Riztime 均可复制": "all selected Riztimes can be copied",
    "所有选中画布均可复制": "all selected canvases can be copied",
    "所有选中 BPM 节点均可插入": "all selected BPM nodes can be inserted",
    "所有选中 Riztime 均可插入": "all selected Riztimes can be inserted",
    "所有选中画布子节点均可插入": "all selected canvas child nodes can be inserted",
    "所有选中画布子节点均可复制": "all selected canvas child nodes can be copied",
    "所有选中摄像机节点均可插入": "all selected camera nodes can be inserted",
    "所有选中摄像机节点均可复制": "all selected camera nodes can be copied",
}


def _safe_expected(value: object) -> str:
    if value is None:
        return "?"
    if isinstance(value, str):
        if not _contains_cjk(value):
            return value
        translated = _EXPECTED_TRANSLATIONS.get(value)
        return translated if translated is not None else "the allowed range"
    return _text_value(value)


def translate_expected(value: object) -> str:
    """Return language-safe expected text for exception fields.

    Chinese ``expected`` descriptions are not emitted in English mode; the
    detailed English message already carries the relevant constraints where
    available. Non-Chinese technical values such as ``int`` or ``dict`` are
    preserved unchanged. This helper has no failure path.
    """
    if get_language() != DEFAULT_LANGUAGE:
        return _text_value(value) if not isinstance(value, str) else value
    return _safe_expected(value)


def _failure_values(failure: object) -> dict[str, Any]:
    fields = failure.fields()
    actual = fields.get("actual", "?")
    values = {
        "parameter": fields.get("parameter", "?"),
        "actual": _text_value(actual),
        "expected": _safe_expected(fields.get("expected")),
        "path": _path_text(fields.get("path", "?")),
        "index": fields.get("index", "?"),
        "length": fields.get("length", "?"),
        "failed_indices": _text_value(fields.get("failed_indices", [])),
        "unexpected_parts": fields.get("unexpected_parts", "?"),
        "missing_parts": fields.get("missing_parts", "?"),
        "error_values": fields.get("error_values", "?"),
    }
    return values


def translate_failure(failure: object) -> str:
    """Render a failure message for the active language.

    Chinese mode preserves the function's existing detailed source message.
    English mode uses semantic message templates keyed by ``reason_code`` and
    structured failure fields. If a specialized template is absent, it falls
    back to a generic but still field-aware English message. This guarantees
    that default English output never leaks a Chinese fallback message.
    """
    language = get_language()
    original = getattr(failure, "message", "")
    if language != DEFAULT_LANGUAGE:
        return original
    values = _failure_values(failure)
    fields = failure.fields()
    code = getattr(failure, "code", None)
    if code:
        key = f"failure.{code}"
        if code == "index.out_of_range" and "length" not in fields:
            key = "failure.index.out_of_range_no_length"
        text = _message_text(key)
        if text is not None:
            return _format_message(text, values)
    if values["parameter"] != "?":
        return translate_message("failure.parameter_invalid", **values)
    if values["path"] != "?":
        return translate_message("failure.path_invalid", **values)
    return translate_message("failure.generic", **values)


def translate_doc(function_name: str) -> str | None:
    """Return a localized public-function docstring, or ``None``.

    ``None`` means no catalog entry exists. The English layer uses a concise
    generated fallback so a Chinese source docstring never leaks into default
    English output.
    """
    with _LOCK:
        catalog = _current_catalog
        language = _current_language
    text = _lookup(catalog, "docs", function_name)
    if text is None and language != DEFAULT_LANGUAGE:
        text = _lookup(_load_catalog(DEFAULT_LANGUAGE), "docs", function_name)
    return text


def _generated_english_doc(function_name: str) -> str:
    """Return a concise English fallback for a function missing docs."""
    return (
        f"Public RizChartFunction operation ``{function_name}``.\n\n"
        "See the function signature for parameters and return values."
    )


def apply_docstrings(namespace: dict[str, Any]) -> None:
    """Apply localized docstrings to a module namespace.

    This is called after public functions have been wrapped for
    ``isReturnException`` so ``functools.wraps`` cannot overwrite the localized
    documentation. It has no failure path and is intentionally cheap: one
    catalog lookup per exported function.
    """
    english = get_language() == DEFAULT_LANGUAGE
    for name in namespace.get("__all__", ()):
        function = namespace.get(name)
        if not inspect.isfunction(function):
            continue
        text = translate_doc(name)
        if text is None and english:
            text = _generated_english_doc(name)
        if text is not None:
            function.__doc__ = inspect.cleandoc(text)


def register_doc_namespace(namespace: dict[str, Any]) -> None:
    """Register a public module namespace and apply its current docstrings.

    The registry lets ``set_language()`` refresh already imported modules
    without re-importing Python modules. Complexity is ``O(number of exported
    functions in the module)`` on registration and language changes.
    """
    with _LOCK:
        namespace_id = id(namespace)
        if namespace_id not in _doc_namespace_ids:
            _doc_namespace_ids.add(namespace_id)
            _doc_namespaces.append(namespace)
    apply_docstrings(namespace)


def refresh_docstrings() -> None:
    """Reapply docstrings to all registered public modules.

    Complexity is ``O(total exported functions in imported package modules)``.
    Existing references to functions are updated in place. This function has no
    failure path and does not accept ``isReturnException``.
    """
    with _LOCK:
        namespaces = list(_doc_namespaces)
    for namespace in namespaces:
        apply_docstrings(namespace)


def get_language() -> str:
    """Return the active language code.

    Complexity: ``O(1)`` after import. This function has no failure path and
    therefore does not accept ``isReturnException``.

    The default is ``"en"`` unless a language was selected by
    :func:`set_language`, an environment variable, or a configuration file.
    """
    with _LOCK:
        return _current_language


def set_language(language: str) -> str:
    """Activate a language for the current Python process.

    Parameters:
        language: Language code such as ``"en"`` or ``"zh-CN"``. Region and
            separator variants such as ``"zh"`` and ``"zh_CN"`` are normalized.

    Returns:
        The canonical active language code. Unknown codes fall back to English.

    Complexity: ``O(size of the selected JSON catalog)`` on first load, then
    ``O(1)``. This function has no exception path and does not accept
    ``isReturnException``. A malformed catalog or unknown code is reported as a
    warning and falls back to English.
    """
    global _explicit_language
    normalized = _normalize_language(language)
    if normalized is None:
        _warn(
            f"RizChartFunction: unknown language {language!r}. "
            "Falling back to English."
        )
        normalized = DEFAULT_LANGUAGE
    active = _activate(normalized, source="runtime")
    with _LOCK:
        _explicit_language = active
    refresh_docstrings()
    return active


def reload_language() -> str:
    """Re-read configuration and activate its language.

    The runtime ``set_language()`` override is cleared; configuration,
    environment variables, and defaults are evaluated again.

    Complexity: ``O(size of the config file + size of the selected JSON
    catalog)``; catalog files are cached after the first read. This function
    has no exception path and does not accept ``isReturnException``.
    """
    global _explicit_language
    with _LOCK:
        _explicit_language = None
        _catalog_cache.clear()
    language, source = _resolve_configured_language()
    active = _activate(language, source=source)
    refresh_docstrings()
    return active


def available_languages() -> tuple[str, ...]:
    """Return bundled canonical language codes.

    The default language is first, followed by the remaining codes in sorted
    order.

    Complexity: ``O(number of locale files)`` and does not load catalog
    contents. This function has no failure path and does not accept
    ``isReturnException``.
    """
    codes = set(_discover_languages().values())
    codes.add(DEFAULT_LANGUAGE)
    rest = sorted(code for code in codes if code != DEFAULT_LANGUAGE)
    return (DEFAULT_LANGUAGE, *rest)


# Initialize on import. Configuration and bundle problems only produce warnings;
# importing the main package must remain possible on a minimal installation.
_resolved_language, _resolved_source = _resolve_configured_language()
_activate(_resolved_language, source=_resolved_source)
