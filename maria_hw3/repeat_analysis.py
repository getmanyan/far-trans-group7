#!/usr/bin/env python3
"""Why the encoder changes nothing for short histories: repeat purchases and rank of own assets.
  python repeat_analysis.py --course-dir ... --data-dir ... --run-dir outputs/DW
"""
import argparse, csv, gzip, importlib.util, json
from collections import defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
for a in ('--course-dir', '--data-dir', '--run-dir'):
    ap.add_argument(a, type=Path, required=True)
args = ap.parse_args()
spec = importlib.util.spec_from_file_location('st', args.course_dir / 'far-trans' / 'starter.py')
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
assets, profiles, history, truth, end, _ = st.load_data(args.data_dir, '2021-06-01', 30)
lists = defaultdict(dict)
with gzip.open(args.run_dir / 'predictions.csv.gz', 'rt', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        lists[r['user_id']].setdefault(r['method'], []).append(r['ISIN'])
users = (args.run_dir / 'users.txt').read_text().split()
out = {}
for name, lo, hi in (('len_1', 1, 1), ('len_2_3', 2, 3), ('len_4_plus', 4, 10**9)):
    us = [u for u in users if lo <= len(history[u]) <= hi and truth.get(u, set()) & set(assets)]
    rel = [(u, truth[u] & set(assets)) for u in us]
    repeat_items = sum(len(t & set(history[u])) for u, t in rel)
    all_items = sum(len(t) for _, t in rel)
    only_repeat = sum(t <= set(history[u]) for u, t in rel)
    own_in_top = {m: sum(set(history[u]) <= set(lists[u][m][:len(history[u])]) for u in us)
                  for m in ('original_text_cbf', 'llmrec_encoder')}
    new_hits = {m: sum(len((t - set(history[u])) & set(lists[u][m])) for u, t in rel)
                for m in ('original_text_cbf', 'llmrec_encoder', 'latest_buy')}
    out[name] = {'nonempty_users': len(us), 'truth_items': all_items, 'repeat_items': repeat_items,
                 'users_truth_only_repeats': only_repeat,
                 'users_own_assets_fill_top_positions': own_in_top,
                 'new_asset_hits_in_top10': new_hits}
(args.run_dir / 'repeat_analysis.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
