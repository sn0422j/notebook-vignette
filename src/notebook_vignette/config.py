"""外部設定を検証し、共有データクラスへ変換する境界層。

辞書を扱うのはTOML・CLI・Notebook metadataの読み込み時だけ。
読み込み後はAppConfig / ConfigOverrides / ThemeConfigで受け渡す。
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import cast

from .models import (
    PRESETS,
    AppConfig,
    ColorOverrides,
    ConfigOverrides,
    MathJaxMode,
    RenderConfig,
    RenderOverrides,
    ThemeConfig,
)


def _table(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{label} は文字列キーのテーブルで指定してください。")
    return dict(value)


def _keys(data: Mapping[str, object], allowed: set[str], label: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"未知の設定: {label}.{', '.join(sorted(unknown))}")


def _string(data: Mapping[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{key} は文字列で指定してください。")
    return value


def _boolean(data: Mapping[str, object], key: str) -> bool | None:
    value = data.get(key)
    if value is not None and type(value) is not bool:
        raise ValueError(f"{key} は true / false で指定してください。")
    return value


def _path(data: Mapping[str, object], key: str, base: Path | None) -> Path | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, (str, Path)):
        raise ValueError(f"{key} はファイルパスで指定してください。")
    path = Path(value).expanduser()
    return (base / path).resolve() if base is not None else path


def parse_render_overrides(value: object, *, base: Path | None = None) -> RenderOverrides:
    """外部の部分設定を検証する。相対パスはbase指定時のみその場所で解決する。"""
    data = _table(value, "render")
    _keys(data, {f.name for f in fields(RenderOverrides)}, "render")
    depth = data.get("toc_depth")
    if depth is not None and type(depth) is not int:
        raise ValueError("render.toc_depth は整数で指定してください。")
    mode = _string(data, "mathjax")
    if mode is not None and mode not in ("auto", "cdn", "none"):
        raise ValueError("render.mathjax は auto / cdn / none です。")
    return RenderOverrides(
        title=_string(data, "title"),
        collapse_code=_boolean(data, "collapse_code"),
        hide_code=_boolean(data, "hide_code"),
        toc_depth=depth,
        mathjax=cast(MathJaxMode | None, mode),
        mathjax_js=_path(data, "mathjax_js", base),
        font=_path(data, "font", base),
        font_license=_path(data, "font_license", base),
        trusted_html=_boolean(data, "trusted_html"),
        allow_outside_assets=_boolean(data, "allow_outside_assets"),
        date=_string(data, "date"),
    )


def validate_render(value: object) -> RenderConfig:
    """外部の変換設定に既定値を補い、項目間の整合性も検証する。"""
    return RenderConfig().apply(parse_render_overrides(value))


def parse_theme_config(value: object) -> ThemeConfig:
    """外部のテーマ設定を型付き差分へ変換する。未知の色名もここで拒否する。"""
    data = _table(value, "theme")
    _keys(data, {f.name for f in fields(ThemeConfig)}, "theme")
    colors = _table(data.get("colors", {}), "theme.colors")
    _keys(colors, {f.name for f in fields(ColorOverrides)}, "theme.colors")
    color_values: dict[str, str] = {}
    for key, item in colors.items():
        if not isinstance(item, str):
            raise ValueError(f"theme.colors.{key} は16進色の文字列です。")
        color_values[key] = item
    name = _string(data, "name")
    if name is not None and name not in PRESETS:
        raise ValueError(f"未知のテーマ: {name}")
    height = data.get("line_height")
    if height is not None and type(height) not in (int, float):
        raise ValueError("theme.line_height は数値で指定してください。")
    return ThemeConfig(
        name=name,
        colors=ColorOverrides(**color_values),
        syntax_style=_string(data, "syntax_style"),
        font_family=_string(data, "font_family"),
        mono_font_family=_string(data, "mono_font_family"),
        content_width=_string(data, "content_width"),
        font_size=_string(data, "font_size"),
        line_height=float(cast(float, height)) if height is not None else None,
    )


def _parse_config(value: object, *, base: Path | None = None) -> ConfigOverrides:
    data = _table(value, "config")
    _keys(data, {"render", "theme"}, "config")
    return ConfigOverrides(
        render=parse_render_overrides(data.get("render", {}), base=base),
        theme=parse_theme_config(data.get("theme", {})),
    )


def load_config(path: Path | None) -> AppConfig:
    """明示指定されたTOMLを読み込み、検証済みのAppConfigを返す。

    pathがNoneなら既定設定を返す。設定ファイルは自動探索しない。
    補助ファイルの相対パスは、設定ファイルの親ディレクトリ基準。
    """
    if path is None:
        return AppConfig()
    path = path.expanduser().resolve()
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    settings = AppConfig().apply(_parse_config(data, base=path.parent))
    from .themes import resolve_theme

    resolve_theme(settings.theme)
    return settings


def parse_overrides(items: list[str]) -> ConfigOverrides:
    """--setのkey=valueを型付き差分へ変換する。文字列とTOMLの値を受け付ける。"""
    result: dict[str, object] = {}
    for item in items:
        key, separator, raw = item.partition("=")
        if not separator or not raw.strip():
            raise ValueError(f"--set は key=value で指定してください: {item}")
        parts = key.strip().split(".")
        if len(parts) < 2 or parts[0] not in {"render", "theme"} or any(not p for p in parts):
            raise ValueError(f"--set のキーが不正です: {key}")
        try:
            value = tomllib.loads("value = " + raw)["value"]
        except (tomllib.TOMLDecodeError, KeyError):
            value = raw
        cursor = result
        for part in parts[:-1]:
            if part not in cursor:
                cursor[part] = {}
            child = cursor[part]
            if not isinstance(child, dict):
                raise ValueError(f"--set のキーが衝突しています: {key}")
            cursor = cast(dict[str, object], child)
        cursor[parts[-1]] = value
    return _parse_config(result)
