"""変換結果の集計と、公開API用のJSON互換形式。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from nbformat import NotebookNode

from .content import NotebookBody
from .models import ThemeName


class RenderStats(TypedDict):
    """render_notebookの戻り値。従来の辞書形式を型付きで維持する。"""

    source: str
    output: str
    title: str
    code_cells: int
    unexecuted_cells: int
    output_cells: int
    errors: int
    images: int
    tables: int
    embedded_local_images: int
    notes: list[str]
    theme: ThemeName


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderReport:
    """本文とNotebookから集計した結果。ページ表示とAPI出力で共有する。"""

    source: Path
    output: Path
    title: str
    code_cells: int
    unexecuted_cells: int
    output_cells: int
    errors: int
    images: int
    tables: int
    embedded_local_images: int
    notes: tuple[str, ...]
    theme: ThemeName

    @classmethod
    def collect(
        cls,
        notebook: NotebookNode,
        body: NotebookBody,
        source: Path,
        output: Path,
        embedded_images: int,
        notes: list[str],
        theme: ThemeName,
    ) -> RenderReport:
        """処理済みの本文から統計を集め、注意事項は出現順で重複を除く。"""
        codes = [cell for cell in notebook.cells if cell.cell_type == "code"]
        return cls(
            source=source,
            output=output,
            title=body.title,
            code_cells=len(codes),
            unexecuted_cells=sum(cell.execution_count is None for cell in codes),
            output_cells=sum(bool(cell.get("outputs")) for cell in codes),
            errors=sum(o.output_type == "error" for cell in codes for o in cell.get("outputs", [])),
            images=len(body.soup.find_all("img")),
            tables=len(body.soup.find_all("table")),
            embedded_local_images=embedded_images,
            notes=tuple(dict.fromkeys(notes)),
            theme=theme,
        )

    @property
    def badge(self) -> str:
        """ページ上部に表示する件数の要約。"""
        result = f"コード {self.code_cells} · 出力あり {self.output_cells} · 図 {self.images}"
        if self.unexecuted_cells:
            result += f" · 未実行 {self.unexecuted_cells}"
        if self.errors:
            result += f" · エラー出力 {self.errors}"
        return result

    def to_dict(self) -> RenderStats:
        """公開API・JSON出力に使う新しい辞書を返す。内部の不変データは共有しない。"""
        return RenderStats(
            source=str(self.source),
            output=str(self.output),
            title=self.title,
            code_cells=self.code_cells,
            unexecuted_cells=self.unexecuted_cells,
            output_cells=self.output_cells,
            errors=self.errors,
            images=self.images,
            tables=self.tables,
            embedded_local_images=self.embedded_local_images,
            notes=list(self.notes),
            theme=self.theme,
        )
