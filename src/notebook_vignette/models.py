"""共有する設定モデル。外部の辞書はconfig.pyで検証してから変換する。

設定は変更不能なデータクラスとして受け渡す。OverridesとThemeConfigの
Noneは「指定なし」を表し、明示的なFalseや空文字を上書き時に保持する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Literal, cast

ThemeName = Literal["default", "dark", "paper"]
MathJaxMode = Literal["auto", "cdn", "none"]
PRESETS: tuple[ThemeName, ...] = ("default", "dark", "paper")
FONT_FAMILY = "VignetteJP, 'Noto Sans JP', 'Yu Gothic', Meiryo, sans-serif"
MONO_FONT_FAMILY = "'DejaVu Sans Mono', Consolas, monospace"


def _check_color(name: str, value: object) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value
    ):
        raise ValueError(f"theme.colors.{name} は16進色で指定してください。")


@dataclass(frozen=True, slots=True, kw_only=True)
class ColorOverrides:
    """指定された色だけを持つテーマ差分。Noneは既存の色を引き継ぐ。"""

    ink: str | None = None
    muted: str | None = None
    accent: str | None = None
    line: str | None = None
    paper: str | None = None
    background: str | None = None
    text: str | None = None
    nav: str | None = None
    nav_active: str | None = None
    note_text: str | None = None
    shadow: str | None = None
    quote_bg: str | None = None
    heading_bg: str | None = None
    heading_text: str | None = None
    table_border: str | None = None
    cell_border: str | None = None
    stripe: str | None = None
    index_text: str | None = None
    inline_text: str | None = None
    inline_bg: str | None = None
    code_bg: str | None = None
    code_border: str | None = None
    fold_bg: str | None = None
    summary_text: str | None = None
    summary_bg: str | None = None
    button_border: str | None = None
    button_text: str | None = None
    stream_border: str | None = None
    stream_bg: str | None = None
    warning_text: str | None = None
    warning_bg: str | None = None
    result_bg: str | None = None
    formula_bg: str | None = None
    formula_text: str | None = None
    toolbar_text: str | None = None
    toolbar_border: str | None = None
    toolbar_button: str | None = None
    success: str | None = None
    footer_text: str | None = None
    error_text: str | None = None
    error_bg: str | None = None
    error_border: str | None = None
    state_text: str | None = None
    notice_bg: str | None = None
    ansi_red: str | None = None
    ansi_green: str | None = None
    ansi_blue: str | None = None
    ansi_yellow: str | None = None
    ansi_magenta: str | None = None

    def __post_init__(self) -> None:
        for name, value in self.values().items():
            _check_color(name, value)

    def values(self) -> dict[str, str]:
        """CSS生成・外部表示用に、指定済みの色だけを新しい辞書へ変換する。"""
        return {
            f.name: cast(str, getattr(self, f.name))
            for f in fields(self)
            if getattr(self, f.name) is not None
        }

    def overlay(self, higher: ColorOverrides) -> ColorOverrides:
        """高優先度の値で上書きした新しい差分を返す。"""
        return ColorOverrides(**(self.values() | higher.values()))


@dataclass(frozen=True, slots=True, kw_only=True)
class ColorPalette:
    """すべての色が確定したパレット。既定値はdefaultテーマの配色。"""

    ink: str = "#18334c"
    muted: str = "#586879"
    accent: str = "#087f8c"
    line: str = "#dfe6eb"
    paper: str = "#fff"
    background: str = "#f1f4f6"
    text: str = "#293c4d"
    nav: str = "#617486"
    nav_active: str = "#e4eef0"
    note_text: str = "#72808d"
    shadow: str = "#18334c06"
    quote_bg: str = "#edf7f5"
    heading_bg: str = "#eef3f5"
    heading_text: str = "#405c70"
    table_border: str = "#cbd7df"
    cell_border: str = "#e5ebef"
    stripe: str = "#fafcfd"
    index_text: str = "#8795a1"
    inline_text: str = "#126271"
    inline_bg: str = "#edf3f5"
    code_bg: str = "#f5f8fa"
    code_border: str = "#dce5eb"
    fold_bg: str = "#f7f9fb"
    summary_text: str = "#6d7f8f"
    summary_bg: str = "#edf2f5"
    button_border: str = "#c9d6df"
    button_text: str = "#586f82"
    stream_border: str = "#cbdce2"
    stream_bg: str = "#fafcfc"
    warning_text: str = "#926428"
    warning_bg: str = "#fff9f0"
    result_bg: str = "#f1f7f7"
    formula_bg: str = "#f8fafb"
    formula_text: str = "#284d67"
    toolbar_text: str = "#8294a2"
    toolbar_border: str = "#c5d7df"
    toolbar_button: str = "#49687b"
    success: str = "#169879"
    footer_text: str = "#738591"
    error_text: str = "#873d34"
    error_bg: str = "#fff6f2"
    error_border: str = "#ce8c7e"
    state_text: str = "#7b6574"
    notice_bg: str = "#fff9eb"
    ansi_red: str = "#b93838"
    ansi_green: str = "#25823e"
    ansi_blue: str = "#2c5cab"
    ansi_yellow: str = "#947013"
    ansi_magenta: str = "#8951a5"

    def __post_init__(self) -> None:
        for name, value in self.values().items():
            _check_color(name, value)

    def values(self) -> dict[str, str]:
        """CSS生成・外部表示用の新しい辞書を返す。"""
        return {f.name: cast(str, getattr(self, f.name)) for f in fields(self)}

    def apply(self, overrides: ColorOverrides) -> ColorPalette:
        """色の差分を適用した新しいパレットを返す。"""
        return ColorPalette(**(self.values() | overrides.values()))


@dataclass(frozen=True, slots=True, kw_only=True)
class ThemeConfig:
    """設定元が明示したテーマ値。プリセットの既定値はthemes.pyで補う。"""

    name: ThemeName | None = None
    colors: ColorOverrides = field(default_factory=ColorOverrides)
    syntax_style: str | None = None
    font_family: str | None = None
    mono_font_family: str | None = None
    content_width: str | None = None
    font_size: str | None = None
    line_height: float | None = None

    def __post_init__(self) -> None:
        if self.name is not None and self.name not in PRESETS:
            raise ValueError(f"未知のテーマ: {self.name}")
        if not isinstance(self.colors, ColorOverrides):
            raise TypeError("colors は ColorOverrides で指定してください。")
        if self.syntax_style is not None and not isinstance(self.syntax_style, str):
            raise ValueError("theme.syntax_style は文字列で指定してください。")
        for key in ("font_family", "mono_font_family"):
            value = getattr(self, key)
            if value is not None and (
                not isinstance(value, str) or not re.fullmatch(r"[\w\s,'\".-]+", value)
            ):
                raise ValueError(f"theme.{key} はフォント名のカンマ区切りで指定してください。")
        for key in ("content_width", "font_size"):
            value = getattr(self, key)
            if value is not None and (
                not isinstance(value, str)
                or not re.fullmatch(
                    r"(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)(?:px|rem|em)", value
                )
            ):
                raise ValueError(f"theme.{key} は正の px / rem / em 値で指定してください。")
        if self.line_height is not None and (
            type(self.line_height) not in (int, float) or not 1 <= self.line_height <= 3
        ):
            raise ValueError("theme.line_height は1〜3の数値です。")

    def overlay(self, higher: ThemeConfig) -> ThemeConfig:
        """明示された値だけを上書きし、色はキー単位で引き継ぐ。"""
        return ThemeConfig(
            name=higher.name if higher.name is not None else self.name,
            colors=self.colors.overlay(higher.colors),
            syntax_style=higher.syntax_style
            if higher.syntax_style is not None
            else self.syntax_style,
            font_family=higher.font_family if higher.font_family is not None else self.font_family,
            mono_font_family=higher.mono_font_family
            if higher.mono_font_family is not None
            else self.mono_font_family,
            content_width=higher.content_width
            if higher.content_width is not None
            else self.content_width,
            font_size=higher.font_size if higher.font_size is not None else self.font_size,
            line_height=higher.line_height if higher.line_height is not None else self.line_height,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedTheme:
    """プリセットと全設定を合成した、HTML生成用の確定テーマ。"""

    name: ThemeName
    colors: ColorPalette
    syntax_style: str
    font_family: str = FONT_FAMILY
    mono_font_family: str = MONO_FONT_FAMILY
    content_width: str = "1240px"
    font_size: str = "15px"
    line_height: float = 1.94


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderOverrides:
    """CLIなどが指定した変換設定だけを保持する。Falseと空文字も有効な値。"""

    title: str | None = None
    collapse_code: bool | None = None
    hide_code: bool | None = None
    toc_depth: int | None = None
    mathjax: MathJaxMode | None = None
    mathjax_js: Path | None = None
    font: Path | None = None
    font_license: Path | None = None
    trusted_html: bool | None = None
    allow_outside_assets: bool | None = None
    date: str | None = None

    def __post_init__(self) -> None:
        _check_render(self, partial=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderConfig:
    """型・値・組み合わせを検証済みの変換設定。補助ファイルはPathで保持する。"""

    title: str | None = None
    collapse_code: bool = False
    hide_code: bool = False
    toc_depth: int = 3
    mathjax: MathJaxMode = "auto"
    mathjax_js: Path | None = None
    font: Path | None = None
    font_license: Path | None = None
    trusted_html: bool = False
    allow_outside_assets: bool = False
    date: str | None = None

    def __post_init__(self) -> None:
        _check_render(self, partial=False)
        if self.collapse_code and self.hide_code:
            raise ValueError("collapse_code と hide_code は併用できません。")
        if self.mathjax_js and self.mathjax == "none":
            raise ValueError("mathjax=none と mathjax_js は併用できません。")
        if self.font_license and not self.font:
            raise ValueError("font_license は font と一緒に指定してください。")

    def apply(self, overrides: RenderOverrides) -> RenderConfig:
        """部分設定を適用し、完成した設定の組み合わせを再検証する。"""
        return RenderConfig(
            title=overrides.title if overrides.title is not None else self.title,
            collapse_code=overrides.collapse_code
            if overrides.collapse_code is not None
            else self.collapse_code,
            hide_code=overrides.hide_code if overrides.hide_code is not None else self.hide_code,
            toc_depth=overrides.toc_depth if overrides.toc_depth is not None else self.toc_depth,
            mathjax=overrides.mathjax if overrides.mathjax is not None else self.mathjax,
            mathjax_js=overrides.mathjax_js
            if overrides.mathjax_js is not None
            else self.mathjax_js,
            font=overrides.font if overrides.font is not None else self.font,
            font_license=overrides.font_license
            if overrides.font_license is not None
            else self.font_license,
            trusted_html=overrides.trusted_html
            if overrides.trusted_html is not None
            else self.trusted_html,
            allow_outside_assets=overrides.allow_outside_assets
            if overrides.allow_outside_assets is not None
            else self.allow_outside_assets,
            date=overrides.date if overrides.date is not None else self.date,
        )

    @property
    def resource_paths(self) -> tuple[Path, ...]:
        """出力先との衝突確認に使う補助ファイルの一覧。"""
        return tuple(p for p in (self.font, self.font_license, self.mathjax_js) if p is not None)


def _check_render(value: RenderConfig | RenderOverrides, *, partial: bool) -> None:
    """型注釈を迂回する外部呼び出しでも、不正な設定を受け付けない。"""
    for key in ("collapse_code", "hide_code", "trusted_html", "allow_outside_assets"):
        item = getattr(value, key)
        if not (partial and item is None) and type(item) is not bool:
            raise ValueError(f"render.{key} は true / false で指定してください。")
    if not (partial and value.toc_depth is None) and (
        type(value.toc_depth) is not int or not 1 <= value.toc_depth <= 6
    ):
        raise ValueError("render.toc_depth は1〜6の整数です。")
    if not (partial and value.mathjax is None) and value.mathjax not in ("auto", "cdn", "none"):
        raise ValueError("render.mathjax は auto / cdn / none です。")
    for key in ("title", "date"):
        item = getattr(value, key)
        if item is not None and not isinstance(item, str):
            raise ValueError(f"render.{key} は文字列で指定してください。")
    for key in ("font", "font_license", "mathjax_js"):
        item = getattr(value, key)
        if item is not None and not isinstance(item, Path):
            raise TypeError(f"render.{key} は Path で指定してください。")


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfigOverrides:
    """ひとつの設定元から得た、変換設定とテーマ設定の差分。"""

    render: RenderOverrides = field(default_factory=RenderOverrides)
    theme: ThemeConfig = field(default_factory=ThemeConfig)


@dataclass(frozen=True, slots=True, kw_only=True)
class AppConfig:
    """CLI・Python API・レンダラーで共有するアプリケーション設定。"""

    render: RenderConfig = field(default_factory=RenderConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)

    def __post_init__(self) -> None:
        if not isinstance(self.render, RenderConfig) or not isinstance(self.theme, ThemeConfig):
            raise TypeError("AppConfigにはRenderConfigとThemeConfigを指定してください。")

    def apply(self, overrides: ConfigOverrides) -> AppConfig:
        """設定元の優先順位に従い、新しい設定を作成する。"""
        return AppConfig(
            render=self.render.apply(overrides.render), theme=self.theme.overlay(overrides.theme)
        )
