# speclint

A linter for user stories and PRDs.

Code gets linted. Specs do not — yet a vague acceptance criterion costs more than a
vague variable name, because it ships as the wrong feature. `speclint` reads markdown
specs and flags the things a reviewer would catch on a good day and miss on a busy one:
criteria no tester can pass or fail, stories with only a happy path, metrics with no
baseline, open questions nobody owns.

No dependencies. Python 3.10+. Works on English and Vietnamese specs.

```
pip install -e .
speclint docs/specs/
```

## What it looks like

```
story-bad.md  điểm 0/100 · hạng D · 7 vấn đề trên 4 AC
  x lỗi   ST001  Thiếu so that trong câu user story
         story-bad.md:1
         → Dạng chuẩn: **As a** <vai trò cụ thể> / **I want** <năng lực> / **so that** <kết quả>
  x lỗi   AC005  AC dùng từ không kiểm chứng được: "đầy đủ"
         story-bad.md:11
         → Tester không dự họp phải ra cùng kết luận. Thay bằng điều kiện đo được.
  x lỗi   AC002  AC thiếu Then — không nêu kết quả nào để tester đối chiếu
         story-bad.md:12
  ! cảnh  AC006  AC có 2 mệnh đề When — nên tách thành 2 tiêu chí
         story-bad.md:13
         → Một tiêu chí = một trigger. Cần 'and when' nghĩa là đang gộp hai thứ.

Tổng kết
  8 file · 4 sạch · 6 lỗi · 10 cảnh báo · 2 gợi ý
  Điểm trung bình: 72/100
```

Locations print as `file:line`, so they are clickable in a VS Code terminal.
Full sample: [`examples/sample-terminal.txt`](examples/sample-terminal.txt) ·
[`examples/sample-report.md`](examples/sample-report.md).

## Usage

```bash
speclint .                              # lint the current tree
speclint specs/story.md                 # one file
speclint specs/ --format markdown -o report.md
speclint specs/ --format json           # for dashboards
speclint specs/ --min-severity warn     # hide info
speclint specs/ --only AC005,PR002      # one rule at a time while fixing
speclint specs/ --skip AC003,QO001      # mute a rule you disagree with
speclint specs/ --fail-on error         # exit 1 for CI
speclint --list-rules
```

Without an install: `python -m speclint <path>` from the repo root.

A document is linted when its frontmatter says `type: story` or `type: prd`, or when
the filename looks like one (`US-01 ....md`, `... PRD ....md`). Everything else is still
read, so wikilinks pointing at it resolve.

## Rules

| ID | Severity | Applies to | Checks |
| --- | --- | --- | --- |
| `ST001` | error | story | Missing As a / I want / so that |
| `ST002` | warn | story | `so that` merely restates `I want` |
| `ST003` | error | story | No acceptance-criteria section |
| `ST004` | error | story | Acceptance-criteria section is empty |
| `ST005` | info | story | No Definition of Done |
| `AC001` | error | story, prd | Criterion has no Given/When/Then at all |
| `AC002` | error | story, prd | Missing **Then** — nothing to verify |
| `AC003` | warn | story, prd | Missing **When** — implicit trigger |
| `AC004` | info | story, prd | Missing **Given** — no precondition |
| `AC005` | error | story, prd | Unverifiable wording ("properly", "đầy đủ", "as expected") |
| `AC006` | warn | story, prd | More than one `When` — should be split |
| `AC007` | warn | story, prd | Over 70 words — probably several criteria in one |
| `AC008` | warn | story | Failure case with no message and no recovery action |
| `CV001` | warn | story | Happy path only |
| `CV002` | warn | story | No boundary case |
| `QO001` | warn / info | all | Open question with no owner |
| `PR001` | error | prd | No Problem section |
| `PR002` | error | prd | Metric with an empty baseline |
| `PR003` | warn | prd | Metric with no stated source |
| `PR004` | error | prd | Out of scope missing or under two items |
| `PR005` | warn | prd | No counter-metric |
| `PR006` | info | prd | Problem section reads like a solution |
| `LK001` | warn | all | Wikilink resolves to nothing |

`error` is reserved for things that are objectively wrong. Everything heuristic, or
merely a matter of taste, is `warn` or `info`. That split is the whole design.

## Calibration

Rules were tuned against a real 15-document spec set — 14 user stories and a PRD for a
referral campaign engine, 194 acceptance criteria in total.

