# FAR-Trans HW3 full warm cohort protocol

This protocol was written after the HW2 and HW3 D100 results were known and before the full warm cohort run. D100 is nested within DW, both use the same historical window, and both are development evaluations.

## Question and comparisons

Does Qwen-derived closed-schema asset metadata improve nDCG@10 over rules using the same source fields, at the same weight of 0.25? The primary comparison is LLM minus rules at weight 0.25. The raw TF-IDF comparison removes the attribute view (weight 0). Keep the weight-1 methods, LLM-attributes-only ablation and all four course baselines. The original 100-user replay must match all HW2 Top-10 rows and metrics exactly. Use the same configurations on DW, with all eligible warm users.

## Common evaluation

Use the HW2 data and starter. Fix cutoff 2021-06-01, a 30-day Buy window ending 2021-07-01 exclusive, the 767 eligible assets, repeat purchases allowed and binary nDCG@10. Report all-user means with empty truth as zero, and means among users with nonempty truth. Reuse cached validated attributes for all assets. An invalid result yields an empty attribute view for that asset and retains its raw metadata vector.

## Analyses

Report paired differences (LLM 0.25 minus rules 0.25, raw TF-IDF, and LLM 1), directional counts and 95% paired percentile bootstrap intervals on DW, using 2,000 user resamples and seed 42. Use the deterministic course user order. Summarize the two primary comparator deltas by distinct prior buys (1, 2–3, 4+) and for buyers with nonempty truth. Include representative gain and loss cases using sample row numbers, hit ranks and history length. Audit the invalid responses and measure exposure to the affected assets in history, truth and recommendations. As a sensitivity analysis, substitute rule attributes on just the rejected assets and rerun at weight 0.25. This substitution tests one fallback policy.

Record timings, original model settings and source hashes. No customer identifiers go in the repository package. Personal verification is recorded after the author performs it.

## Post-run diagnostics

The report revision adds an exact as-of prompt audit, attribute coverage, and an additive nDCG decomposition by whether the relevant asset appears in the observed pre-cutoff purchase history. These diagnostics were added after the cohort results were known. They use the original ranked lists and ideal DCG.
