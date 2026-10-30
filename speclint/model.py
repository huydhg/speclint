"""Parse BA spec markdown (user stories, PRDs) into a model the rules can inspect."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# A markdown list marker: "-", "+", or a single "*" — but NOT "**", which
# starts bold text. Specs group criteria under bold sub-headings like
# "**Phân quyền**", and a naive `^\s*[-*]` swallows those as list items.
# The required trailing whitespace is what separates "- item" from "**bold**".
BULLET = r"^\s*(?:[-+]|\*(?!\*))\s+"
BULLET_PREFIX = BULLET + r"(?:\[[ xX]\]\s*)?"
BULLET_ITEM = re.compile(BULLET_PREFIX + r"\S")


# ---------------------------------------------------------------- data model


@dataclass
class Line:
    no: int  # 1-indexed
    text: str
    fenced: bool = False  # inside a ``` code block — never spec prose


@dataclass
class Section:
    heading: str
    level: int
    start: int  # 1-indexed line of the heading itself
    lines: list[Line] = field(default_factory=list)

    @property
    def body(self) -> str:
        return "\n".join(ln.text for ln in self.lines)

    @property
    def is_blank(self) -> bool:
        return not self.body.strip()


@dataclass
class Criterion:
    """One acceptance-criteria bullet."""

    no: int  # 1-indexed source line
    raw: str
    section: str

    @property
    def text(self) -> str:
        """Bullet text without the leading `- [ ]` / `- ` marker."""
        return re.sub(BULLET_PREFIX, "", self.raw).strip()

    @property
    def plain(self) -> str:
        """Lowercased, with markdown emphasis and inline code stripped."""
        t = self.text
        t = re.sub(r"`[^`]*`", " ", t)
        t = re.sub(r"\*\*|__|\*|_", "", t)
        return t.lower()

    @property
    def unquoted(self) -> str:
        """`plain` with quoted UI copy removed.

        Specs are full of quoted user-facing strings ("Duyệt nhanh chóng").
        Those are *data*, not spec prose, so vague-word and multi-trigger
        checks must not look inside them or every well-written spec fails.
        """
        t = self.plain
        for a, b in (('"', '"'), ("“", "”"), ("‘", "’"), ("'", "'")):
            t = re.sub(re.escape(a) + r"[^" + re.escape(b) + r"]*" + re.escape(b), " ", t)
        return t

    @property
    def then_clause(self) -> str:
        m = re.search(r"\bthen\b(.*)$", self.plain, re.S)
        return m.group(1) if m else ""


@dataclass
class Document:
    path: Path
    text: str
    frontmatter: dict[str, str]
    sections: list[Section]
    lines: list[Line]

    # ---- classification

    @property
    def doc_type(self) -> str:
        t = (self.frontmatter.get("type") or "").strip().lower()
        if t in {"story", "prd", "spec"}:
            return t
        name = self.path.name.lower()
        if "prd" in name:
            return "prd"
        if re.match(r"^us[-_ ]?\d", name):
            return "story"
        return "unknown"

    # ---- lookup helpers

    def section(self, *keywords: str) -> Section | None:
        """First section whose heading contains any keyword (case-insensitive)."""
        for s in self.sections:
            h = s.heading.lower()
            if any(k.lower() in h for k in keywords):
                return s
        return None

    def sections_matching(self, *keywords: str) -> list[Section]:
        out = []
        for s in self.sections:
            h = s.heading.lower()
            if any(k.lower() in h for k in keywords):
                out.append(s)
        return out

    def has_section(self, *keywords: str) -> bool:
        return self.section(*keywords) is not None

    # ---- story statement

    @property
    def story_statement(self) -> dict[str, str]:
        """Extract As a / I want / so that. Supports VN+EN label variants."""
        out: dict[str, str] = {}
        patterns = {
            "as_a": r"\*\*as an?\*\*\s*(.+)",
            "i_want": r"\*\*i want\*\*\s*(.+)",
            "so_that": r"\*\*so that\*\*\s*(.+)",
        }
        for key, pat in patterns.items():
            m = re.search(pat, self.text, re.I)
            if m:
                out[key] = m.group(1).strip()
        # single-line form: "As a X, I want Y so that Z"
        if not out:
            m = re.search(
                r"\bas an?\b(.+?),?\s*\bi want\b(.+?)\s*\bso that\b(.+)", self.text, re.I | re.S
            )
            if m:
                out = {
                    "as_a": m.group(1).strip(),
                    "i_want": m.group(2).strip(),
                    "so_that": m.group(3).strip(),
                }
        return out

    # ---- acceptance criteria

    AC_HEADINGS = ("acceptance criteria", "acceptance critera", "tiêu chí chấp nhận", " ac", "ac ")

    @property
    def criteria(self) -> list[Criterion]:
        out: list[Criterion] = []
        secs = [s for s in self.sections if self._is_ac_heading(s.heading)]
        for s in secs:
            for ln in s.lines:
                if ln.fenced:
                    continue
                if BULLET_ITEM.match(ln.text):
                    # Skip nested sub-bullets — they elaborate on the criterion
                    # above, they are not criteria themselves. Markdown nests
                    # with 2 spaces, so any indent at all means nested.
                    if len(ln.text) - len(ln.text.lstrip()) >= 2:
                        continue
                    out.append(Criterion(no=ln.no, raw=ln.text, section=s.heading))
        return out

    @classmethod
    def _is_ac_heading(cls, heading: str) -> bool:
        h = heading.lower().strip()
        if "acceptance criteria" in h or "tiêu chí chấp nhận" in h:
            return True
        return h in {"ac", "acs"}

    @property
    def has_ac_section(self) -> bool:
        return any(self._is_ac_heading(s.heading) for s in self.sections)

    # ---- misc

    @property
    def wikilinks(self) -> list[tuple[int, str]]:
        out = []
        for ln in self.lines:
            for m in re.finditer(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", ln.text):
                out.append((ln.no, m.group(1).strip()))
        return out

    @property
    def open_question_lines(self) -> list[Line]:
        return [ln for ln in self.lines if "❓" in ln.text and not ln.fenced]


# ---------------------------------------------------------------- parsing

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_CODE_FENCE = re.compile(r"^\s*(```|~~~)")


def _parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Return (frontmatter, number of lines consumed)."""
    m = _FM_RE.match(text)
    if not m:
        return {}, 0
    block = m.group(1)
    fm: dict[str, str] = {}
    for raw in block.split("\n"):
        if ":" not in raw or raw.lstrip().startswith("#"):
            continue
        k, _, v = raw.partition(":")
        fm[k.strip()] = v.strip().strip("\"'")
    return fm, m.group(0).count("\n")


