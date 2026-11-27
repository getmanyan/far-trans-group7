# HW3 — manual verification: one real user, real IDs, future Buy, hand nDCG@10

STATUS: **NOT VERIFIED — Dilara must execute and confirm after the DW run.**

This worksheet is intentionally blank until results exist. No user may be chosen using
future purchases; the selection rule below uses future truth only *after* the cohort is
fixed, and only to choose a case to audit.

## Fixed selection rule (from PROTOCOL.md §8)

After the DW run: among users with nonempty truth and positive `B − A` nDCG@10 delta,
pick smallest `|truth ∩ eligible|`, then largest `B − A`, then smallest user ID. If no
such user exists, pick the largest `B − A` and state that this fallback rule was used.

## Steps to execute after the run

1. Run the selection rule with a short script; print the user ID and the reason it was
   selected.
2. From `dilara_hw3/outputs/all_DW/predictions.csv.gz`, print the rank-1..10 ISIN lists
   for methods `structured_encoder_v1` (A) and `structured_retry_once` (B).
3. From `/Users/dafaritova/Downloads/FAR-Trans/transactions.csv`, print the actual Buy
   rows for that user with `2021-06-01 <= timestamp[:10] < 2021-07-01`, deduplicated
   and with `transactionID >= 0`. These are the future purchases used as truth.
4. Verify each recommended ISIN is in the eligible universe from `protocol.json`.
5. Hand-compute, with a calculator or a short independent script:

```
DCG     = sum over rank i (1..10) of 1/log2(i+1) if recommended ISIN is in truth
IDCG    = sum over rank i (1..min(10, |truth ∩ eligible|)) of 1/log2(i+1)
nDCG@10 = DCG / IDCG  (0 if truth is empty)
```

Reference implementation: `dilara_hw2/far-trans/starter.py:60-66`.

6. Compare your hand value with `per_user.json` for both A and B and with the saved
   failure/retry record for any repaired asset in the top-10.

## Fill in after execution

- Selected user ID: ______________________________________________
- Selection reason: ______________________________________________
- A top-10 ISINs (1..10): ________________________________________
- B top-10 ISINs (1..10): ________________________________________
- Future Buy ISINs and timestamps: _______________________________
- Hand DCG (A / B): ______________________________________________
- Hand IDCG: _____________________________________________________
- Hand nDCG@10 (A / B): __________________________________________
- Saved nDCG@10 (A / B): _________________________________________
- Match? _________________________________________________________
- Executed by: Dilara Faritova
- Date: __________

Raw evidence prepared by the agent (NOT personally verified):

- `dilara_hw3/outputs/replay_check_final/replay_comparison.json` — exact-metrics and
  byte-exact-ranking checks for the saved HW2 D100 run.
- `dilara_hw3/outputs/replay_check_final/predictions.csv` — replayed HW2 ranked IDs;
  use this only as a dry run of the worksheet procedure, not as the HW3 case.
- No HW3 A/B prediction file exists yet. Do not fill in a case from the replay output.

Note: `outputs/robustness_analysis/manual_verification.md` in my HW2 outputs contains
an analogous check for user `94A16DE0F59F24BB77C2` (nDCG@10 = 1.0). That is an **HW2**
artifact and is not a personal verification of this HW3 run.
