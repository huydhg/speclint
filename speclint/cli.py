"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .model import Document, discover, parse
from .report import as_json, markdown, terminal
from .rules import RULES, FileResult, check_links, lint


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="speclint",
        description="Soát chất lượng user story và PRD: AC không kiểm chứng được, "
        "thiếu negative path, metric không baseline, open question không chủ.",
    )
    p.add_argument("path", nargs="?", default=".", help="File hoặc thư mục (mặc định: .)")
    p.add_argument("--format", choices=("terminal", "markdown", "json"), default="terminal")
    p.add_argument("-o", "--out", help="Ghi kết quả ra file thay vì stdout")
    p.add_argument(
        "--min-severity", choices=("error", "warn", "info"), default="info",
        help="Chỉ báo từ mức này trở lên (mặc định: info)",
    )
    p.add_argument("--only", help="Chỉ chạy các rule này, phân tách bằng dấu phẩy")
    p.add_argument("--skip", help="Bỏ qua các rule này, phân tách bằng dấu phẩy")
    p.add_argument("--no-hints", action="store_true", help="Ẩn dòng gợi ý sửa")
    p.add_argument("--no-links", action="store_true", help="Bỏ qua kiểm tra wikilink")
    p.add_argument(
        "--fail-on", choices=("error", "warn", "info", "never"), default="error",
        help="Exit code 1 khi có vấn đề từ mức này trở lên (mặc định: error)",
    )
    p.add_argument("--list-rules", action="store_true", help="In danh sách rule rồi thoát")
    p.add_argument("--version", action="version", version=f"speclint {__version__}")
    return p


def list_rules() -> str:
    rows = ["ID      Mức    Áp dụng       Nội dung", "-" * 78]
    for r in sorted(RULES, key=lambda r: r.id):
        rows.append(f"{r.id:<7} {r.severity:<6} {','.join(r.applies_to):<13} {r.title}")
    rows.append(f"{'LK001':<7} {'warn':<6} {'*':<13} Wikilink trỏ tới file không tồn tại")
    return "\n".join(rows)


def _force_utf8() -> None:
    """Windows defaults stdout to the locale codepage (cp1252 on a VN machine).
    Redirecting output to a file or a pipe then crashes on the first Vietnamese
    character. Nothing about this tool is ASCII, so force UTF-8 everywhere.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - detached stream
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    args = build_parser().parse_args(argv)

    if args.list_rules:
        print(list_rules())
        return 0

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Không tìm thấy: {root}", file=sys.stderr)
        return 2

    files = discover(root)
    if not files:
        print(f"Không có file .md nào trong {root}", file=sys.stderr)
        return 2

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    skip = {s.strip() for s in args.skip.split(",")} if args.skip else None

    docs: list[Document] = []
    for f in files:
        try:
            docs.append(parse(f))
        except Exception as e:  # pragma: no cover
            print(f"Bỏ qua {f}: {e}", file=sys.stderr)

    # chỉ soát story/prd; file khác vẫn dùng làm đích wikilink
    targets = [d for d in docs if d.doc_type in {"story", "prd"}]
    known = {d.path.stem.lower() for d in docs} | {
        d.path.with_suffix("").as_posix().lower() for d in docs
    }

    order = {"error": 0, "warn": 1, "info": 2}
    cutoff = order[args.min_severity]

    results: list[FileResult] = []
    for d in targets:
        fs = lint(d, only=only, skip=skip)
        if not args.no_links and (not only or "LK001" in only) and not (skip and "LK001" in skip):
            fs += check_links(d, known)
        fs = [f for f in fs if order[f.severity] <= cutoff]
        fs.sort(key=lambda f: (f.line, f.rule))
        n_sections = len([s for s in d.sections if s.heading != "(preamble)"])
        results.append(
            FileResult(
                path=d.path,
                findings=fs,
                n_criteria=len(d.criteria),
                n_sections=n_sections,
            )
        )

    base = root if root.is_dir() else root.parent
    if args.format == "markdown":
        text = markdown(results, base)
    elif args.format == "json":
        text = as_json(results, base)
    else:
        text = terminal(results, base, show_hints=not args.no_hints)

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)

    if args.fail_on == "never":
        return 0
    limit = order[args.fail_on]
    worst = min((order[f.severity] for r in results for f in r.findings), default=99)
    return 1 if worst <= limit else 0
