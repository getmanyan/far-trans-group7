# HW3 development protocol — Maria Senenko, Group 7 (Encoder track)

Written and committed **before** any HW3 method comparison was run. Later changes, if any,
must be made in a new commit and listed under "Amendments" with the reason.

These are **development results**, not official benchmark scores.

## Question

For which users does the course LLM-Rec paraphrase encoder (Qwen3-1.7B paraphrases of
supplied asset attributes, added as a second TF-IDF view) change nDCG@10 relative to
the matched original-text TF-IDF CBF control? Target conditions from HW2: short
purchase history (1–3 distinct assets) and histories made of assets without
sector/industry metadata.

## Data and evaluation (identical for every method)

- FAR-Trans files, SHA-256 identical to the HW2 run manifest:
  transactions.csv 358871fa…cc8f, asset_information.csv 33f9897b…7a590,
  customer_information.csv c4ad52eb…064af, close_prices.csv 6ba1fe83…0c8f.
- Course code: dryjins/RecSys-LLMs `799e54c` (code under project/ identical to `f685086`,
  which the HW2 README cites; the two commits differ only in README/homework3.md).
- Cutoff 2021-06-01 (exclusive); evaluation window 2021-06-01 … 2021-07-01 (30 days);
  repeat purchases allowed; Buy transactions only; eligible assets = the 767 assets with
  a positive close price before the cutoff (same for every user).
- Labels, eligible assets, history and popularity come only from `starter.load_data`
  and `starter.contexts_for`, unchanged.
- Metric: binary nDCG@10 (`starter.ndcg10`); mean over all evaluated users with empty
  truth counted as 0 (primary), plus mean over users with ≥1 future purchase and their
  count. Four decimals.

## User sets (selection does not use future purchases or scores)

- **D100** — the HW2 teaching sample: first 100 warm users by the starter's ordering
  (SHA-256 of "42:"+customerID). Reported for continuity with HW2.
- **DW** — all warm users: every customer with ≥1 Buy before the cutoff, same ordering
  (`select_users(..., 'warm', 0)`), 10,404 users. D100 is the first 100 of DW.
  DW is the **primary development set** because D100 has 1 / 0 users with future
  purchases in the two target subgroups.

## Subgroups (defined from pre-cutoff data only; same rules as HW2 analyze_maria.py)

- History length = number of distinct assets bought before the cutoff: `len_1`,
  `len_2_3`, `len_4_plus`.
- Metadata: an asset is "none" if both sector and industry are missing
  ('', Not_Available, nan, unknown), "both" if both present, otherwise "one".
  User group `meta_none` if all history assets are "none", `meta_both` if all are
  "both", else `meta_mixed`.

## Methods

1. Popularity, 2. CBF, 3. Latest buy, 4. Latest buy or sell — starter baselines, unchanged.
5. `original_text_cbf` — matched control: TF-IDF over the canonical JSON of supplied
   attributes (`encoder.source_text`), count-weighted history profile, cosine.
6. `llmrec_encoder` — course LLM comparison: original view + generated paraphrase view,
   each L2-normalised, concatenated in separate namespaces (`encoder.combine_views`).
7. **Ablation `llmrec_meta_none_only`** — identical to (6) except the generated view is
   kept **only for assets whose sector and industry are both missing**; every other asset
   keeps only its original view. TF-IDF of the generated view is fitted on the same full
   set of 767 paraphrases as in (6), so the only change is which assets carry the view.
   It tests whether the encoder's effect comes from paraphrasing metadata-poor assets
   (where the LLM could add wording that the sparse JSON lacks) or from paraphrasing
   assets that already have sector/industry.

Ranking for 5–7 uses `encoder.history_scores` and `encoder.predict`'s rule (sort by
−score, then ISIN; popularity if the profile has no overlap), top 10 of the 767 assets.

## LLM inference

- Model `Qwen/Qwen3-1.7B`, revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`, greedy,
  thinking disabled, max_new_tokens 160, course prompt `encoder.paraphrase_prompt`.
- Generations: the HW2 run on Google Colab (Tesla T4, float16, torch 2.14.1+cu130,
  transformers 4.57.6, 20.11.2026; 703 model calls + 64 cache hits for duplicate
  prompts, inference 1,115.7 s; 0 invalid outputs). Saved log:
  `inputs/hw2_generations.jsonl` (SHA-256 4ba16c96…a043).
- HW3 does **not** re-run the model (no GPU and no Hugging Face weight download in the
  HW3 environment). A replay backend returns the saved response for the exact prompt;
  a prompt not found in the log is an error, not a fallback. Validity check unchanged
  (1–40 words, else fallback to source text), counted and reported.
- Because generation is per asset, the same 767 paraphrases serve D100 and DW; no
  extra inference is needed for the larger set or for the ablation.

## Analyses fixed in advance

- Main table for D100 and DW: all methods, nDCG@10 all / nonempty / nonempty count.
- Subgroup table on DW for methods 5–7 and Latest buy.
- Paired difference (6 − 5) and (7 − 5) on DW, all users: mean, 95% percentile
  bootstrap interval over users (2,000 resamples, seed 42), and counts of users whose
  nDCG@10 goes up / down / is unchanged, and whose top-10 list is identical.
- Failure analysis: invalid outputs, fallbacks, coverage; paraphrase tokens absent
  from the source JSON (automatic screen) followed by manual reading of flagged
  paraphrases; users where the encoder lowers nDCG@10; users whose list does not change.
- Personal verification by Maria: one user's top-10 and nDCG@10 by hand; one paraphrase
  against its source JSON.

## Expectation written before running

From HW2 (D100: +0.0001 all-user) the overall difference is expected to be near zero
on DW as well. If the encoder helps anywhere, the ablation should keep most of the
effect only if the effect comes from metadata-poor assets.

## Amendments

1. (23.11, after the pre-registered run and the paraphrase audit; commit 75e4c17 holds
   the pre-registered results unchanged.) The audit found that 381 of 767 saved outputs
   are copies of the input JSON rather than prose; the course validity rule (1–40 words)
   accepts them. Added as **post-hoc diagnostics, not the pre-registered ablation**:
   `diag_prose_only.py` (generated view kept only for prose outputs; full encoder split by
   whether the history contains a prose asset), `format_shift.py` (share of JSON-copy
   assets among new top-10 items), `repeat_analysis.py` and `change_types.py` (whether
   changed nDCG comes from re-ordering the user's own assets or from new assets),
   `case_details.py` (case studies). Same users, labels, cutoff and code paths.
