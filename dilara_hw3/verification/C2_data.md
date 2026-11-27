# C2 — manual verification of a FAR-Trans record and temporal assumption

STATUS: **PERSONALLY VERIFIED BY DILARA (reported 2026-11-27).**

Target record: `ISIN=FI0009003305` (`Sampo Oyj`). Its HW2 first response was rejected
with `name contains a term not supported by its source field` because the model emitted
`name: ["sampoyj"]` while the source name contains a space.

## Task

Check one real CSV row and the temporal assumption used by the starter.

## Recorded observation

- Verbatim CSV row observed (`asset_information.csv`):

  ```json
  {"ISIN": "FI0009003305", "assetCategory": "Stock", "assetName": "Sampo Oyj", "assetShortName": "UNK_93", "assetSubCategory": "", "industry": "Insurance - Diversified", "marketID": "XHEL", "sector": "Financial Services", "timestamp": "2018-01-02"}
  ```

- Is the metadata timestamp strictly before `2021-06-01`? **Yes**; `2018-01-02 <
  2021-06-01`.
- Which terms are substrings of the casefolded source name `"sampo oyj"`? `sampoyj`:
  **False**; `sampo`: **True**; `oyj`: **True**.
- Exact validator error recorded in my HW2 run: `name contains a term not supported by
  its source field`.
- Recorded HW2 response (agent-retrieved from the saved failure log): a JSON object with
  a duplicated `category` key and `name: ["sampoyj"]`. The saved failure reason is the
  unsupported name, not the duplicate key.
- Does this support the retry hypothesis? **It supports classifying the failure as a
  fixable formatting/grounding error in principle.** It does not by itself prove that my
  retry fixed this asset: the saved retry audit for `FI0009003305` still shows
  `name=["sampoyj"]`, `retry_valid=false`, and source-only fallback.
- Executed by: **Dilara Faritova** (personally reported).
- Date: **2026-11-27**.

## Commands used / to re-run

```bash
cd /Users/dafaritova/Downloads/FAR-Trans

# (a) exact row in the original asset file
python3 - <<'PY'
import csv
with open('asset_information.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row['ISIN'] == 'FI0009003305':
            print(row)
PY

# (b) temporal rule in the unchanged starter
grep -n "def latest_before" /Users/dafaritova/Downloads/far-trans-group7-hw3-dilara/dilara_hw2/far-trans/starter.py
grep -n "timestamp.*< cutoff" /Users/dafaritova/Downloads/far-trans-group7-hw3-dilara/dilara_hw2/far-trans/starter.py

# (c) reproduce the validator's substring rule on this record
python3 - <<'PY'
source_name = 'Sampo Oyj'.casefold()
for term in ['sampoyj', 'sampo', 'oyj']:
    print(term, term in source_name)
PY

# (d) confirm this asset's rejected response is saved in my HW2 run
python3 - <<'PY'
import json
p='/Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans-llm/outputs/structured_full_mps/encoder_failures.jsonl'
for line in open(p):
    r=json.loads(line)
    if r['asset_id']=='FI0009003305':
        print(r['error']); print(r['response'])
PY
```

## Agent-prepared evidence (not the personal check)

- `dilara_hw3/outputs/verify_inputs.json` — CSV SHA-256s, protocol hash, 767 prompts,
  520 failures, 480 unique retry prompts, all-failures-have-generation check.
- `dilara_hw3/outputs/smoke_3/retry_audit.jsonl` — record for `FI0009003305`: the
  validation-aware retry also returned `name=["sampoyj"]`, was rejected, and the
  deterministic source-only fallback was used.
- `dilara_hw3/outputs/smoke_3/retry_prompts.jsonl` — the exact retry prompt for this
  asset, containing only the six as-of fields plus validation feedback.
