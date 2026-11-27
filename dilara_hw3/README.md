# Dilara Faritova — HW3 (Encoder): validation-aware retry ablation

Branch `dilara/hw3-retry-ablation`, based on `dilara/hw2-structured-encoder`.
Working copy: `/Users/dafaritova/Downloads/far-trans-group7-hw3-dilara`.

**State: Phase 3 complete (full retry run + evaluation + analysis). Phase 4 documentation
complete: C1, C2 and HW3 are all personally verified by Dilara, with the HW3 worksheet
marked `PERSONALLY VERIFIED` on 2026-11-27. Bootstrap parameters and all eight metric rows
were rechecked against saved files without rerunning experiments. Formal HW3 assignment
requirements verified. No final PDF generated; no push or merge.**

The frozen protocol is [`PROTOCOL.md`](PROTOCOL.md); post-protocol decisions are in
[`IMPLEMENTATION_NOTES.md`](IMPLEMENTATION_NOTES.md).

## Question

One validation-aware second LLM attempt for asset responses rejected by the strict
source-grounded JSON validator: does it reduce source-only fallback usage and improve
future-purchase nDCG@10?

Primary answer: it reduces fallback usage substantially but does **not** demonstrate an
overall recommendation gain. DW all-user B−A is `−0.000288` with 95% bootstrap CI
`[−0.000627, +0.000048]`; 56 users improve, 115 worsen and 10,233 are unchanged.

## Contents

| file | purpose |
|---|---|
| `PROTOCOL.md` | frozen protocol, cohorts, methods, ablation, endpoints, risks |
| `verification/C1_paper.md` | manual check of a cited paper method/result (personally verified) |
| `verification/C2_data.md` | manual check of a FAR-Trans record and temporal rule (personally verified) |
| `verification/HW3_case.md` | manual nDCG@10 worksheet (PERSONALLY VERIFIED) |
| `verification/REPORT_OUTLINE.md` | paper-style outline, exact metrics table, submission checklist |
| `hw2.py` | imports the untouched HW2 modules |
| `retry_prompt.py` | exact protocol §5 retry prompt |
| `retry_encoder.py` | saved-output replay, one retry per unique prompt, evidence logs, view construction |
| `run_hw3.py` | preflight, D100 replay gate, bounded retry inference, cohort scoring |
| `verify_inputs.py`, `analyze_hw3.py` | CPU-only preflight; failure analysis and paired bootstrap |
| `tests/test_retry.py` | 11 contract tests with fake generators |
| `IMPLEMENTATION_NOTES.md`, `results/phase2_summary.json` | Phase 2 implementation record and summary |
| `results/phase3_summary.json` | Phase 3 aggregate summary |
| `outputs/` | ignored local evidence: retry logs, predictions, per-user scores, analyses |

## Read-only inputs (never modified)

```
/Users/dafaritova/Downloads/FAR-Trans/
/Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps/
```

Teammate branches `maria/hw3-encoder-ablation` and `anastasia/hw3-encoder-ablation` are
read-only references. Their results are their runs, not mine.

## Commands after approval

See `PROTOCOL.md` §7 and `IMPLEMENTATION_NOTES.md`. Before any model call, run the
CPU-only input verification and the exact D100 replay check of method A against the
saved HW2 metrics. Use `PYTHONHASHSEED=0`; for MPS inference use the HW2 venv Python
`/Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/.venv/bin/python`.

Only code and small JSON/manifests are committed; datasets, prompts, generations,
per-user outputs and caches stay in ignored local directories.

## Personal verification

- C1 and C2 are recorded as personally verified by Dilara on 2026-11-27.
- HW3 case inputs, A/B predictions and nDCG@10 arithmetic are recorded from Dilara's
  inspection (`A = 0.63092975`, `B = 1.00000000`, `B − A = +0.36907025`).
- Dilara personally executed the eligibility verification on 2026-11-27: 767 eligible
  assets, `GRS120003009` eligible, both Top-10 lists eligible with purchased-asset ranks
  2 (A) and 1 (B); `verification/HW3_case.md` is marked `PERSONALLY VERIFIED`.
- Bootstrap parameters were checked against `analyze_hw3.py` and saved analysis files:
  `SEED = 20261120`, `DRAWS = 10000`; no experiment was rerun.
- Formal HW3 assignment requirements were verified from `/Users/dafaritova/Downloads/homework3.md`.
- AI-generated analysis is labelled as agent evidence, not as personal verification.
