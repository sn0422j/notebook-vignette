"""型付きテーマ差分を確定パレットとCSSへ変換する。ファイルの読み込みは行わない。"""

from __future__ import annotations

from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

from .models import (
    FONT_FAMILY,
    MONO_FONT_FAMILY,
    ColorPalette,
    ResolvedTheme,
    ThemeConfig,
    ThemeName,
)

DEFAULT_COLORS = ColorPalette()


def _preset(name: ThemeName) -> tuple[ColorPalette, str]:
    """組み込みテーマの全色と構文強調スタイルを返す。"""
    colors = DEFAULT_COLORS.values()
    syntax = "friendly"
    if name == "dark":
        # Every surface, text, and border changes; no light-only subcomponents.
        for key in colors:
            if key.endswith("_bg") or key in {"paper", "heading_bg", "nav_active", "stripe"}:
                colors[key] = "#182633"
            elif "border" in key or key == "line":
                colors[key] = "#3c5062"
            else:
                colors[key] = "#b6c6d4"
        colors.update(
            background="#0e1822",
            paper="#14212d",
            ink="#e5eef6",
            text="#d1dfeb",
            muted="#acbdcc",
            accent="#66c8cb",
            inline_text="#81dbd0",
            shadow="#00000030",
            success="#67cda7",
            error_text="#ffb4a8",
            error_bg="#352426",
            warning_bg="#302c21",
            warning_text="#ebca92",
            ansi_red="#ff9999",
            ansi_green="#90dca5",
            ansi_blue="#91bdff",
            ansi_yellow="#ecd083",
            ansi_magenta="#d3a1ed",
        )
        syntax = "native"
    elif name == "paper":
        colors.update(
            background="#f4f0e7",
            paper="#fffdf8",
            ink="#38332d",
            text="#433f37",
            muted="#71685b",
            accent="#916333",
            line="#e2d9c8",
            quote_bg="#f4eee1",
            nav_active="#ebe1cd",
            code_bg="#f7f3ea",
            fold_bg="#faf6ee",
            summary_bg="#efe8d9",
            heading_bg="#efe8d9",
            stripe="#fbf8f1",
            inline_bg="#f2ecde",
        )
    return ColorPalette(**colors), syntax


def resolve_theme(settings: ThemeConfig | None = None) -> ResolvedTheme:
    """指定された項目をプリセットへ適用し、欠けた値のないテーマを返す。

    外部の辞書はconfig.parse_theme_configでThemeConfigへ変換してから渡す。
    構文強調スタイル名はPygmentsで検証し、未知の名前はValueErrorとする。
    """
    settings = settings or ThemeConfig()
    name = settings.name or "default"
    colors, syntax = _preset(name)
    syntax = settings.syntax_style if settings.syntax_style is not None else syntax
    try:
        get_style_by_name(syntax)
    except ClassNotFound as exc:
        raise ValueError(f"未知のPygmentsスタイル: {syntax}") from exc
    return ResolvedTheme(
        name=name,
        colors=colors.apply(settings.colors),
        syntax_style=syntax,
        font_family=settings.font_family if settings.font_family is not None else FONT_FAMILY,
        mono_font_family=settings.mono_font_family
        if settings.mono_font_family is not None
        else MONO_FONT_FAMILY,
        content_width=settings.content_width if settings.content_width is not None else "1240px",
        font_size=settings.font_size if settings.font_size is not None else "15px",
        line_height=settings.line_height if settings.line_height is not None else 1.94,
    )


def theme_css(theme: ResolvedTheme) -> str:
    """確定テーマから画面用と印刷用のCSS変数を生成する。"""
    tokens = theme.colors.values()
    tokens.update(
        font_family=theme.font_family,
        mono_font_family=theme.mono_font_family,
        content_width=theme.content_width,
        font_size=theme.font_size,
        line_height=str(theme.line_height),
    )
    declarations = ";".join(f"--{k.replace('_', '-')}:{v}" for k, v in tokens.items())
    scheme = "dark" if theme.name == "dark" else "light"
    print_colors = ";".join(
        f"--{k.replace('_', '-')}:{v}" for k, v in DEFAULT_COLORS.values().items()
    )
    css = ":root{" + declarations + ";color-scheme:" + scheme + "}"
    return css + "@media print{:root{" + print_colors + ";color-scheme:light}}"
