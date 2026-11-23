#!/usr/bin/env python3
"""Classify users whose nDCG@10 changes (encoder vs control): did the change come from
re-ordering the user's own (repeat) assets, or from new assets entering/moving?
  python change_types.py outputs/DW COURSE_PROJECT_DIR DATA_DIR
"""
import csv, gzip, importlib.util, json, sys
from collections import Counter, defaultdict
from pathlib import Path
run = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('st', sys.argv[2] + '/far-trans/starter.py')
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
assets, _, history, truth, _, _ = st.load_data(Path(sys.argv[3]), '2021-06-01', 30)
L = defaultdict(dict)
with gzip.open(run / 'predictions.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        if r['method'] in ('original_text_cbf', 'llmrec_encoder'):
            L[r['user_id']].setdefault(r['method'], []).append(r['ISIN'])
res = Counter()
for u in (run / 'users.txt').read_text().split():
    t = truth.get(u, set()) & set(assets)
    a, b = (st.ndcg10(L[u][m], t) for m in ('original_text_cbf', 'llmrec_encoder'))
    if abs(a - b) < 1e-12:
        continue
    direction = 'up' if b > a else 'down'
    moved = {i for i in t if (L[u]['original_text_cbf'].index(i) if i in L[u]['original_text_cbf'] else 99)
             != (L[u]['llmrec_encoder'].index(i) if i in L[u]['llmrec_encoder'] else 99)}
    kind = ('repeat_assets_only' if moved <= set(history[u])
            else 'new_assets_only' if not moved & set(history[u]) else 'both')
    res[f'{direction}/{kind}'] += 1
(run / 'change_types.json').write_text(json.dumps(res, indent=1) + '\n')
print(dict(res))
