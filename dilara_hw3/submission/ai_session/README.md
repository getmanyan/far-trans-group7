# AI-session export

This directory contains the genuine AI-session artifact for Homework 3.

## Files

- `opencode_hw3_session.jsonl` — the exported session, generated directly from the local OpenCode SQLite database at `/Users/dafaritova/.local/share/opencode/opencode.db`.
- `redaction_report.txt` — scanner results and the exact redaction counts.
- `README.md` — this format note.

## Format

`opencode_hw3_session.jsonl` is a documented JSONL derivative of the native OpenCode session database:

- Line 1 is metadata: source database, generation time, session IDs, part-type rules, counts and redaction counts.
- Every following line is one message record with `session_id`, `message_id`, role/model metadata and an ordered `parts` array.
- Retained part types: `text` and `tool`.
- Excluded part types: `reasoning`, `step-start`, `step-finish` and `compaction`.
- Tool parts retain `state.input` and `state.output`, so prompts, generated code, shell commands, file edits, tool calls and tool results are preserved.

This is not a hand-written or fabricated transcript. It was exported from the real session records by `../export_ai_session.py`. Repo links or paper drafts are not substituted for the session file.

## Contents

- Sessions: 4 — the main Homework 3 session plus three child exploration sessions.
- Main session ID: `ses_de478a399ffe26jei6mC04J7uK`.
- Message records: 401.
- Tool calls: 498.
- Tool results: 495.
- File size: 5,803,389 bytes.

## Privacy and redaction

The export was scanned for private keys, OpenAI-style keys, GitHub tokens/PATs, Google API keys, Slack tokens, bearer tokens and the local committer identity/hostname. Redactions were applied to exported string values only:

- Local committer identity: 14 replacements.
- Local hostname: 13 replacements.
- No credential or API-token values were found.

No retained prompt, generated code, tool call or tool result was paraphrased. The excluded internal reasoning and step markers are documented above and were not part of the submission evidence.

## Assignment fit

The assignment accepts a native JSON/JSONL session export or a documented derivative that preserves generated code, tool calls and tool results. This package satisfies that requirement because it is a direct SQLite-derived JSONL export with an explicit format note, redaction report and preserved tool inputs/outputs.
