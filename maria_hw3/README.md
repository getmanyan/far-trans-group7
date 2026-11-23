# HW3 — Maria Senenko (Group 7, Encoder track)

Development results, not official benchmark scores. Protocol: [PROTOCOL.md](PROTOCOL.md)
(frozen in commit 5af80d3 before any comparison; Amendment 1 lists the post-hoc diagnostics).

## Commits

| commit | content |
|---|---|
| 8d127b1 | HW2 files moved from `maria_hw2:<file>` names into `maria_hw2/` (renames only) |
| 5af80d3 | protocol frozen; saved HW2 generation log |
| 75e4c17 | **experiment commit**: pre-registered run on D100 and all 10,404 warm users |
| 54b5c35 | failure analysis and post-hoc diagnostics |
| f7cfb25 | independent re-implementation check |

## Reproduce (standard library only, except `independent_check.py`: pandas, numpy, scipy)

```bash
C=path/to/RecSys-LLMs/project     # course repo at 799e54c
D=path/to/FAR-Trans               # transactions.csv, asset_information.csv, ...
python run_hw3.py --course-dir $C --data-dir $D --generations inputs/hw2_generations.jsonl --output-dir out/D100 --max-users 100
python run_hw3.py --course-dir $C --data-dir $D --generations inputs/hw2_generations.jsonl --output-dir out/DW --max-users 0
gzip -k out/DW/predictions.csv out/DW/per_user.json   # later scripts read the .gz files
python analyze_hw3.py out/DW
python paraphrase_audit.py out/DW
python diag_prose_only.py --course-dir $C --data-dir $D --generations inputs/hw2_generations.jsonl --run-dir out/DW
python repeat_analysis.py --course-dir $C --data-dir $D --run-dir out/DW
python change_types.py out/DW $C $D
python format_shift.py out/DW $C $D
python independent_check.py $D inputs/hw2_generations.jsonl out/DW/metrics.json
```

The LLM is not re-run: `run_hw3.py` replays the saved Qwen3-1.7B responses
(`inputs/hw2_generations.jsonl`, HW2 Colab T4 run) for the exact prompts. On D100 it
reproduces every HW2 metric and prediction. Runtime on 2 vCPU: about 70 s for DW.

## Main results (DW, 10,404 users, 1,178 with purchases; nDCG@10 all / with purchases)

Latest buy 0.0526 / 0.4648 · original_text_cbf 0.0419 / 0.3703 · llmrec_encoder
0.0426 / 0.3761 · ablation llmrec_meta_none_only 0.0421 / 0.3722. Encoder − control
+0.0007 (95% bootstrap +0.0002 … +0.0011), concentrated in users with 4+ assets;
nothing measurable for 1-asset or metadata-less histories. 381/767 saved outputs are
JSON copies of the input, not paraphrases. Details: `outputs/DW/*.json`.
