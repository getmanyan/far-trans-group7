# Dilara Faritova - HW2 Structured Attribute Encoder

Individual Homework 2 implementation for Group 7, Encoder track.

## Contribution

The method asks an open-weight LLM to return strict JSON for six as-of FAR-Trans
asset fields: `name`, `category`, `subcategory`, `sector`, `industry`, and `market`.
Terms must be source-grounded and are converted to field-namespaced TF-IDF tokens.
The structured view is combined with the raw metadata view in the unchanged
history-weighted cosine scorer. Invalid responses are logged and use deterministic
source-only structured fallback features.

The implementation source commit in the personal repository is:
`4c56b30607d33e297f84f8792f9198e53b50de14`.
The upstream course source commit was:
`799e54c0493cf7e2b014152548ae5c18ee24a8f5`.

## Protocol And Model

- 100 deterministic warm users, cutoff `2021-06-01` exclusive.
- 30-day future Buy window ending `2021-07-01` exclusive.
- Repeat purchases allowed; empty truth contributes zero.
- 767 eligible assets; all four starter baselines retained.
- Protocol hash: `50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417`.
- Model: `Qwen/Qwen3-1.7B`.
- Revision: `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.
- Dependencies: `torch==2.11.0`, `transformers==4.57.6`.

The completed run used Apple MPS with `torch==2.8.0` because the upstream torch
2.11.0 wheel was unavailable for the local Python 3.9 arm64 environment. The runtime
supports explicit `--device mps` and never silently substitutes CPU when MPS is
requested.

## Dataset Setup

Download and extract the official FAR-Trans dataset so the directory contains:
`transactions.csv`, `asset_information.csv`, `customer_information.csv`, and
`close_prices.csv`. Do not commit the dataset.

## Commands

From `dilara_hw2/`:

```bash
python -m unittest discover -s . -p 'test_encoder.py' -v
python -m unittest discover -s far-trans -p 'test_*.py' -v
python encoder.py \
  --data-dir /path/to/FAR-Trans \
  --output-dir outputs/structured_full_mps \
  --max-users 100 --candidate-count 50 \
  --model Qwen/Qwen3-1.7B \
  --revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e \
  --device mps --on-invalid fallback
```

The command above performs the full catalog inference. For a no-model preparation
check, add `--prepare-only`; this still writes prompts for all eligible assets.
For a bounded diagnostic, use `structured_smoke.py` with an `--assets-json` file
containing one to three allowlisted asset rows.

Offline analyses use only completed artifacts and never load a model:

```bash
python offline_analysis.py /path/to/FAR-Trans \
  outputs/structured_full_mps outputs/baseline_100 outputs/offline_analysis_v2
python robustness_analysis.py
```

The actual completed outputs are intentionally not part of this integration branch.
Keep them in a local ignored `outputs/` directory when reproducing.

## Files

- `encoder.py`: structured-attribute Encoder and scoring pipeline.
- `data_adapter.py`: starter loading policy and result serialization.
- `runtime.py`: local Transformers backend, explicit MPS support, logs and cache.
- `structured_smoke.py`: 1-3 asset non-evaluation diagnostic.
- `test_encoder.py`: Encoder unit and leakage tests; no model calls.
- `offline_analysis.py`: ablation and exploratory subgroup analysis.
- `robustness_analysis.py`: paired bootstrap, verification worksheet and leakage checks.
- `far-trans/starter.py`: copied official starter required by the Encoder.
- `far-trans/test_starter.py`: copied official starter tests.
- `requirements.txt`: inference dependency pins.

Datasets, model weights, virtual environments, caches, prompts, user-level outputs,
and native AI-session exports are excluded from this integration.
