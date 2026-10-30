"""Rules.

Design principle: a linter that cries wolf gets switched off. So:

* `error` is reserved for things that are objectively wrong — a criterion with
  no observable outcome, a metric with no baseline.
* Anything heuristic, or merely a style preference, is `warn` or `info`.
* Vietnamese needs care. "không" appears in almost every sentence, so it is
  useless as an error signal; only strong markers ("lỗi", "timeout", "từ chối")
  count. Quoted UI copy is data, not spec prose, and is excluded from
  vocabulary checks.

Calibrated against a real 15-document spec set; see README for the before/after.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .model import BULLET, Criterion, Document

SEVERITIES = ("error", "warn", "info")
WEIGHTS = {"error": 4.0, "warn": 2.0, "info": 0.5}


@dataclass
class Finding:
    rule: str
    severity: str
    line: int
    message: str
    hint: str = ""
    path: Path | None = None


@dataclass
class Rule:
    id: str
    severity: str
    applies_to: tuple[str, ...]  # doc types; ("*",) for all
    title: str
    check: Callable[[Document], Iterable[Finding]]


RULES: list[Rule] = []


def rule(id: str, severity: str, applies_to: tuple[str, ...], title: str):
    def deco(fn):
        RULES.append(Rule(id=id, severity=severity, applies_to=applies_to, title=title, check=fn))
        return fn

    return deco


def _f(rule_id, severity, line, message, hint="") -> Finding:
    return Finding(rule=rule_id, severity=severity, line=line, message=message, hint=hint)


# ---------------------------------------------------------------- vocabularies

# Words that make a criterion unverifiable. Checked only inside acceptance
# criteria, and only outside quoted strings.
VAGUE = [
    "properly", "appropriately", "as expected", "user-friendly", "user friendly",
    "works correctly", "work correctly", "handles errors", "handle errors",
    "seamless", "intuitive", "robust", "optimal", "and so on",
    "đầy đủ", "hợp lý", "phù hợp", "bình thường", "như mong đợi", "thân thiện",
    "tối ưu", "mượt mà", "ổn định", "dễ dàng", "nhanh chóng", "linh hoạt",
    "đúng đắn", "thích hợp",
]
VAGUE_PATTERNS = [r"\betc\b", r"\bv\.v\b", r"\bvv\b"]

# Loose — used only for *coverage* (does the story have ANY negative case?).
# Over-matching here is safe: it makes the rule quieter, not noisier.
NEGATIVE_MARKERS = [
    "không", "bị ", "lỗi", "thất bại", "từ chối", "disabled", "vô hiệu", "chặn",
    "hết hạn", "quá hạn", "sai", "fail", "error", "invalid", "reject", "trống",
    "rỗng", "timeout", "mất mạng", "mất kết nối", "chưa đủ", "vượt", "khoá",
]

# Tight — used to decide "this criterion describes a failure". Must not include
# bare "không"/"bị"/"sai": in Vietnamese they appear in ordinary statements such
# as "CS chỉ có quyền đọc, không sửa được" (a permission rule, not an error).
ERROR_MARKERS = [
    "lỗi", "thất bại", "từ chối", "không hợp lệ", "không đúng", "không tồn tại",
    "hết hạn", "quá hạn", "timeout", "mất mạng", "mất kết nối", "vượt quá",
    "bị chặn", "bị khoá", "bị từ chối", "fail", "error", "invalid", "reject",
    "5xx", "4xx",
]

BOUNDARY_MARKERS = [
    "boundary", "biên", "tối đa", "tối thiểu", "exactly", "đúng bằng",
    "≥", "≤", ">=", "<=", "giới hạn", "max", "min", "hết lượt",
]

# "đúng 5 lượt", "hết 5 lượt", "0/5", "exactly 3" — all state a limit without
# using any of the words above.
BOUNDARY_PATTERNS = [
    r"\bđúng\s+\d",
    r"\bhết\s+\d",
    r"\bexactly\s+\d",
    r"\d+\s*/\s*\d+",
    r"(≥|≤|>=|<=|>|<)\s*\d",
]

RECOVERY_MARKERS = [
    "hiển thị", "thông báo", "hiện", "nút", "hướng dẫn", "message", "toast",
    "báo lỗi", "cho phép", "thử lại", "quay lại", "chuyển", "ghi log", "gửi",
    "trả về", "show", "display", "retry", "chờ",
]

SOLUTION_WORDS = [
    "thêm nút", "xây dựng", "tính năng mới", "màn hình mới", "api mới",
    "nút bấm", "popup",
]


def _contains_any(text: str, words: Iterable[str]) -> str | None:
    for w in words:
        if w in text:
            return w
    return None


def _ac_corpus(doc: Document) -> str:
    return " ".join(c.plain for c in doc.criteria)


def _gherkin_parts(c: Criterion) -> list[str]:
    p = c.plain
    return [k for k in ("given", "when", "then") if re.search(rf"\b{k}\b", p)]


# ---------------------------------------------------------------- story shape


@rule("ST001", "error", ("story",), "Thiếu câu user story")
def st001(doc):
    s = doc.story_statement
    missing = [k for k in ("as_a", "i_want", "so_that") if not s.get(k)]
    if missing:
        label = {"as_a": "As a", "i_want": "I want", "so_that": "so that"}
        yield _f(
            "ST001", "error", 1,
            "Thiếu " + ", ".join(label[m] for m in missing) + " trong câu user story",
            "Dạng chuẩn: **As a** <vai trò cụ thể> / **I want** <năng lực> / **so that** <kết quả>",
        )


@rule("ST002", "warn", ("story",), "`so that` chỉ nhắc lại `I want`")
def st002(doc):
    s = doc.story_statement
    want, so = s.get("i_want"), s.get("so_that")
    if not want or not so:
        return

    def toks(t):
        t = re.sub(r"[^\w\sÀ-ỹ]", " ", t.lower())
        return {w for w in t.split() if len(w) > 2}

    a, b = toks(want), toks(so)
    if not a or not b:
        return
    overlap = len(a & b) / min(len(a), len(b))
    if overlap >= 0.6:
        yield _f(
            "ST002", "warn", 1,
            f"`so that` trùng {overlap:.0%} từ với `I want` — có thể chỉ đang diễn đạt lại",
            "`so that` phải nói kết quả người dùng nhận được, không lặp lại mong muốn",
        )


@rule("ST003", "error", ("story",), "Không có mục Acceptance criteria")
def st003(doc):
    if not doc.has_ac_section:
        yield _f("ST003", "error", 1, "Story không có mục Acceptance criteria")


@rule("ST004", "error", ("story",), "Mục Acceptance criteria rỗng")
def st004(doc):
    if doc.has_ac_section and not doc.criteria:
        sec = next(s for s in doc.sections if Document._is_ac_heading(s.heading))
        yield _f("ST004", "error", sec.start, "Mục Acceptance criteria không có tiêu chí nào")


@rule("ST005", "info", ("story",), "Thiếu Definition of Done")
def st005(doc):
    if doc.criteria and not doc.has_section("definition of done", "dod"):
        yield _f("ST005", "info", 1, "Story không có Definition of Done")


# ---------------------------------------------------------------- criterion shape
#
# Graded deliberately. Missing Then is a real defect: nothing to verify.
# Missing When is a style smell, common and often harmless for state-display
# criteria, so it only warns.


@rule("AC001", "error", ("story", "prd"), "AC không theo cấu trúc Given/When/Then")
def ac001(doc):
    for c in doc.criteria:
        if not _gherkin_parts(c):
            yield _f(
                "AC001", "error", c.no,
                "AC không theo cấu trúc Given/When/Then",
                "Given <trạng thái trước> / When <một hành động> / Then <kết quả quan sát được>",
            )


@rule("AC002", "error", ("story", "prd"), "AC thiếu Then — không có kết quả để kiểm tra")
def ac002(doc):
    for c in doc.criteria:
        parts = _gherkin_parts(c)
        if parts and "then" not in parts:
            yield _f(
                "AC002", "error", c.no,
                "AC thiếu Then — không nêu kết quả nào để tester đối chiếu",
            )


@rule("AC003", "warn", ("story", "prd"), "AC thiếu When — trigger ngầm định")
def ac003(doc):
    for c in doc.criteria:
        parts = _gherkin_parts(c)
        if "then" in parts and "when" not in parts:
            yield _f(
                "AC003", "warn", c.no,
                "AC có Then nhưng không có When — chưa rõ điều gì kích hoạt",
                "Tester phải đoán: lúc mở màn hình? lúc bấm nút? Nêu rõ trigger.",
            )


@rule("AC004", "info", ("story", "prd"), "AC thiếu Given — không nêu tiền đề")
def ac004(doc):
    for c in doc.criteria:
        parts = _gherkin_parts(c)
        if "then" in parts and "given" not in parts:
            yield _f("AC004", "info", c.no, "AC không nêu trạng thái tiền đề (Given)")


# ---------------------------------------------------------------- criterion quality


@rule("AC005", "error", ("story", "prd"), "AC chứa từ không kiểm chứng được")
def ac005(doc):
    for c in doc.criteria:
        t = c.unquoted
        hit = _contains_any(t, VAGUE)
        if not hit:
            for pat in VAGUE_PATTERNS:
                m = re.search(pat, t)
                if m:
                    hit = m.group(0)
                    break
        if hit:
            yield _f(
                "AC005", "error", c.no,
                f'AC dùng từ không kiểm chứng được: "{hit}"',
                "Tester không dự họp phải ra cùng kết luận. Thay bằng điều kiện đo được.",
            )


@rule("AC006", "warn", ("story", "prd"), "AC có nhiều hơn một trigger")
def ac006(doc):
    for c in doc.criteria:
        n = len(re.findall(r"\bwhen\b", c.unquoted))
        if n > 1:
            yield _f(
                "AC006", "warn", c.no,
                f"AC có {n} mệnh đề When — nên tách thành {n} tiêu chí",
                "Một tiêu chí = một trigger. Cần 'and when' nghĩa là đang gộp hai thứ.",
            )


@rule("AC007", "warn", ("story", "prd"), "AC quá dài")
def ac007(doc):
    LIMIT = 70
    for c in doc.criteria:
        n = len(c.text.split())
        if n > LIMIT:
            yield _f(
                "AC007", "warn", c.no,
                f"AC dài {n} từ (ngưỡng {LIMIT}) — có thể đang gộp nhiều tiêu chí",
            )


@rule("AC008", "warn", ("story",), "AC lỗi nhưng không nói người dùng thấy gì")
def ac008(doc):
    for c in doc.criteria:
        then = c.then_clause
        if not then:
            continue
        if not _contains_any(c.unquoted, ERROR_MARKERS):
            continue
        if re.search(r"[\"“‘]", c.text):  # có thông điệp trích dẫn
            continue
        if _contains_any(then, RECOVERY_MARKERS):
            continue
        yield _f(
            "AC008", "warn", c.no,
            "AC mô tả trường hợp lỗi nhưng không nêu thông điệp hoặc hành động tiếp theo",
            'Nêu rõ người dùng thấy gì và làm gì tiếp: then hiển thị "..." và nút Thử lại',
        )


# ---------------------------------------------------------------- coverage


@rule("CV001", "warn", ("story",), "Không có negative path")
def cv001(doc):
    if not doc.criteria:
        return
    if not _contains_any(_ac_corpus(doc), NEGATIVE_MARKERS):
        yield _f(
            "CV001", "warn", doc.criteria[0].no,
            "Chỉ có happy path — không thấy tiêu chí nào cho trường hợp bị chặn hoặc lỗi",
            "Thêm ít nhất một AC: điều kiện không thoả, và người dùng được báo gì",
        )


@rule("CV002", "warn", ("story",), "Không có boundary case")
def cv002(doc):
    if not doc.criteria:
        return
    corpus = _ac_corpus(doc)
    if _contains_any(corpus, BOUNDARY_MARKERS):
        return
    if any(re.search(p, corpus) for p in BOUNDARY_PATTERNS):
        return
    yield _f(
        "CV002", "warn", doc.criteria[0].no,
        "Không thấy tiêu chí nào chạm giá trị biên",
        "Giới hạn là chỗ hay vỡ nhất: đúng 5 chứ không phải 4 hay 6, danh sách rỗng, độ dài tối đa",
    )


# ---------------------------------------------------------------- open questions


def _in_open_questions(doc: Document, line_no: int) -> bool:
    for s in doc.sections:
        if "open question" in s.heading.lower() or "câu hỏi mở" in s.heading.lower():
            if s.lines and s.lines[0].no <= line_no <= s.lines[-1].no:
                return True
    return False


@rule("QO001", "warn", ("*",), "Open question không có người chịu trách nhiệm")
def qo001(doc):
    for ln in doc.open_question_lines:
        t = ln.text
        if re.match(BULLET + r"\[[xX]\]", t):  # đã chốt
            continue
        if "@" in t:
            continue
        if not re.match(BULLET, t):
            continue
        # Trong mục Open questions thì bắt buộc có owner.
        # Rải rác trong Notes thì chỉ là ghi chú — nhắc nhẹ thôi.
        if _in_open_questions(doc, ln.no):
            yield _f(
                "QO001", "warn", ln.no,
                "Câu hỏi mở không ghi ai trả lời được",
                "Thêm @Team hoặc @Tên, kèm việc nó đang chặn gì",
            )
        else:
            yield _f(
                "QO001", "info", ln.no,
                "Ghi chú ❓ chưa có người theo",
                "Nếu đây là câu hỏi thật, chuyển vào mục Open questions kèm @owner",
            )


# ---------------------------------------------------------------- PRD


@rule("PR001", "error", ("prd",), "PRD thiếu mục Problem")
def pr001(doc):
    if not doc.has_section("problem", "vấn đề"):
        yield _f("PR001", "error", 1, "PRD không có mục Problem")


@rule("PR002", "error", ("prd",), "Metric thiếu baseline")
def pr002(doc):
    sec = doc.section("metric", "goals", "mục tiêu")
    if not sec:
        return
    for ln in sec.lines:
        t = ln.text.strip()
        if not t.startswith("|") or "---" in t:
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"metric", "chỉ số", "", "chỉ tiêu"}:
            continue
        if not cells[1] or cells[1] in {"-", "—"}:
            yield _f(
                "PR002", "error", ln.no,
                f'Metric "{cells[0][:40]}" có baseline rỗng',
                "Không baseline thì sau khi launch không chứng minh được thành công hay thất bại. "
                "Chưa có số thì ghi ❓ và đưa vào Open questions.",
            )


@rule("PR003", "warn", ("prd",), "Metric không ghi nguồn số")
def pr003(doc):
    sec = doc.section("metric", "goals", "mục tiêu")
    if not sec:
        return
    for ln in sec.lines:
        t = ln.text.strip()
        if not t.startswith("|") or "---" in t:
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if len(cells) < 3:
            continue
        name = cells[0]
        if name.lower() in {"metric", "chỉ số", "", "chỉ tiêu"}:
            continue
        if not re.search(r"[(*].+[)*]|`.+`", name):
            yield _f(
                "PR003", "warn", ln.no,
                f'Metric "{name[:40]}" không ghi lấy số từ đâu',
                "Ghi nguồn ngay trong ô: *(DB: bảng.cột)*, *(Amplitude: tên event)*",
            )


@rule("PR004", "error", ("prd",), "Out of scope quá mỏng")
def pr004(doc):
    sec = doc.section("scope", "phạm vi")
    if not sec:
        yield _f("PR004", "error", 1, "PRD không có mục Scope")
        return
    m = re.search(r"\*\*out of scope\*\*(.*?)(?=\n\*\*|\Z)", sec.body, re.S | re.I)
    if not m:
        yield _f("PR004", "error", sec.start, "Mục Scope không có phần Out of scope")
        return
    items = [l for l in m.group(1).split("\n") if re.match(BULLET + r"\S", l)]
    if len(items) < 2:
        yield _f(
            "PR004", "error", sec.start,
            f"Out of scope chỉ có {len(items)} mục",
            "Phạm vi được định nghĩa bằng thứ bị loại ra. Liệt kê ít nhất 2 thứ stakeholder "
            "dễ mặc định là có nhưng thực ra không làm.",
        )


@rule("PR005", "warn", ("prd",), "Không có counter-metric")
def pr005(doc):
    sec = doc.section("metric", "goals", "mục tiêu")
    if not sec:
        return
    if not re.search(r"counter[- ]metric|chỉ số đối trọng|⚠", sec.body, re.I):
        yield _f(
            "PR005", "warn", sec.start,
            "Không khai báo counter-metric",
            "Thứ gì có thể xấu đi khi chỉ số chính đẹp lên? Không có nó thì mọi kết quả đều là thắng lợi.",
        )


@rule("PR006", "info", ("prd",), "Mục Problem có vẻ đang mô tả giải pháp")
def pr006(doc):
    sec = doc.section("problem", "vấn đề")
    if not sec:
        return
    hit = _contains_any(sec.body.lower(), SOLUTION_WORDS)
    if hit:
        yield _f(
            "PR006", "info", sec.start,
            f'Mục Problem có cụm "{hit}" — kiểm tra xem đang tả vấn đề hay đã nhảy sang giải pháp',
        )


# ---------------------------------------------------------------- links


def check_links(doc: Document, known: set[str]) -> list[Finding]:
    out = []
    for no, target in doc.wikilinks:
        stem = target.split("/")[-1].strip()
        if stem.lower() in known or target.strip().lower() in known:
            continue
        out.append(
            _f("LK001", "warn", no, f'Wikilink "{target}" không trỏ tới file nào trong phạm vi quét')
        )
    return out


# ---------------------------------------------------------------- runner


def applicable(rule: Rule, doc_type: str) -> bool:
    return "*" in rule.applies_to or doc_type in rule.applies_to


def lint(doc: Document, only: set[str] | None = None, skip: set[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    dt = doc.doc_type
    for r in RULES:
        if only and r.id not in only:
            continue
        if skip and r.id in skip:
            continue
        if not applicable(r, dt):
            continue
        for f in r.check(doc):
            f.path = doc.path
            findings.append(f)
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


def score(findings: list[Finding], n_units: int = 1) -> int:
    """Heuristic 0-100, by *density* not raw count.

    A 20-criteria spec with 3 problems is healthier than a 4-criteria spec with
    3 problems, so penalty is divided by the number of criteria. Indicative
    only — use it to compare drafts of the same document over time, not to
    rank two different documents against each other.
    """
    penalty = sum(WEIGHTS.get(f.severity, 1.0) for f in findings)
    density = penalty / max(n_units, 1)
    return max(0, round(100 - density * 20))


def grade(s: int) -> str:
    return "A" if s >= 90 else "B" if s >= 75 else "C" if s >= 55 else "D"


@dataclass
class FileResult:
    path: Path
    findings: list[Finding]
    n_criteria: int
    n_sections: int = 0

    @property
    def n_units(self) -> int:
        """Denominator for the density score.

        Stories are measured per acceptance criterion. PRDs often carry very
        few criteria but many sections, and dividing those by `n_criteria`
        buried every PRD at 0/100 regardless of how good it was. Taking the
        larger of the two keeps both document shapes on a comparable scale.
        """
        return max(self.n_criteria, self.n_sections, 1)

    @property
    def score(self) -> int:
        return score(self.findings, self.n_units)

    @property
    def grade(self) -> str:
        return grade(self.score)

    @property
    def clean(self) -> bool:
        return not self.findings
