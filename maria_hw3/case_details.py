#!/usr/bin/env python3
"""Dump history, truth, both top-10 lists (with names and paraphrases) for chosen users.
  python case_details.py --course-dir ... --data-dir ... --run-dir outputs/DW USER [USER...]
"""
import argparse, csv, gzip, importlib.util, json, math
from collections import defaultdict
from pathlib import Path
ap = argparse.ArgumentParser()
for a in ('--course-dir', '--data-dir', '--run-dir'):
    ap.add_argument(a, type=Path, required=True)
ap.add_argument('users', nargs='+')
args = ap.parse_args()
spec = importlib.util.spec_from_file_location('st', args.course_dir / 'far-trans' / 'starter.py')
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
assets, profiles, history, truth, end, _ = st.load_data(args.data_dir, '2021-06-01', 30)
para = {json.loads(l)['asset_id']: json.loads(l) for l in (args.run_dir / 'paraphrases.jsonl').open()}
L = defaultdict(dict)
with gzip.open(args.run_dir / 'predictions.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        if r['user_id'] in args.users:
            L[r['user_id']].setdefault(r['method'], []).append(r['ISIN'])
out = {}
for u in args.users:
    t = sorted(truth.get(u, set()) & set(assets))
    rec = {'history': [{'isin': i, 'buys': n, **para[i]} for i, n in history[u].items()],
           'truth': [{'isin': i, 'name': assets[i]['assetName'], 'in_history': i in history[u]} for i in t],
           'lists': {}}
    for m in ('original_text_cbf', 'llmrec_encoder'):
        rk = L[u][m]
        rec['lists'][m] = [{'rank': k + 1, 'isin': i, 'name': assets[i]['assetName'],
                            'hit': i in t, 'json_copy': para[i]['paraphrase'].lstrip().startswith('{')}
                           for k, i in enumerate(rk)]
        rec[f'ndcg_{m}'] = st.ndcg10(rk, set(t))
    out[u] = rec
print(json.dumps(out, ensure_ascii=False, indent=1))
