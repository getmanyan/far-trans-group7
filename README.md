# HW2 — LLM attribute encoder for FAR-Trans (Anastasia Getman, Group 7)

**Research question (Encoder track).** Do LLM-derived asset attributes improve nDCG@10
over the same content-based recommender that uses only the raw as-of asset metadata?

**Change.** The course's LLM-Rec-inspired encoder asks the LLM to *paraphrase* each
asset's metadata. This encoder instead asks the LLM to *fill a fixed schema* —
`asset_class`, `sector`, `region`, `currency`, each from a closed vocabulary — from the
as-of metadata and the asset name. Valid answers become prefixed tokens
(`sector_financials`), a second TF-IDF view next to the raw-metadata view. Scoring is
unchanged from the course encoder: a count-weighted profile of the user's past Buys,
cosine similarity over all 767 eligible assets, top ten.

| Method | Role |
|---|---|
| `popularity`, `cbf`, `latest_buy`, `latest_buy_or_sell` | four provided baselines (starter, unchanged) |
| `original_text_cbf` | control: raw-metadata TF-IDF only |
| `rule_attr_encoder` | same-information control: same schema filled by fixed rules from raw metadata, no LLM |
| `llm_attr_encoder` | **my method**: raw view + LLM attribute view |
| `llm_attr_only` | ablation: LLM attribute view only |
| `llmrec_encoder` | optional: course paraphrase encoder run on the same GPU |

Invalid LLM answers (no JSON, wrong keys, value outside the vocabulary) are logged in
`encoder_failures.jsonl`; with `--on-invalid fallback` that asset keeps only its raw
view. Results include those fallbacks and their count is reported.

## Protocol

Starter defaults: deterministic 100-user warm sample, cutoff 2021-06-01 (exclusive),
30-day Buy window, repeat purchases allowed, binary nDCG@10, empty truth = 0 in the
all-user mean, nonempty mean reported separately. Course repository
`dryjins/RecSys-LLMs` at commit `f6850861ea20a51e1fb018ee4e5f840c2ac759e0`.
Only as-of asset metadata enters the prompt — no customer data, ISIN, price, Sell or
future row. The asset name can activate the model's pretrained knowledge, which may
post-date the cutoff; generated attributes are not automatically fact-checked.
Not investment advice.

## Model and settings

`Qwen/Qwen3-1.7B`, revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` (same as the course
encoder), greedy decoding, thinking disabled via the chat template, 8192-token context,
96 new tokens per asset. bfloat16 on GPUs with compute capability ≥ 8, float16 otherwise
(Colab T4). Exact versions, GPU and timings are written to `run_manifest.json`.

## Run

Colab (T4 GPU): open `hw2_colab.ipynb`, set `TEAM_REPO`, run all cells.

Local, from this folder, with a checkout of the course repository:

```bash
pip install -r requirements.txt
python -m unittest test_attribute_encoder
python attribute_encoder.py --course-dir /path/to/RecSys-LLMs/project \
  --data-dir /path/to/FAR-Trans --output-dir outputs/attr_encoder \
  --model Qwen/Qwen3-1.7B --revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e \
  --allow-download --device cuda --on-invalid fallback
python analyze.py --course-dir /path/to/RecSys-LLMs/project --data-dir /path/to/FAR-Trans \
  --baseline outputs/baseline --runs outputs/attr_encoder --out outputs/results.md
```

`--prepare-only` writes the 767 prompts without loading a model.

## Files

- `attribute_encoder.py` — prompt, validation, rule control, scoring, run manifest
- `run_course_encoder.py` — runs the course paraphrase encoder unchanged except for dtype
- `analyze.py` — four-decimal results table, subgroup split, protocol checks
- `test_attribute_encoder.py` — unit tests (no model, no data)
- `hw2_colab.ipynb` — end-to-end Colab run

Datasets, model weights, caches, prompts and user-level outputs are not committed
(see `.gitignore`).
