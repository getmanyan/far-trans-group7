#!/usr/bin/env python3
"""HW3 analyses fixed in PROTOCOL.md: subgroups, paired bootstrap, unchanged lists,
and an automatic screen of paraphrase tokens that are absent from the source JSON.

  python analyze_hw3.py outputs/DW
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CONTROL = 'original_text_cbf'
LLM_METHODS = ('llmrec_encoder', 'llmrec_meta_none_only')
GROUP_ORDER = ('all', 'len_1', 'len_2_3', 'len_4_plus', 'meta_none', 'meta_mixed', 'meta_both')
TABLE_METHODS = ('latest_buy', 'popularity', CONTROL) + LLM_METHODS


def mean(values):
    return sum(values) / len(values) if values else float('nan')


def bootstrap(diffs, resamples=2000, seed=42):
    rng = random.Random(seed)
    n = len(diffs)
    stats = sorted(mean([diffs[rng.randrange(n)] for _ in range(n)]) for _ in range(resamples))
    return stats[int(0.025 * resamples)], stats[int(0.975 * resamples) - 1]


def main(run_dir):
    run_dir = Path(run_dir)
    records = json.loads((run_dir / 'per_user.json').read_text(encoding='utf-8'))
    by_user = defaultdict(dict)
    info = {}
    for r in records:
        by_user[r['user_id']][r['method']] = r['ndcg_at_10']
        info[r['user_id']] = r
    lists = defaultdict(dict)
    with (run_dir / 'predictions.csv').open(encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            lists[row['user_id']].setdefault(row['method'], []).append(row['ISIN'])

    def members(group):
        return [u for u in by_user if group == 'all' or group in (info[u]['len_group'], info[u]['meta_group'])]

    out = {'subgroups': {}, 'paired': {}, 'unchanged': {}}
    for group in GROUP_ORDER:
        users = members(group)
        nonempty = [u for u in users if info[u]['relevant_count']]
        out['subgroups'][group] = {
            'users': len(users), 'nonempty': len(nonempty),
            **{m: {'all': mean([by_user[u][m] for u in users]),
                   'nonempty': mean([by_user[u][m] for u in nonempty])} for m in TABLE_METHODS}}
        for m in LLM_METHODS:
            diffs = [by_user[u][m] - by_user[u][CONTROL] for u in users]
            ne_diffs = [by_user[u][m] - by_user[u][CONTROL] for u in nonempty]
            lo, hi = bootstrap(diffs)
            same_list = sum(lists[u][m] == lists[u][CONTROL] for u in users)
            same_set = sum(set(lists[u][m]) == set(lists[u][CONTROL]) for u in users)
            out['paired'][f'{group}/{m}'] = {
                'mean_diff_all': mean(diffs), 'ci95_all': [lo, hi],
                'mean_diff_nonempty': mean(ne_diffs),
                'up': sum(d > 1e-12 for d in diffs), 'down': sum(d < -1e-12 for d in diffs),
                'tied': sum(abs(d) <= 1e-12 for d in diffs),
                'nonempty_up': sum(d > 1e-12 for d in ne_diffs),
                'nonempty_down': sum(d < -1e-12 for d in ne_diffs),
                'identical_top10_order': same_list, 'identical_top10_set': same_set}

    # Paraphrase screen: content tokens in the paraphrase that never occur in the source JSON.
    template = set('the a an is it its this of in on and or with as for to by at its stock bond '
                   'category industry sector market subcategory name unknown not specified '
                   'traded listed under within classified type falls part which that has are '
                   'belongs asset issued from located operates'.split())
    flags, token_counter, paraphrase_words = [], Counter(), []
    for line in (run_dir / 'paraphrases.jsonl').read_text(encoding='utf-8').splitlines():
        p = json.loads(line)
        source = set(re.findall(r'\w+', p['source'].casefold()))
        para = re.findall(r'\w+', p['paraphrase'].casefold())
        paraphrase_words.append(len(p['paraphrase'].split()))
        novel = sorted({t for t in para if t not in source and t not in template and not t.isdigit()})
        token_counter.update(novel)
        if novel:
            flags.append({'asset_id': p['asset_id'], 'meta_state': p['meta_state'], 'novel_tokens': novel,
                          'source': p['source'], 'paraphrase': p['paraphrase']})
    out['paraphrase_screen'] = {
        'assets': len(paraphrase_words), 'flagged_assets': len(flags),
        'flagged_by_meta_state': Counter(f['meta_state'] for f in flags),
        'mean_words': mean(paraphrase_words), 'max_words': max(paraphrase_words),
        'top_novel_tokens': token_counter.most_common(40)}
    (run_dir / 'paraphrase_flags.jsonl').write_text(
        ''.join(json.dumps(f, ensure_ascii=False) + '\n' for f in flags), encoding='utf-8')
    (run_dir / 'analysis.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n',
                                           encoding='utf-8')

    print('group        users  nonempty | ' + ' | '.join(f'{m[:14]:>14s}' for m in TABLE_METHODS))
    for g, v in out['subgroups'].items():
        print(f"{g:12s} {v['users']:6d} {v['nonempty']:8d} | all " +
              ' '.join(f"{v[m]['all']:.4f}" for m in TABLE_METHODS) +
              ' | ne ' + ' '.join(f"{v[m]['nonempty']:.4f}" for m in TABLE_METHODS))
    for k, v in out['paired'].items():
        print(f"{k:34s} d={v['mean_diff_all']:+.4f} CI[{v['ci95_all'][0]:+.4f},{v['ci95_all'][1]:+.4f}] "
              f"d_ne={v['mean_diff_nonempty']:+.4f} up/down/tie={v['up']}/{v['down']}/{v['tied']} "
              f"ne up/down={v['nonempty_up']}/{v['nonempty_down']} same_order={v['identical_top10_order']} "
              f"same_set={v['identical_top10_set']}")
    print(json.dumps(out['paraphrase_screen'], ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
