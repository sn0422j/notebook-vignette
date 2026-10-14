"""入力・出力パスの検証と、HTMLファイルの安全な確定。"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .models import RenderConfig


@dataclass(frozen=True, slots=True)
class RenderPaths:
    """検証・正規化済みの入力Notebookと出力HTMLの絶対パス。"""

    source: Path
    destination: Path

    @classmethod
    def resolve(
        cls,
        notebook: str | Path,
        output: str | Path | None,
        config: RenderConfig,
        *,
        overwrite: bool,
    ) -> RenderPaths:
        """入力の存在、拡張子、上書き方針、補助ファイルとの衝突を検証する。"""
        source = Path(notebook).expanduser().resolve()
        if source.is_dir():
            source = source / "vignette.ipynb"  # Legacy Python API directory behavior.
        if not source.is_file() or source.suffix.lower() != ".ipynb":
            raise ValueError(f".ipynbファイルが見つかりません: {source}")
        destination = Path(output).expanduser().resolve() if output else source.with_suffix(".html")
        if destination == source or destination.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("出力先はNotebookと異なる .html または .htm ファイルにしてください。")
        if destination.exists() and not overwrite:
            raise FileExistsError(f"出力が既に存在します（--force で上書き）: {destination}")
        if any(path.expanduser().resolve() == destination for path in config.resource_paths):
            raise ValueError("出力先が入力の補助ファイルと重複しています。")
        return cls(source, destination)


def write_html(page: str, destination: Path, *, overwrite: bool) -> None:
    """完成したHTMLを一時ファイル経由で確定し、失敗時は一時ファイルを除去する。

    上書き時はos.replace、上書き禁止時はos.linkを使う。後者は同じ
    ファイルシステムのハードリンクを使い、並行実行による上書きも防ぐ。
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(page)
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
