# Report Continuity Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Feed the previous 2 daily reports into report generation so new reports build on prior context instead of re-reporting the same news articles and background each day.

**Architecture:** A new `load_recent_reports()` helper in `main.py` reads the last 2 dated report files from `reports/` (excluding today) and passes them, verbatim, into `generate_report()`. They are injected into the **user message** — never the system prompt — so prompt caching still fires. A static continuity rule is added to the generator's system prompt. The fact-checker is NOT given the prior reports, but gets a static system-prompt note making it aware that continuity references (e.g. "unchanged from yesterday") may appear and should not be auto-disputed merely for being absent from the data bundle.

**Tech Stack:** Python 3, `anthropic` SDK, `pytest` with `unittest.mock` (all tests mock the API — no real calls).

---

## File Structure

- `src/main.py` — add `load_recent_reports()`; wire it into `run_pipeline()`.
- `src/report_generator.py` — `generate_report()` gains a `recent_reports` parameter; injects prior reports into the user message; adds a static continuity rule to the system prompt.
- `src/fact_checker.py` — add a static awareness note to the system prompt.
- `tests/test_main.py` — tests for `load_recent_reports()` and the pipeline wiring.
- `tests/test_report_generator.py` — tests for the new parameter and injection.
- `tests/test_fact_checker.py` — test for the awareness note.

### Key design constraints (from CLAUDE.md)
- **Prompt caching:** the system prompt must be byte-identical across runs. Prior reports are per-run data → they go in the **user message only**. The continuity rule and the fact-checker note are static instruction text → safe to add to system prompts.
- **Graceful degradation:** on cold start (no prior reports, or `reports/` missing), `load_recent_reports()` returns `[]` and generation proceeds normally.

---

## Task 1: `load_recent_reports()` helper in main.py

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_main.py`:

```python
def test_load_recent_reports_returns_empty_when_dir_missing(tmp_path):
    from main import load_recent_reports
    result = load_recent_reports(reports_dir=str(tmp_path / "nope"), n=2)
    assert result == []