The first run reported **135 errors across 15 files**. Exactly **one** was real. That
ratio was the bug report: a linter firing on 70% of a competent spec set is not finding
problems, it is the problem.

| | First run | Now |
| --- | ---: | ---: |
| Errors | 135 | 0 |
| Warnings | 72 | 55 |
| Genuine defects among errors | 1 | 1, since fixed |

(The average score is not comparable across the two runs — the scoring formula changed
from a raw count to a density during this work. It currently sits at 85/100.)

Three things were wrong, and each is now a regression test:

**1. A regex ate the sub-headings.** Specs group criteria under bold labels:

```markdown
**Phân quyền và che thông tin**
- [ ] **Given** CS mở hồ sơ **when** ... **then** ...
```

The bullet pattern `^\s*[-*]` matched the first `*` of `**Phân quyền...**` and treated
the heading as a criterion with no Gherkin structure. One character of carelessness,
**85 false positives** — 63% of every error reported. The fix is requiring whitespace
after the marker and excluding `**`.

**2. `error` was doing work `warn` should do.** 49 criteria were written as
`Given ... Then ...` with no `When`. That is a real smell — a tester has to guess
whether the outcome appears on load or on tap — but it is a style issue, not a defect.
At `error` it drowned everything else. It is now `warn`, and missing **Then** (nothing
observable to check) took over as the error.

**3. Vietnamese broke the vocabulary.** The rule for "failure case with no message"
keyed off negative words including `không`. In Vietnamese `không` appears in ordinary
statements — *"CS chỉ có quyền đọc, không sửa được trạng thái"* is a permission rule,
not an error path. The error vocabulary is now narrow (`lỗi`, `timeout`, `từ chối`,
`quá hạn`) and the loose list is kept only for coverage checks, where over-matching
makes the rule quieter rather than noisier.

A fourth issue surfaced while writing the docs: redirecting output to a file crashed on
Windows, because Python falls back to the locale codepage (`cp1252`) when stdout is not
a console, and no Vietnamese character survives that. Output is now forced to UTF-8.

The one real error in that spec set, found on the first run and still found now:

```
x lỗi AC005  AC dùng từ không kiểm chứng được: "bình thường"
      US-08 Ghi nhận event và xét hoàn thành nhiệm vụ.md:42
```

The criterion read *"then vẫn đánh giá bình thường"* — *"then it is evaluated
normally"*. Normally according to whom? It now reads *"then the mission is still
evaluated and rewarded as if the campaign were LIVE"*.

## The score

```
density = Σ severity_weight / max(criteria, sections, 1)      error 4 · warn 2 · info 0.5
score   = 100 − density × 20
```

Density, not a raw count: a 20-criteria spec with three problems is healthier than a
four-criteria spec with three problems. PRDs carry few criteria but many sections, so
the denominator takes whichever is larger — dividing a PRD by its criteria count pinned
every PRD at 0/100 no matter how good it was.

The number is indicative. Use it to watch one document improve across drafts, not to
rank two different documents against each other.

## Design notes

**Quoted text is data, not prose.** A criterion saying
`then hiển thị "Duyệt nhanh chóng"` is precise: it specifies the exact string a user
sees. Vocabulary checks strip quoted spans first, otherwise every spec that pins down
its UI copy — the well-written ones — gets punished for it.

**Nested bullets are not criteria.** An indented bullet elaborates on the criterion
above it. Counting it separately inflates the denominator and invents findings.

**Fenced code is not spec text.** JSON samples and diagrams contain `- [ ]` lines and
`❓` characters that mean nothing to a linter.

**Silence is a feature.** Any rule that cannot be stated precisely is `info`, or is not
written. A linter nobody trusts is a linter nobody runs.

## Tests

```bash
python tests/test_rules.py        # no pytest needed
pytest tests/                     # or with pytest
```

30 tests. Most are regression tests for false positives, because false positives are
what kill a linter.

## Limitations

- Markdown only. Jira and Confluence would need an export step first.
- Gherkin keywords are matched in English (`Given`/`When`/`Then`) even inside
  Vietnamese prose, which matches how Vietnamese teams actually write specs.
- The vocabularies in `rules.py` are tuned for fintech specs in Vietnamese and English.
  Edit `VAGUE`, `ERROR_MARKERS` and `BOUNDARY_MARKERS` for your own house style.
- No auto-fix. Prose problems need a human; a linter that rewrites requirements would
  be worse than the problem.

## Licence

MIT