def parse(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    fm, fm_lines = _parse_frontmatter(text)

    all_lines = text.split("\n")
    lines = [Line(no=i + 1, text=t) for i, t in enumerate(all_lines)]
    body_lines = lines[fm_lines:]

    sections: list[Section] = []
    current = Section(heading="(preamble)", level=0, start=fm_lines + 1)
    in_fence = False

    for ln in body_lines:
        if _CODE_FENCE.match(ln.text):
            in_fence = not in_fence
            ln.fenced = True
            current.lines.append(ln)
            continue
        if in_fence:
            ln.fenced = True
            current.lines.append(ln)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln.text)
        if m:
            sections.append(current)
            current = Section(heading=m.group(2).strip(), level=len(m.group(1)), start=ln.no)
        else:
            current.lines.append(ln)
    sections.append(current)

    return Document(path=path, text=text, frontmatter=fm, sections=sections, lines=lines)


def discover(root: Path, patterns: tuple[str, ...] = ("*.md",)) -> list[Path]:
    """Markdown files under root, skipping dot-dirs and common noise."""
    skip_parts = {".obsidian", ".claudian", ".trash", ".git", "node_modules", ".venv"}
    out: list[Path] = []
    if root.is_file():
        return [root]
    for pat in patterns:
        for p in sorted(root.rglob(pat)):
            if skip_parts & set(p.parts):
                continue
            out.append(p)
    return out
