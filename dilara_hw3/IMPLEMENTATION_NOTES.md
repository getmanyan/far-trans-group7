# HW3 Phase 2 implementation notes (addendum to the frozen protocol)

This file records implementation decisions made **after** protocol commit `d644f56`.
It does not change any endpoint, cohort, method definition, metric or selection rule in
`PROTOCOL.md`. See `PROTOCOL.md` §10 Amendment 1.

## What was built

| file | role |
|---|---|
| `hw2.py` | imports untouched HW2 modules (`encoder`, `runtime`, `data_adapter`, `starter`) |
| `retry_prompt.py` | exact protocol §5 retry prompt; forbidden-term list |
| `retry_encoder.py` | replay of saved attempt 1, retry records, one-call-per-unique-prompt, full evidence logs, view construction |
| `run_hw3.py` | preflight, exact D100 replay gate, bounded retry inference, cohort scoring for A/B/C/D + four baselines |
| `verify_inputs.py` | CPU-only data/protocol/failure/cohort checks and 520→480 mapping |
| `analyze_hw3.py` | failure table and paired bootstrap (ready, not run on HW3 data) |
| `tests/test_retry.py` | 11 contract tests with fake generators |

No HW2 file, teammate branch, dataset or saved output was modified. `run_hw3.py` hashes
the whole HW2 output tree before and after every run and raises if it changed.

## Implementation decisions (transparent, not protocol changes)

1. **Replay method name.** In `replay_check` only, method A is written as
   `structured_attribute_encoder` (the exact HW2 name) so saved artifacts can be
   compared byte-for-byte. In HW3 runs it is `structured_encoder_v1` as in the protocol.
2. **`--max-users 0`.** The new runner calls `starter.select_users(..., limit=0)` for DW;
   HW2 `data_adapter.load` is unchanged. D100 uses `limit=100`.
3. **PYTHONHASHSEED.** Official `starter.tokens` iterates a Python `set`, so summing
   floats in `starter.content_scores` can differ by ~1e-16 between processes and flip
   ties in the **official `cbf` baseline only**. Replay explored seeds; all HW3 commands
   below were run with `PYTHONHASHSEED=0` and the value is recorded in every manifest.
   This does not change any preregistered endpoint, only determinism of tie order.
4. **Retry deduplication.** 520 rejected assets map to **480 unique retry prompts**;
   `run_retries` calls the model once per unique prompt and reuses the response for all
   assets in that group. This matches the HW2 cache semantics.
5. **Validation is never relaxed.** `parse_or_fallback` calls the untouched
   `encoder.parse_structured_attributes`; a rejected word remains rejected and falls
   back deterministically. No repair of term text is performed by code.

## Verified so far (agent-run; Dilara has not personally confirmed)

- Unit tests: HW3 11/11, HW2 30/30, official starter 58/58.
- Preflight `verify_inputs.json`: all checks pass, including 767/767/767, 520 failures,
  480 unique retry prompts, 10,404/1,178/7,360/63 cohorts.
- D100 replay: `metrics.json` and `per_user.json` byte-identical to HW2; every ranked
  list identical except the official `cbf` baseline for 7 users (tie noise, item 3).
- Smoke test: 3 rejected assets, 3 unique retry prompts, 1 valid retry / 2 still
  rejected, device `mps`, resolved revision `70d244cc…`, 3 new calls, 0 cache hits.

## Commands used

```bash
python3 -m unittest discover -s dilara_hw3/tests -p 'test_*.py'
python3 -m unittest discover -s dilara_hw2 -p 'test_*.py'
python3 -m unittest discover -s dilara_hw2/far-trans -p 'test_*.py'
PYTHONHASHSEED=0 python3 dilara_hw3/verify_inputs.py \
  --data-dir /Users/dafaritova/Downloads/FAR-Trans \
  --hw2-outputs /Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps \
  --out dilara_hw3/outputs/verify_inputs.json
PYTHONHASHSEED=0 python3 dilara_hw3/run_hw3.py --cohort D100 --method replay_check \
  --data-dir /Users/dafaritova/Downloads/FAR-Trans \
  --hw2-outputs /Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps \
  --output-dir dilara_hw3/outputs/replay_check_final
PYTHONHASHSEED=0 /Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/.venv/bin/python \
  dilara_hw3/run_hw3.py --cohort D100 --method retry \
  --data-dir /Users/dafaritova/Downloads/FAR-Trans \
  --hw2-outputs /Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps \
  --output-dir dilara_hw3/outputs/smoke_3 \
  --asset-ids dilara_hw3/outputs/smoke_asset_ids.json \
  --model Qwen/Qwen3-1.7B --revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e --device mps
```

The venv Python 3.9.6 was used only for MPS inference (torch 2.8.0, transformers 4.57.6);
CPU tests used `/usr/bin/python3`.

## Not done

No full 480-prompt retry, no D100/DW B or C metrics, no nDCG comparison, no PDF, no
push, no branch merge. C1/C2/HW3 worksheets remain `NOT VERIFIED`.
