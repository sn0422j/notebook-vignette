"""型付きの公開Python API。レンダラー本体は最初の利用時に読み込む。"""

from typing import TYPE_CHECKING

from .models import AppConfig, ColorOverrides, RenderConfig, ThemeConfig

if TYPE_CHECKING:
    from .renderer import NotebookRenderer, render_notebook

__all__ = [
    "AppConfig",
    "ColorOverrides",
    "RenderConfig",
    "ThemeConfig",
    "NotebookRenderer",
    "render_notebook",
]

__version__ = "0.2.0"


def __getattr__(name: str) -> object:
    """CLIのヘルプ表示時はJupyterを読み込まず、API利用時だけ読み込む。"""
    if name in {"NotebookRenderer", "render_notebook"}:
        from .renderer import NotebookRenderer, render_notebook

        return NotebookRenderer if name == "NotebookRenderer" else render_notebook
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