def test_load_recent_reports_returns_last_n_oldest_first(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    for d in ["2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29"]:
        (reports / f"{d}.md").write_text(f"report {d}", encoding="utf-8")
    result = load_recent_reports(reports_dir=str(reports), n=2)
    assert [r["date"] for r in result] == ["2026-05-28", "2026-05-29"]
    assert result[1]["content"] == "report 2026-05-29"


def test_load_recent_reports_excludes_before_date(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    for d in ["2026-05-28", "2026-05-29", "2026-05-30"]:
        (reports / f"{d}.md").write_text(f"report {d}", encoding="utf-8")
    result = load_recent_reports(reports_dir=str(reports), n=2, before_date="2026-05-30")
    assert [r["date"] for r in result] == ["2026-05-28", "2026-05-29"]


def test_load_recent_reports_ignores_non_dated_files(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "README.md").write_text("readme", encoding="utf-8")
    (reports / "2026-05-29.md").write_text("report", encoding="utf-8")
    result = load_recent_reports(reports_dir=str(reports), n=2)
    assert [r["date"] for r in result] == ["2026-05-29"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_main.py -k load_recent_reports -v`
Expected: FAIL with `ImportError: cannot import name 'load_recent_reports'`

- [ ] **Step 3: Implement the helper**

In `src/main.py`, add `import re` near the top imports, and add this function above `assemble_bundle`:

```python
DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


def load_recent_reports(reports_dir: str = "reports", n: int = 2, before_date: str = None) -> list[dict]:
    """Load up to n most recent prior report files, oldest first.

    Report files are named YYYY-MM-DD.md. Files matching before_date (today)
    are excluded so a same-day re-run never feeds a report its own output.
    Returns a list of {"date": str, "content": str}, or [] if the directory
    is missing or holds no dated reports (graceful degradation on cold start).
    """
    dir_path = Path(reports_dir)
    if not dir_path.is_dir():
        return []
    dated = []
    for f in dir_path.iterdir():
        m = DATE_FILE_RE.match(f.name)
        if not m:
            continue
        if before_date is not None and m.group(1) == before_date:
            continue
        dated.append((m.group(1), f))
    dated.sort(key=lambda x: x[0])
    recent = dated[-n:]
    return [{"date": d, "content": f.read_text(encoding="utf-8")} for d, f in recent]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -k load_recent_reports -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add load_recent_reports helper for report continuity"
```

---

## Task 2: `generate_report` injects recent reports + continuity rule

**Files:**
- Modify: `src/report_generator.py`
- Test: `tests/test_report_generator.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_report_generator.py`:

```python
SAMPLE_RECENT = [
    {"date": "2026-04-14", "content": "# REPORT 04-14\nBrent unchanged."},
    {"date": "2026-04-15", "content": "# REPORT 04-15\nGold rallied."},
]


def test_generate_report_injects_recent_reports_into_user_message():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE, recent_reports=SAMPLE_RECENT)
    user_content = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "REPORT 04-14" in user_content
    assert "REPORT 04-15" in user_content


def test_generate_report_recent_reports_not_in_system_prompt():
    """Prior reports are per-run data — they must stay out of the cached system prompt."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE, recent_reports=SAMPLE_RECENT)
    system_text = mock_client.messages.create.call_args[1]["system"][0]["text"]
    assert "REPORT 04-14" not in system_text
    assert "Gold rallied" not in system_text


def test_generate_report_works_without_recent_reports():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            result = generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    assert isinstance(result, str)
    user_content = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "No previous reports" in user_content


def test_generate_report_system_prompt_has_continuity_rule():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    system_text = mock_client.messages.create.call_args[1]["system"][0]["text"]
    assert "continuity" in system_text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_report_generator.py -v`
Expected: FAIL — the new tests fail (`generate_report() got an unexpected keyword argument 'recent_reports'` and missing assertions).

- [ ] **Step 3: Update the signature, system prompt, and user message**

In `src/report_generator.py`, change the function signature:

```python
def generate_report(data_bundle: dict, template: str, recent_reports: list[dict] = None) -> str:
```

Add this bullet to the end of the `Critical rules:` list in `system_prompt` (before the closing `"""`):

```
- You may be given the previous reports as continuity context in the user message. Do NOT re-report the same news articles or restate unchanged background. When a level or bias is unchanged, say so briefly (e.g. "unchanged from prior session") and focus each section on what is NEW or has CHANGED since those reports.
```

Immediately before the `user_content = ...` assignment, build the prior-reports block:

```python
    recent_reports = recent_reports or []
    if recent_reports:
        prior_block = "\n\n".join(
            f"=== PREVIOUS REPORT ({r['date']}) ===\n{r['content']}"
            for r in recent_reports
        )
    else:
        prior_block = "(No previous reports available — this is the first report or earlier reports are missing.)"
```

Then update `user_content` to include the block:

```python
    user_content = f"""Generate today's macro report using this data bundle:

{json.dumps(data_bundle, indent=2, default=str)}

Today's date: {date_str}
Report time: {time_str} UTC

In the report header, replace {{DATE}} with {date_str} and {{TIME}} with {time_str}.

PREVIOUS REPORTS (most recent last) — continuity context. Do NOT repeat the same
news articles, background, or framing already covered below. Lead with what is new
or changed since these reports:
{prior_block}
"""
```

- [ ] **Step 4: Run the full generator test file**

Run: `python -m pytest tests/test_report_generator.py -v`
Expected: PASS (all tests, including the pre-existing caching/date tests, pass)

- [ ] **Step 5: Commit**

```bash
git add src/report_generator.py tests/test_report_generator.py
git commit -m "feat: feed previous reports into generate_report as continuity context"
```

---

## Task 3: Wire `load_recent_reports` into `run_pipeline`

**Files:**
- Modify: `src/main.py:42-44`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_main.py`:

```python
def test_run_pipeline_passes_recent_reports_to_generator(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "2026-01-01.md").write_text("old report", encoding="utf-8")
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "report_template.md").write_text("# Template")

    with patch("main.fetch_prices", return_value={"equities": {}, "fx": {}, "crypto": {}, "commodities": {}}), \
         patch("main.fetch_macro", return_value={}), \
         patch("main.fetch_news", return_value=[]), \
         patch("main.generate_report", return_value="# MACRO REPORT\n\nContent") as mock_gen, \
         patch("main.fact_check", return_value="# MACRO REPORT\n\nContent\n\n---\n\n## FACT-CHECK"):

        run_pipeline()

    recent = mock_gen.call_args[1]["recent_reports"]
    assert [r["date"] for r in recent] == ["2026-01-01"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -k passes_recent_reports -v`
Expected: FAIL with `KeyError: 'recent_reports'` (generate_report is called without the kwarg).

- [ ] **Step 3: Update `run_pipeline`**

In `src/main.py`, replace the `[5/6]` block:

```python
    print("[5/6] Generating report...")
    template = Path("templates/report_template.md").read_text(encoding="utf-8")
    report = generate_report(bundle, template)
```

with:

```python
    print("[5/6] Generating report...")
    template = Path("templates/report_template.md").read_text(encoding="utf-8")
    recent_reports = load_recent_reports(n=2, before_date=bundle["date"])
    report = generate_report(bundle, template, recent_reports=recent_reports)
```

- [ ] **Step 4: Run the full main test file**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS (all tests, including the pre-existing `test_run_pipeline_saves_file`, pass)

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: wire recent-report context into the pipeline"
```

---

## Task 4: Fact-checker awareness note

**Files:**
- Modify: `src/fact_checker.py`
- Test: `tests/test_fact_checker.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_fact_checker.py` (match the existing mock/env patterns in that file — patch `fact_checker.anthropic.Anthropic` and set `ANTHROPIC_API_KEY`):

```python
def test_fact_check_system_prompt_notes_continuity_context():
    """Fact-checker must know the generator saw prior reports, so continuity
    references aren't auto-disputed for being absent from the data bundle."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="## FACT-CHECK & INSIGHTS")]
    )
    with patch("fact_checker.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            fact_check("# REPORT", {"date": "2026-04-16", "prices": {}, "macro": {}, "news": []})
    system_text = mock_client.messages.create.call_args[1]["system"][0]["text"]
    lowered = system_text.lower()
    assert "previous report" in lowered or "prior report" in lowered
    assert "continuity" in lowered
```

If `tests/test_fact_checker.py` lacks the imports, add at the top:

```python
import os
from unittest.mock import patch, MagicMock
from fact_checker import fact_check
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fact_checker.py -k continuity -v`
Expected: FAIL — assertion error (the system prompt has no continuity note yet).

- [ ] **Step 3: Add the awareness note to the system prompt**

In `src/fact_checker.py`, add this paragraph to the end of the `Rules:` section in `system_prompt` (before the closing `"""`):

```
Continuity context: the report's author was given the previous reports as
continuity context, so the report may reference prior sessions (e.g. "unchanged
from yesterday", "as noted previously"). Those prior reports are NOT in your data
bundle. Do not list such a statement as Disputed solely because the comparison
value is absent from the bundle — only dispute claims about TODAY'S data that
conflict with, or are unsupported by, the bundle.
```

- [ ] **Step 4: Run the full fact-checker test file**

Run: `python -m pytest tests/test_fact_checker.py -v`
Expected: PASS (all tests pass)

- [ ] **Step 5: Commit**

```bash
git add src/fact_checker.py tests/test_fact_checker.py
git commit -m "feat: make fact-checker aware of report continuity context"
```

---

## Task 5: Full suite regression check

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest tests/ -v`
Expected: PASS — the original 39 tests plus the new ones (10 added: 4 in Task 1, 4 in Task 2, 1 in Task 3, 1 in Task 4), all green.

- [ ] **Step 2: Sanity-check the generated user message manually (optional)**

If `ANTHROPIC_API_KEY`, `FRED_API_KEY`, `TAVILY_API_KEY` are set locally, run a real pipeline pass and confirm the new report references prior context and does not re-list yesterday's news verbatim:

Run: `python -m pytest tests/ -q` first, then `PYTHONPATH=src python src/main.py`
Expected: a new `reports/<today>.md` whose narrative contrasts against the prior 2 days rather than restating them.

- [ ] **Step 3: Commit (only if any cleanup was needed)**

```bash
git add -A
git commit -m "test: full-suite regression check for report continuity"
```

---

## Self-Review Notes

- **Spec coverage:** N=2 (Task 1 `n=2`, Task 3 call) ✓; verbatim prior reports (Task 2 injects `r['content']` unchanged) ✓; "don't reiterate same news articles" (continuity rule in Task 2 system prompt + user-message instruction) ✓; fact-checker NOT fed reports but made aware via system prompt (Task 4) ✓; graceful cold-start (Task 1 returns `[]`, Task 2 emits "No previous reports") ✓.
- **Caching preserved:** prior reports go only in the user message (Task 2 test `test_generate_report_recent_reports_not_in_system_prompt`); the pre-existing `{DATE}` caching tests remain unmodified and must still pass.
- **Type consistency:** `load_recent_reports` returns `list[{"date": str, "content": str}]`; `generate_report(recent_reports=...)` consumes `r['date']` / `r['content']`; `run_pipeline` passes the same list. Consistent across Tasks 1–3.
