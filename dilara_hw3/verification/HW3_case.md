# HW3 — manual verification: one real user, real IDs, future Buy, hand nDCG@10

STATUS: **PERSONALLY VERIFIED — 2026-11-27.** Dilara personally verified the case inputs,
A/B predictions and hand arithmetic, and personally executed the eligibility verification
in her terminal. The purchased asset and both A/B Top-10 lists passed the eligible-universe
check; C1, C2 and HW3 are all personally verified.

This case was chosen only after the DW cohort was fixed. No user was selected using
future purchases before the run; the fixed selection rule below uses future truth only
to choose a case to audit.

## Fixed selection rule (from `PROTOCOL.md` §8)

After the DW run: among users with nonempty truth and positive `B − A` nDCG@10 delta,
pick smallest `|truth ∩ eligible|`, then largest `B − A`, then smallest user ID. If no
such user exists, pick the largest `B − A` and state that the fallback rule was used.

## Dilara-observed case inputs and predictions

- Selected user ID: **`59E9527FA16DB58874C8`**
- Selection reason: fixed rule; `relevant_count = 1`, `B − A = 0.36907024642854247`,
  user ID `59E9527FA16DB58874C8`. Agent-run reproduction found 56 positive-delta
  candidates; this user is first under the rule.
- A (`structured_encoder_v1`) top-10 ISINs (1..10):

  1. `GRS298343005`
  2. `GRS120003009`
  3. `GRS120131008`
  4. `GRS426003000`
  5. `US71654V4086`
  6. `GRS204003008`
  7. `GRS096003009`
  8. `GRS087103008`
  9. `GRS014003032`
  10. `GRS473003002`

- B (`structured_retry_once`) top-10 ISINs (1..10):

  1. `GRS120003009`
  2. `GRS298343005`
  3. `GRS120131008`
  4. `GRS426003000`
  5. `GRS204003008`
  6. `US71654V4086`
  7. `GRS096003009`
  8. `GRS014003032`
  9. `GRS473003002`
  10. `GRS477003008`

- Future Buy row observed in `transactions.csv`:

  `customerID=59E9527FA16DB58874C8`, `ISIN=GRS120003009`, `transactionID=9155307`,
  `transactionType=Buy`, `timestamp=2021-06-29`.

- Eligibility: **PASSED**. The purchased asset `GRS120003009` and all 10 ISINs in both A
  and B Top-10 lists are inside the 767-asset eligible universe. Dilara reviewed the
  eligibility-check results and confirmed the three `all_in_eligible=True` outputs.
- Saved nDCG@10 (A / B): `0.6309297535714575` / `1.0`.
- Important caveat: the future-purchased asset `GRS120003009` itself was **not**
  repaired by the retry. Agent-run audit shows original error
  `name contains a term not supported by its source field`, retry error of the same
  type, `retry_valid=false`, and source-only fallback. The rank improvement is therefore
  not a clean "repaired asset moved up" story.

## Completed personal arithmetic check

- Executed by: **Dilara Faritova**
- Date: **2026-11-27**
- Verified identity: `1 / log2(3) = 0.63092975` (rounded to eight decimal places).
- Verified interpolation: with one relevant asset, IDCG@10 = `1.00000000`.
- Hand DCG (A / B): `0.63092975` / `1.00000000`.
- Hand nDCG@10 (A / B): `0.63092975` / `1.00000000`.
- Difference (B − A): **`+0.36907025`**.
- Match with saved per-user results? **Yes**. Saved full-precision values are
  `0.6309297535714575` and `1.0`, whose eight-decimal roundings are `0.63092975` and
  `1.00000000`.

The precise underlying arithmetic is: A's relevant asset is at rank 2, so
`DCG_A = 1/log2(3) = 0.6309297535714575`; B's relevant asset is at rank 1, so
`DCG_B = 1/log2(2) = 1.0`; `B − A = 0.36907024642854247`, which rounds to
`+0.36907025`.

## Personal eligibility check

Executed personally by Dilara Faritova in her terminal on **2026-11-27**. The command
verified that each recommendation list contains exactly 10 items and that every
recommended ISIN belongs to the eligible universe.

Observed output:

```text
Eligible universe: 767
Purchased asset eligible: True

structured_encoder_v1
Top-10 eligible: True
Purchased asset rank: 2

structured_retry_once
Top-10 eligible: True
Purchased asset rank: 1
```

