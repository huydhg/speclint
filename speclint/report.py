"""Output formats: terminal, markdown, json."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

from .rules import FileResult, RULES

# ---------------------------------------------------------------- colour

_FORCE = os.environ.get("SPECLINT_COLOR")
COLOR = _FORCE == "1" or (_FORCE != "0" and sys.stdout.isatty())

if os.name == "nt" and COLOR:  # enable ANSI on legacy Windows consoles
    try:
        import ctypes

        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)
    except Exception:
        pass


def c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if COLOR else s


DIM, BOLD = "2", "1"
SEV_COLOR = {"error": "31", "warn": "33", "info": "36"}
SEV_LABEL = {"error": "lỗi  ", "warn": "cảnh ", "info": "gợi ý"}
SEV_ICON = {"error": "x", "warn": "!", "info": "i"}
SEV_MD = {"error": "⛔", "warn": "⚠️", "info": "💡"}


def _rel(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _titles() -> dict[str, str]:
    t = {r.id: r.title for r in RULES}
    t["LK001"] = "Wikilink hỏng"
    return t


# ---------------------------------------------------------------- terminal


def terminal(results: list[FileResult], root: Path, show_hints: bool = True) -> str:
    out: list[str] = []
    total: Counter = Counter()

    for res in results:
        total.update(f.severity for f in res.findings)
        if res.clean:
            continue
        rel = _rel(res.path, root)
        out.append(
            c(BOLD, str(rel))
            + "  "
            + c(DIM, f"điểm {res.score}/100 · hạng {res.grade} · "
                     f"{len(res.findings)} vấn đề trên {res.n_criteria} AC")
        )
        for f in res.findings:
            sev = c(SEV_COLOR[f.severity], f"{SEV_ICON[f.severity]} {SEV_LABEL[f.severity]}")
            out.append(f"  {sev} {c(DIM, f.rule)}  {f.message}")
            out.append(c(DIM, f"         {rel}:{f.line}"))
            if show_hints and f.hint:
                out.append(c(DIM, f"         → {f.hint}"))
        out.append("")

    clean = [r for r in results if r.clean]
    out.append(c(BOLD, "Tổng kết"))
    out.append(
        f"  {len(results)} file · {len(clean)} sạch · "
        + c(SEV_COLOR["error"], f"{total['error']} lỗi")
        + " · "
        + c(SEV_COLOR["warn"], f"{total['warn']} cảnh báo")
        + " · "
        + c(SEV_COLOR["info"], f"{total['info']} gợi ý")
    )
    if results:
        avg = round(sum(r.score for r in results) / len(results))
        out.append(c(DIM, f"  Điểm trung bình: {avg}/100"))
    all_f = [f for r in results for f in r.findings]
    if all_f:
        titles = _titles()
        top = Counter(f.rule for f in all_f).most_common(3)
        out.append(
            c(DIM, "  Hay gặp nhất: "
              + ", ".join(f"{r} ({n}× {titles.get(r, '')})" for r, n in top))
        )
    return "\n".join(out)


# ---------------------------------------------------------------- markdown


def markdown(results: list[FileResult], root: Path) -> str:
    all_f = [f for r in results for f in r.findings]
    total = Counter(f.severity for f in all_f)
    titles = _titles()
    avg = round(sum(r.score for r in results) / len(results)) if results else 100

    lines = [
        "---",
        "type: report",
        "tags: [speclint]",
        "---",
        "# Spec lint report",
        "",
        f"Quét **{len(results)}** file · điểm trung bình **{avg}/100** · "
        f"**{total['error']}** lỗi · **{total['warn']}** cảnh báo · **{total['info']}** gợi ý",
        "",
        "## Theo file",
        "",
        "| File | AC | Điểm | Hạng | Lỗi | Cảnh báo | Gợi ý |",
        "| --- | ---: | ---: | :---: | ---: | ---: | ---: |",
    ]
    for res in sorted(results, key=lambda r: r.score):
        rel = _rel(res.path, root)
        cnt = Counter(f.severity for f in res.findings)
        link = rel.as_posix()
        if link.endswith(".md"):
            link = link[:-3]
        lines.append(
            f"| [[{link}]] | {res.n_criteria} | {res.score} | {res.grade} | "
            f"{cnt['error']} | {cnt['warn']} | {cnt['info']} |"
        )

    if all_f:
        lines += ["", "## Hay gặp nhất", "", "| Rule | Số lần | Nội dung |", "| --- | ---: | --- |"]
        for rid, n in Counter(f.rule for f in all_f).most_common():
            lines.append(f"| `{rid}` | {n} | {titles.get(rid, '')} |")

    lines += ["", "## Chi tiết", ""]
    for res in results:
        if res.clean:
            continue
        rel = _rel(res.path, root)
        lines += [f"### {rel.name}", ""]
        for f in res.findings:
            lines.append(f"- {SEV_MD[f.severity]} **`{f.rule}`** dòng {f.line} — {f.message}")
            if f.hint:
                lines.append(f"  - *{f.hint}*")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- json


def as_json(results: list[FileResult], root: Path) -> str:
    payload = [
        {
            "file": _rel(r.path, root).as_posix(),
            "criteria": r.n_criteria,
            "score": r.score,
            "grade": r.grade,
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "line": f.line,
                    "message": f.message,
                    "hint": f.hint,
                }
                for f in r.findings
            ],
        }
        for r in results
    ]
    summary = Counter(f.severity for r in results for f in r.findings)
    return json.dumps(
        {
            "summary": {
                "files": len(results),
                "error": summary["error"],
                "warn": summary["warn"],
                "info": summary["info"],
            },
            "files": payload,
        },
        ensure_ascii=False,
        indent=2,
    )
