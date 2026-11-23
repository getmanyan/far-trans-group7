#!/usr/bin/env python3
"""Does the encoder pull in assets whose LLM output has the same *format* (JSON copy vs prose)
as the user's history? Share of JSON-copy assets among top-10 positions, control vs encoder,
split by the history's format. Users with history of one format only.
  python format_shift.py outputs/DW COURSE_PROJECT_DIR DATA_DIR
"""
import csv, gzip, json, sys
from collections import defaultdict
from pathlib import Path
run = Path(sys.argv[1])
fmt = {}
for l in (run / 'paraphrases.jsonl').open(encoding='utf-8'):
    p = json.loads(l); fmt[p['asset_id']] = p['paraphrase'].lstrip().startswith('{')
L = defaultdict(dict)
with gzip.open(run / 'predictions.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        if r['method'] in ('original_text_cbf', 'llmrec_encoder'):
            L[r['user_id']].setdefault(r['method'], []).append(r['ISIN'])
import importlib.util
out = {}
users = (run / 'users.txt').read_text().split()
# purchase history is recomputed with the course starter (argv[2] = course project dir, argv[3] = data dir)
spec = importlib.util.spec_from_file_location('st', sys.argv[2] + '/far-trans/starter.py')
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
_, _, history, _, _, _ = st.load_data(Path(sys.argv[3]), '2021-06-01', 30)
for label, test in (('history_all_json_copy', lambda h: all(fmt[i] for i in h)),
                    ('history_all_prose', lambda h: not any(fmt[i] for i in h))):
    us = [u for u in users if test(history[u])]
    def share(m):
        vals = [sum(fmt[i] for i in L[u][m] if i not in history[u]) /
                max(1, sum(1 for i in L[u][m] if i not in history[u])) for u in us]
        return sum(vals) / len(vals)
    out[label] = {'users': len(us), 'json_copy_share_new_items_control': share('original_text_cbf'),
                  'json_copy_share_new_items_encoder': share('llmrec_encoder')}
out['catalogue_json_copy_share'] = sum(fmt.values()) / len(fmt)
(run / 'format_shift.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
