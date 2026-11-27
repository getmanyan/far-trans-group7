# C2 — manual verification of a FAR-Trans record and temporal assumption

STATUS: **NOT VERIFIED — Dilara must execute and confirm.**

Target record: `ISIN=FI0009003305` (`Sampo Oyj`). Its HW2 first response was rejected
with `name contains a term not supported by its source field` because the model emitted
`name: ["sampoyj"]` while the source name contains a space.

## Task

Check one real CSV row and the temporal assumption used by the starter.

## Commands to execute

```bash
cd /Users/dafaritova/Downloads/FAR-Trans

# (a) exact row in the original asset file
python3 - <<'PY'
import csv
with open('asset_information.csv', newline='', encoding='utf-8') as f:
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

## Fill in after execution

- Verbatim CSV row observed: ____________________________________
- Is the metadata timestamp strictly before `2021-06-01`? _______
- Which terms are substrings of the casefolded source name? _____
- Exact validator error recorded in my HW2 run: _________________
- Does this support the retry hypothesis (a fixable formatting error)? ______
- Executed by: Dilara Faritova
- Date: __________

Agent-prepared expectations (to be checked, not copied as your own observation): row
`FI0009003305, Sampo Oyj, UNK_93, Stock, , XHEL, Financial Services,
Insurance - Diversified, 2018-01-02`; `sampoyj in "sampo oyj"` is False, `sampo` is True.
