# HW3 FAR-Trans encoder ablation

Anastasia Getman · Group 7 · HSE LLM4Rec

The experiment tests whether a weak LLM attribute view improves ranking relative to both a raw TF-IDF control and a same-weight rule-based attribute view. It reuses the HW2 Qwen3-1.7B outputs. See [PROTOCOL.md](PROTOCOL.md) for the comparisons and analysis plan recorded before the full warm cohort run.

## Reproduce

Extract the HW2 verification archive to obtain a directory containing FAR-Trans, RecSys-LLMs, getman/hw2 and outputs/attr_encoder. From this folder, run the following using Python 3.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reproduce.py --hw2 /path/to/hw2_verify --out replay_D100
PYTHONDONTWRITEBYTECODE=1 python3 reproduce.py --hw2 /path/to/hw2_verify --out replay_DW --cohort DW
python3 verify_metrics.py --hw2 /path/to/hw2_verify --run replay_DW
python3 audit_hw3.py --hw2 /path/to/hw2_verify --run replay_DW --out audit.json
```

Use fresh output directories. The replay uses CPU and saved attributes and checks data hashes, settings, the D100 user order, all 8,000 HW2 prediction rows and all eight HW2 metric entries. The independent verifier rebuilds the purchase labels from transactions and checks nDCG for each method from its saved Top-10 lists.

Compare fresh metrics.json and checks.json with the reference files in results/ and results_DW/. Compare paired_analysis.json for DW. The manifest records script and input hashes and elapsed time. Keep the source archive, predictions.csv, per_user.json and run_manifest.json local. Per-user outputs and the manifest contain customer identifiers.

## Results on the full warm cohort

| Method | nDCG@10, all 10,404 users | nDCG@10, 1,178 users with purchases |
|---|---:|---:|
| Latest buy | 0.0526 | 0.4648 |
| Raw TF-IDF | 0.0419 | 0.3703 |
| Rules, weight 0.25 | 0.0419 | 0.3700 |
| LLM, weight 0.25 | 0.0421 | 0.3720 |
| LLM, weight 1 | 0.0377 | 0.3334 |

Weak LLM minus weak rules was +0.00023 (95% paired user-bootstrap interval −0.00002 to +0.00048). Weak LLM minus equal-weight LLM was +0.00437 (+0.00351 to +0.00526). The two cohorts share the same time window. See [paired analysis](results_DW/paired_analysis.json) for directional counts, history-length slices, case studies and fallback sensitivity.

The [post-run audit](results_DW/audit.json) checks all 767 saved prompts against the as-of source rows, summarizes field coverage, and splits buyer-mean nDCG into contributions from repeat and new-to-user purchases.
