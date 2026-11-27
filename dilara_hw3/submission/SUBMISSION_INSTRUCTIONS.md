# Homework 3 submission package

## Upload these files

- `submission/Faritova_HW3_Final_Report.pdf`
- `submission/ai_session/opencode_hw3_session.jsonl`
- `submission/ai_session/README.md`
- `submission/ai_session/redaction_report.txt`

Supporting reproducibility files in the repository:

- `submission/paper_source.md`
- `submission/build_report_pdf.py`
- `submission/export_ai_session.py`
- `submission/verify_submission.py`
- `submission/qa/qa_report.md`
- `submission/qa/page-1.png` through `page-6.png`

## Checklist

- [x] PDF report is in English.
- [x] Main paper is 5 pages; references are on page 6, giving 6 PDF pages total.
- [x] Required sections present: title, abstract, introduction, related work, method, experiments/results, discussion, AI-usage disclosure, references.
- [x] All eight evaluated methods are in the results table: Popularity, CBF, Latest buy, Latest buy or sell, Original-text CBF, All-fallback structured, A Structured Encoder, B Structured + retry.
- [x] Metrics are shown to four decimals; primary difference and bootstrap interval are shown to seven decimals in the text.
- [x] D100 replay and DW development evaluation are reported; official final evaluation is explicitly not claimed.
- [x] Model version, revision, hardware, precision, decoding, seeds and runtime are reported.
- [x] Code locations are reported: `run_hw3.py`, `retry_encoder.py`, `retry_prompt.py`, `analyze_hw3.py`.
- [x] Retry recovery, failure buckets, coverage and exposure analysis are reported.
- [x] C1, C2 and HW3 personal verifications are recorded in the verified worksheets and summarized in the paper.
- [x] Genuine OpenCode JSONL session export is included; no fictional transcript is substituted.
- [x] Export README documents format, included/excluded parts and assignment fit.
- [x] Redaction report documents credential/privacy checks and exact redactions.
- [x] 99 unit tests pass.
- [x] Final numerical verifier passes all checks.
- [ ] Recommended before upload: human visual glance of the six rendered pages. The agent OCR-checked every page; it could not visually inspect image attachments.

## Key paths

- Report: `submission/Faritova_HW3_Final_Report.pdf`
- Paper source: `submission/paper_source.md`
- AI session: `submission/ai_session/opencode_hw3_session.jsonl`
- AI-session format note: `submission/ai_session/README.md`
- QA report: `submission/qa/qa_report.md`
- Experiment commit: `2e4a253`
- Submission branch: `dilara/hw3-retry-ablation`

## Reproduce checks

```bash
python3 -m unittest discover -s dilara_hw3/tests -p 'test_*.py'
python3 -m unittest discover -s dilara_hw2 -p 'test_*.py'
python3 -m unittest discover -s dilara_hw2/far-trans -p 'test_*.py'
python3 dilara_hw3/submission/verify_submission.py
```

Do not rerun Qwen inference or modify frozen experiment outputs when reproducing documentation checks.
