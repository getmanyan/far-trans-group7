| Method | Users | Users with future purchases | nDCG@10: all users | nDCG@10: nonempty truth | Runtime | Failed cases |
|---|---:|---:|---:|---:|---:|---:|
| Popularity | 100 | 11 | 0.0286 | 0.2599 | 17.8 s (whole starter run) | 0 |
| CBF | 100 | 11 | 0.0201 | 0.1827 | 17.8 s (whole starter run) | 0 |
| Latest buy | 100 | 11 | 0.0277 | 0.2520 | 17.8 s (whole starter run) | 0 |
| Latest buy or sell | 100 | 11 | 0.0271 | 0.2464 | 17.8 s (whole starter run) | 0 |
| Original-text TF-IDF CBF (control) | 100 | 11 | 0.0235 | 0.2140 | 179 s (whole attr_encoder run, 64 cache hits) | 0 |
| Rule attributes, no LLM (same-info control) | 100 | 11 | 0.0224 | 0.2034 | 179 s (whole attr_encoder run, 64 cache hits) | 0 |
| LLM attribute encoder (mine) | 100 | 11 | 0.0225 | 0.2049 | 179 s (whole attr_encoder run, 64 cache hits) | 22 |
| LLM attributes only (ablation) | 100 | 11 | 0.0010 | 0.0092 | 179 s (whole attr_encoder run, 64 cache hits) | 22 |

Subgroup by distinct past-bought assets (mean nDCG@10 over nonempty-truth users):

| Method | 1–3 distinct: n | 1–3 distinct | 4+ distinct: n | 4+ distinct |
|---|---:|---:|---:|---:|
| Popularity | 1 | 0.0000 | 10 | 0.2859 |
| CBF | 1 | 0.0000 | 10 | 0.2010 |
| Latest buy | 1 | 0.0000 | 10 | 0.2772 |
| Latest buy or sell | 1 | 0.0000 | 10 | 0.2711 |
| Original-text TF-IDF CBF (control) | 1 | 0.0000 | 10 | 0.2354 |
| Rule attributes, no LLM (same-info control) | 1 | 0.0000 | 10 | 0.2237 |
| LLM attribute encoder (mine) | 1 | 0.0000 | 10 | 0.2254 |
| LLM attributes only (ablation) | 1 | 0.0000 | 10 | 0.0101 |

Protocol checks (True = matches starter protocol.json):
- attr_encoder True True True True True
- starter popularity True
- starter cbf True
- starter latest_buy True
- starter latest_buy_or_sell True
