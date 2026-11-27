"""Failure analysis and paired bootstrap for the retry ablation."""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

SEED = 20261120
DRAWS = 10000


def read_run(run_dir):
    run_dir = Path(run_dir)
    per_user = json.loads((run_dir / 'per_user.json').read_text())
    rankings = defaultdict(dict)
    with (run_dir / 'predictions.csv').open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            rankings[row['method']].setdefault(row['user_id'], []).append(row['ISIN'])
    return per_user, rankings


def paired(values, seed=SEED, draws=DRAWS):
    n = len(values)
    rng = random.Random(seed)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(draws))
    return {'mean': sum(values) / n if n else 0.0,
            'ci_low': means[int(draws * 0.025)] if n else 0.0,
            'ci_high': means[int(draws * 0.975) - 1] if n else 0.0,
            'improved': sum(v > 0 for v in values),
            'worsened': sum(v < 0 for v in values),
            'unchanged': sum(v == 0 for v in values), 'users': n}


def paired_by_method(per_user, users, treatment, control):
    by_user = defaultdict(dict)
    for row in per_user:
        by_user[row['user_id']][row['method']] = row['ndcg_at_10']
    return paired([by_user[u][treatment] - by_user[u][control] for u in users])


def top10_change(rankings, users, treatment, control):
    changed = sum(rankings[treatment][u] != rankings[control][u] for u in users)
    overlap = sum(len(set(rankings[treatment][u]) & set(rankings[control][u])) / 10 for u in users)
    return {'changed_users': changed, 'mean_top10_overlap': overlap / len(users) if users else 0.0}


def failure_summary(audit_path):
    path = Path(audit_path)
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.open(encoding='utf-8') if line.strip()]
    reasons = Counter(row['original_error'] for row in rows)
    return {'rejected_assets': len(rows), 'retry_valid': sum(r['retry_valid'] for r in rows),
            'retry_fallback': sum(not r['retry_valid'] for r in rows),
            'reasons': dict(reasons),
            'recovery_by_reason': {
                reason: {'total': count,
                         'recovered': sum(1 for r in rows
                                          if r['original_error'] == reason and r['retry_valid'])}
                for reason, count in reasons.items()}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--audit', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    per_user, rankings = read_run(args.run)
    users = sorted({row['user_id'] for row in per_user})
    comparisons = {}
    for treatment, control in (('structured_retry_once', 'structured_encoder_v1'),
                               ('structured_encoder_v1', 'all_fallback_structured'),
                               ('structured_retry_once', 'all_fallback_structured'),
                               ('structured_encoder_v1', 'original_text_cbf')):
        if treatment in rankings and control in rankings:
            comparisons[f'{treatment}_minus_{control}'] = paired_by_method(
                per_user, users, treatment, control)
            comparisons[f'{treatment}_minus_{control}']['top10'] = top10_change(
                rankings, users, treatment, control)
    report = {'users': len(users), 'seed': SEED, 'draws': DRAWS,
              'paired': comparisons, 'failures': failure_summary(args.audit)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
