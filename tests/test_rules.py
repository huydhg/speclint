"""Tests.

Most of these are regression tests for false positives found by running the
linter against a real 15-document spec set. False positives are the thing that
kills a linter, so they get the most coverage.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speclint.model import parse  # noqa: E402
from speclint.rules import check_links, lint, score  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def run(name: str, **kw):
    return lint(parse(FIXTURES / name), **kw)


def ids(findings):
    return [f.rule for f in findings]


# ------------------------------------------------------------------ parsing


def test_bold_subheading_is_not_a_criterion():
    """`**Nhóm AC**` starts with `*` but is a heading, not a list item.

    A naive `^\\s*[-*]` matched it and produced one AC001 per sub-heading —
    85 false positives across the real spec set.
    """
    doc = parse(FIXTURES / "story-grouped.md")
    texts = [c.text for c in doc.criteria]
    assert len(doc.criteria) == 2, texts
    assert not any(t.startswith("Nhóm") for t in texts)


def test_nested_bullets_are_not_criteria():
    doc = parse(FIXTURES / "story-grouped.md")
    assert all("chi tiết phụ" not in c.text for c in doc.criteria)


def test_frontmatter_and_doc_type():
    doc = parse(FIXTURES / "story-good.md")
    assert doc.frontmatter["type"] == "story"
    assert doc.doc_type == "story"


def test_story_statement_parsed():
    s = parse(FIXTURES / "story-good.md").story_statement
    assert s["as_a"].startswith("borrower")
    assert "so that" not in s["so_that"]


def test_code_fence_contents_ignored_as_headings():
    doc = parse(FIXTURES / "story-grouped.md")
    assert not any(s.heading.startswith("# không phải heading") for s in doc.sections)


# ------------------------------------------------------------------ clean doc


def test_good_story_is_clean():
    assert ids(run("story-good.md")) == []


def test_good_story_scores_full():
    doc = parse(FIXTURES / "story-good.md")
    assert score(lint(doc), len(doc.criteria)) == 100


# ------------------------------------------------------------------ gherkin grading


def test_missing_then_is_error():
    f = [x for x in run("story-bad.md") if x.rule == "AC002"]
    assert f and f[0].severity == "error"


def test_missing_when_is_only_warn():
    """Given/Then is a style smell, not a defect. Severity matters: at `error`
    this rule alone flagged 49 criteria and drowned every real finding."""
    f = [x for x in run("story-grouped.md") if x.rule == "AC003"]
    assert f and all(x.severity == "warn" for x in f)


def test_no_gherkin_at_all_is_error():
    f = [x for x in run("story-bad.md") if x.rule == "AC001"]
    assert f and f[0].severity == "error"


# ------------------------------------------------------------------ vocabulary


def test_vague_word_flagged():
    assert "AC005" in ids(run("story-bad.md"))


def test_vague_word_inside_quotes_is_ignored():
    """Quoted text is UI copy shipped to users, not spec prose. A criterion
    saying `then hiển thị "Duyệt nhanh chóng"` is precise, not vague."""
    assert "AC005" not in ids(run("story-quoted.md"))


def test_vietnamese_khong_is_not_an_error_marker():
    """"không" appears in ordinary statements ("CS không sửa được"), so using
    it to detect error cases misfires constantly."""
    assert "AC008" not in ids(run("story-permission.md"))


def test_real_error_case_without_message_is_flagged():
    assert "AC008" in ids(run("story-bad.md"))


def test_multiple_when_flagged():
    assert "AC006" in ids(run("story-bad.md"))


def test_when_inside_quotes_does_not_count_as_second_trigger():
    assert "AC006" not in ids(run("story-quoted.md"))


# ------------------------------------------------------------------ coverage


def test_happy_path_only_flagged():
    assert "CV001" in ids(run("story-happy-only.md"))


def test_boundary_missing_flagged():
    assert "CV002" in ids(run("story-happy-only.md"))


# ------------------------------------------------------------------ open questions


def test_open_question_without_owner_in_section_is_warn():
    f = [x for x in run("prd-bad.md") if x.rule == "QO001"]
    assert f and any(x.severity == "warn" for x in f)


def test_open_question_with_owner_is_clean():
    assert "QO001" not in ids(run("prd-good.md"))


def test_resolved_open_question_ignored():
    f = [x for x in run("prd-good.md") if x.rule == "QO001"]
    assert not f


# ------------------------------------------------------------------ PRD


def test_metric_without_baseline_is_error():
    f = [x for x in run("prd-bad.md") if x.rule == "PR002"]
    assert f and f[0].severity == "error"


def test_metric_with_question_mark_baseline_is_accepted():
    """`❓ cần số` is an honest gap, not a missing baseline."""
    assert "PR002" not in ids(run("prd-good.md"))


def test_thin_out_of_scope_flagged():
    assert "PR004" in ids(run("prd-bad.md"))


def test_missing_counter_metric_flagged():
    assert "PR005" in ids(run("prd-bad.md"))


def test_good_prd_is_clean():
    assert ids(run("prd-good.md")) == []


# ------------------------------------------------------------------ links


def test_broken_wikilink_flagged():
    doc = parse(FIXTURES / "story-grouped.md")
    out = check_links(doc, known={"story-good"})
    assert [f.rule for f in out] == ["LK001"]


def test_known_wikilink_ok():
    doc = parse(FIXTURES / "story-grouped.md")
    assert check_links(doc, known={"story-good", "khong-ton-tai"}) == []


# ------------------------------------------------------------------ filters


def test_only_filter():
    assert set(ids(run("story-bad.md", only={"AC005"}))) <= {"AC005"}


def test_skip_filter():
    assert "AC005" not in ids(run("story-bad.md", skip={"AC005"}))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {fn.__name__}: {e}")
        except Exception as e:  # pragma: no cover
            failed += 1
            print(f"  ERR  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
