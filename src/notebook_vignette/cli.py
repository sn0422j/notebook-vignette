"""Command line interface and deterministic batch planning."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from io import TextIOWrapper
from pathlib import Path

from . import __version__
from .config import load_config, parse_overrides
from .models import PRESETS, AppConfig, ConfigOverrides, RenderOverrides, ThemeConfig


def parser() -> argparse.ArgumentParser:
    """公開コマンドの引数を定義する。Notebook関連の依存関係は読み込まない。"""
    result = argparse.ArgumentParser(
        description="Notebookを実行せず、保存済み内容を目次付きHTMLに変換します。"
    )
    result.add_argument("inputs", nargs="*", help=".ipynb / フォルダ / 引用符付きglobパターン")
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument(
        "--list-themes", action="store_true", help="テーマとカスタマイズ可能な色名を表示"
    )
    output = result.add_mutually_exclusive_group()
    output.add_argument("-o", "--output", type=Path, help="単一Notebookの出力ファイル")
    output.add_argument(
        "--output-dir", type=Path, help="出力先フォルダ（入力フォルダ内の階層を維持）"
    )
    result.add_argument("-r", "--recursive", action="store_true", help="フォルダを再帰的に検索")
    result.add_argument("--force", action="store_true", help="既存HTMLを上書き")
    result.add_argument("--json", action="store_true", help="結果の配列をJSONで標準出力へ出力")
    result.add_argument("--config", type=Path, help="設定TOML（パスは設定ファイルのフォルダ基準）")
    result.add_argument(
        "--set", action="append", default=[], metavar="KEY=VALUE", help="設定を上書き（複数指定可）"
    )
    result.add_argument("--theme", choices=["default", "dark", "paper"], help="組み込みテーマ")
    result.add_argument("--title", help="文書タイトル")
    result.add_argument("--date", help="表示日付（空文字で非表示）")
    code = result.add_mutually_exclusive_group()
    code.add_argument(
        "--collapse-code", action="store_true", default=None, help="入力コードを折りたたむ"
    )
    code.add_argument(
        "--hide-code", action="store_true", default=None, help="入力コードをHTMLから除去"
    )
    code.add_argument(
        "--show-code", action="store_true", help="設定ファイルに関わらず入力コードを開く"
    )
    result.add_argument("--toc-depth", type=int, choices=range(1, 7), help="目次の見出し深さ")
    result.add_argument("--mathjax", choices=["auto", "cdn", "none"], help="数式描画方式")
    result.add_argument(
        "--mathjax-js", type=Path, help="ローカルのMathJax 3 tex-svg-full.jsを埋め込む"
    )
    result.add_argument("--font", type=Path, help="フォントを埋め込む")
    result.add_argument("--font-license", type=Path, help="埋め込みフォントのライセンス文書")
    result.add_argument(
        "--trusted-html",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="入力HTML/JavaScriptを保持する（ブラウザで実行され得ます）",
    )
    result.add_argument(
        "--allow-outside-assets",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Notebookフォルダ外のローカル画像も取り込む",
    )
    return result


def plan_inputs(
    inputs: list[str], output: Path | None, output_dir: Path | None, recursive: bool, force: bool
) -> list[tuple[Path, Path]]:
    """入力を展開し、書き込み前に出力名の衝突と既存ファイルを確認する。"""
    discovered: dict[Path, Path] = {}
    for value in inputs:
        expanded = Path(value).expanduser()
        matches = (
            [str(expanded)]
            if expanded.exists()
            else sorted(glob.glob(str(expanded), recursive=recursive))
        )
        if not matches:
            raise ValueError(f"入力が見つかりません: {value}")
        count = 0
        for match in matches:
            path = Path(match).resolve()
            if path.is_dir():
                files = path.rglob("*") if recursive else path.iterdir()
                candidates = sorted(
                    p
                    for p in files
                    if p.is_file()
                    and p.suffix.lower() == ".ipynb"
                    and ".ipynb_checkpoints" not in p.parts
                )
                for candidate in candidates:
                    discovered.setdefault(candidate.resolve(), candidate.relative_to(path))
                    count += 1
            elif path.is_file() and path.suffix.lower() == ".ipynb":
                discovered.setdefault(path, Path(path.name))
                count += 1
            else:
                raise ValueError(f"入力は.ipynbファイルまたはフォルダです: {path}")
        if count == 0:
            raise ValueError(f"Notebookが見つかりません: {value}")
    if output and len(discovered) != 1:
        raise ValueError(
            "--output は単一Notebook専用です。複数入力には --output-dir を指定してください。"
        )
    planned = []
    destinations = set()
    for source, relative in discovered.items():
        destination = (
            (
                output
                if output
                else output_dir / relative.with_suffix(".html")
                if output_dir
                else source.with_suffix(".html")
            )
            .expanduser()
            .resolve()
        )
        if destination == source or destination.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("出力先は入力と異なる .html / .htm ファイルにしてください。")
        normalized = str(destination).casefold()
        if normalized in destinations:
            raise ValueError(
                f"出力名が衝突しています。入力ごとに出力先を分けてください: {destination}"
            )
        destinations.add(normalized)
        if destination.exists() and (not force or not destination.is_file()):
            raise FileExistsError(f"出力が既に存在します（--force で上書き）: {destination}")
        planned.append((source, destination))
    return planned


def settings_from_args(args: argparse.Namespace) -> AppConfig:
    """設定ファイル、通常のCLI引数、--setの順に型付き設定を合成する。"""
    collapse = args.collapse_code
    hide = args.hide_code
    if args.hide_code or args.collapse_code or args.show_code:
        collapse, hide = bool(args.collapse_code), bool(args.hide_code)
    flags = RenderOverrides(
        title=args.title,
        collapse_code=collapse,
        hide_code=hide,
        toc_depth=args.toc_depth,
        mathjax=args.mathjax,
        mathjax_js=args.mathjax_js,
        font=args.font,
        font_license=args.font_license,
        trusted_html=args.trusted_html,
        allow_outside_assets=args.allow_outside_assets,
        date=args.date,
    )
    settings = load_config(args.config).apply(
        ConfigOverrides(render=flags, theme=ThemeConfig(name=args.theme))
    )
    return settings.apply(parse_overrides(args.set))


def _configure_output_streams() -> None:
    """出力先の文字コードを保ち、表現できない文字はエスケープして表示する。

    Windowsのリダイレクト先など、UTF-8以外のストリームでも診断表示で
    変換を失敗させない。JSONは別途ensure_ascii=Trueで構文を保つ。
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    """バッチ変換を実行し、成功0・変換失敗1・設定/入力エラー2を返す。"""
    _configure_output_streams()
    command = parser()
    args = command.parse_args(argv)
    if args.list_themes:
        from .themes import DEFAULT_COLORS

        print(
            json.dumps(
                {"themes": PRESETS, "default_colors": DEFAULT_COLORS.values()},
                ensure_ascii=True,
                indent=2,
            )
        )
        return 0
    if not args.inputs:
        command.error("入力Notebookを指定してください。")
    try:
        from .renderer import render_notebook
        from .themes import resolve_theme

        settings = settings_from_args(args)
        resolve_theme(settings.theme)
        planned = plan_inputs(args.inputs, args.output, args.output_dir, args.recursive, args.force)
        protected = {args.config.resolve()} if args.config else set()
        protected.update(path.expanduser().resolve() for path in settings.render.resource_paths)
        if any(destination in protected for _, destination in planned):
            raise ValueError("出力先が設定ファイルまたは補助ファイルと重複しています。")
    except Exception as exc:
        print(f"設定または入力エラー: {exc}", file=sys.stderr)
        return 2
    results = []
    failed = False
    for source, destination in planned:
        try:
            stats = render_notebook(source, destination, config=settings, overwrite=args.force)
            results.append({"ok": True, **stats})
            if not args.json:
                print(f"{source} → {destination}")
                for note in stats["notes"]:
                    print(f"  注意: {note}", file=sys.stderr)
        except Exception as exc:
            failed = True
            results.append(
                {"ok": False, "source": str(source), "output": str(destination), "error": str(exc)}
            )
            print(f"変換できませんでした: {source}: {exc}", file=sys.stderr)
    if args.json:
        print(json.dumps(results, ensure_ascii=True, indent=2))
    return 1 if failed else 0
