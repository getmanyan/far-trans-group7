# Phase 5 QA report

## PDF

- File: `Faritova_HW3_Final_Report.pdf`
- Size: 1,871,678 bytes
- Pages: 6 — main paper pages 1–5, references page 6
- Verified by: PDF page-object count, Spotlight page count and Apple Vision OCR of every rendered page.
- Rendered pages: `qa/page-1.png` through `qa/page-6.png`.
- OCR page map:
  - Page 1: title, author line, abstract, Introduction, Related Work.
  - Page 2: Data/temporal protocol, Method, setup.
  - Page 3: D100/DW results, eight-row metrics table, baseline comparisons.
  - Page 4: failure/coverage analysis and C1/C2/HW3 personally verified examples.
  - Page 5: Discussion, limitations, contribution and AI-usage disclosure.
  - Page 6: References.
- Limitation: the CLI model could not visually inspect attached images. All page renders were OCR-checked for content and ordering, but a final human visual glance before upload is recommended.

## Numerical consistency

Ran `verify_submission.py`:

- 8/8 metric rows checked against `outputs/D100_all/metrics.json` and `outputs/DW_all/metrics.json`.
- Primary B−A mean and confidence interval checked against `outputs/analysis_DW.json`.
- Bootstrap seed/draws checked: `20261120` / `10000`.
- Retry recovery counts checked against `results/phase3_summary.json`: 271 recovered, 249 remaining fallback, 480 unique retry prompts.
- C1, C2 and HW3 worksheets all contain personal-verification markers.
- PDF page count checked from PDF bytes.
- Result: all numeric checks passed.

## Tests

All 99 existing tests passed:

- `python3 -m unittest discover -s dilara_hw3/tests -p 'test_*.py'` — 11 tests, OK.
- `python3 -m unittest discover -s dilara_hw2 -p 'test_*.py'` — 30 tests, OK.
- `python3 -m unittest discover -s dilara_hw2/far-trans -p 'test_*.py'` — 58 tests, OK.

## AI-session export

- File: `ai_session/opencode_hw3_session.jsonl`
- Size: 5,803,389 bytes
- Lines: 402 — metadata plus 401 message records.
- Sessions: 4 — main session plus three child exploration sessions.
- Tool calls: 498; tool results: 495.
- Verified all lines parse as JSON.
- Verified no credential/API-token patterns and no local hostname remain.
- Redactions: 14 local committer identities, 13 local hostname occurrences.

## No rerun

No Qwen inference was rerun during report preparation. Frozen protocol, prompt, model outputs and saved metrics were not modified.
