# Dilara Faritova — HW3 (Encoder): validation-aware retry ablation

Branch `dilara/hw3-retry-ablation`, based on `dilara/hw2-structured-encoder`.
Working copy: `/Users/dafaritova/Downloads/far-trans-group7-hw3-dilara`.

**State: protocol only.** No experiment has been run on this branch, no model has been
called, no HW3 metric exists. The frozen protocol is [`PROTOCOL.md`](PROTOCOL.md).

## Question

One validation-aware second LLM attempt for asset responses rejected by the strict
source-grounded JSON validator: does it reduce source-only fallback usage and improve
future-purchase nDCG@10?

## Contents

| file | purpose |
|---|---|
| `PROTOCOL.md` | frozen protocol, cohorts, methods, ablation, endpoints, risks |
| `verification/C1_paper.md` | manual check of a cited paper method/result (NOT performed) |
| `verification/C2_data.md` | manual check of a FAR-Trans record and temporal rule (NOT performed) |
| `verification/HW3_case.md` | manual nDCG@10 worksheet for a real user (NOT performed) |
| `retry_prompt.py`, `retry_encoder.py`, `run_hw3.py`, `analyze_hw3.py`, `tests/` | to be added in later commits, after protocol approval |

## Read-only inputs (never modified)

```
/Users/dafaritova/Downloads/FAR-Trans/
/Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps/
```

Teammate branches `maria/hw3-encoder-ablation` and `anastasia/hw3-encoder-ablation` are
read-only references. Their results are their runs, not mine.

## Commands after approval

See `PROTOCOL.md` §7. Before any model call, run the CPU-only input verification and
the exact D100 replay check of method A against the saved HW2 metrics.

Only code and small JSON/manifests are committed; datasets, prompts, generations,
per-user outputs and caches stay in ignored local directories.

## Personal verification

All three worksheets are `NOT VERIFIED`. Do not report any check as personally
performed until Dilara executes it and records the observation herself.