- Recorded by: **Dilara Faritova**
- Date: **2026-11-27**
- Eligibility verdict: **PASSED** for purchased asset `GRS120003009`, A Top-10 and B Top-10.
- No further eligibility check is required for this case.

## Full read-only reconstruction command

Optional fuller reproduction of selection, eligibility, truth rows and arithmetic. It
writes no files and performs no model calls.

```bash
python3 - <<'PY'
import csv, json, math
from pathlib import Path

BASE = Path('/Users/dafaritova/Downloads/far-trans-group7-hw3-dilara/dilara_hw3')
HW2 = Path('/Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps')
DATA = Path('/Users/dafaritova/Downloads/FAR-Trans')
A = 'structured_encoder_v1'
B = 'structured_retry_once'

protocol = json.loads((HW2 / 'protocol.json').read_text())
eligible = set(protocol['eligible_assets'])
cutoff, end = protocol['cutoff'], protocol['end_exclusive']
per_user = json.loads((BASE / 'outputs/DW_all/per_user.json').read_text())
scores = {}
for row in per_user:
    scores.setdefault(row['user_id'], {})[row['method']] = row

candidates = []
for uid, methods in scores.items():
    if A in methods and B in methods and methods[A]['relevant_count'] > 0:
        delta = methods[B]['ndcg_at_10'] - methods[A]['ndcg_at_10']
        if delta > 0:
            candidates.append((methods[A]['relevant_count'], -delta, uid, delta))
candidates.sort()
relevant_count, neg_delta, uid, delta = candidates[0]
print('eligible_assets:', len(eligible))
print('selection_key:', {'relevant_count': relevant_count, 'B_minus_A': delta, 'user_id': uid})
print('candidate_count:', len(candidates))

rankings = {}
with (BASE / 'outputs/DW_all/predictions.csv').open(newline='') as f:
    for row in csv.DictReader(f):
        if row['user_id'] == uid and row['method'] in (A, B) and int(row['rank']) <= 10:
            rankings.setdefault(row['method'], {})[int(row['rank'])] = row['ISIN']

truth_rows = []
seen = set()
with (DATA / 'transactions.csv').open(newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        key = tuple(sorted(row.items()))
        if row['customerID'] != uid or key in seen:
            continue
        seen.add(key)
        if int(row['transactionID']) < 0:
            continue
        if row['transactionType'] != 'Buy' or row['ISIN'] not in eligible:
            continue
        if cutoff <= row['timestamp'][:10] < end:
            truth_rows.append(row)
truth = {row['ISIN'] for row in truth_rows}
print('future_buy_truth:', sorted(truth))
for row in truth_rows:
    print('future_buy_row:', {k: row[k] for k in ('customerID','ISIN','transactionID','transactionType','timestamp')})

idcg = sum(1 / math.log2(i + 2) for i in range(min(10, len(truth))))
print('IDCG@10:', repr(idcg))
for method in (A, B):
    ranking = [rankings[method][i] for i in range(1, 11)]
    hits = [(i, isin) for i, isin in enumerate(ranking, 1) if isin in truth]
    dcg = sum(1 / math.log2(rank + 1) for rank, _ in hits)
    ndcg = dcg / idcg if idcg else 0.0
    print(method, 'top10:', ranking)
    print(method, 'eligible_top10:', all(isin in eligible for isin in ranking))
    print(method, 'hits:', hits, 'DCG:', repr(dcg), 'nDCG:', repr(ndcg), 'saved:', repr(scores[uid][method]['ndcg_at_10']))
PY
```

## Agent evidence (not personal verification)

- `dilara_hw3/outputs/analysis_DW.json` and `dilara_hw3/results/phase3_summary.json`:
  aggregate bootstrap, subgroup and failure analysis.
- `dilara_hw3/outputs/DW_all/predictions.csv`, `per_user.json`, `metrics.json` and
  `run_manifest.json`: all-method DW predictions, per-user scores, aggregate metrics and
  cohort manifest.
- `dilara_hw3/outputs/full_retry/retry_audit.jsonl`: audit line for `GRS120003009`.
- The analogous HW2 worksheet for `94A16DE0F59F24BB77C2` is HW2 evidence only and is not
  personal verification of this HW3 run.
