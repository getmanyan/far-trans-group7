"""Failure analysis and paired bootstrap for the retry ablation."""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from retry_encoder import build_views, load_first_pass, read_jsonl, sha256_text

SEED = 20261120
DRAWS = 10000
CUTOFF = '2021-06-01'
HORIZON_DAYS = 30
A = 'structured_encoder_v1'
B = 'structured_retry_once'
C = 'all_fallback_structured'
D = 'original_text_cbf'
BASELINES = ('popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell', D, C)
BOOTSTRAP_PAIRS = ((B, A), (A, C), (B, C), (A, D), (B, D))


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
    overlap = sum(len(set(rankings[treatment][u]) & set(rankings[control][u])) / 10
                  for u in users)
    return {'users': len(users), 'changed_users': changed,
            'mean_top10_overlap': overlap / len(users) if users else 0.0}


def mean_delta(per_user, users, treatment, control):
    by_user = defaultdict(dict)
    for row in per_user:
        by_user[row['user_id']][row['method']] = row['ndcg_at_10']
    return sum(by_user[u][treatment] - by_user[u][control] for u in users) / len(users)


def nonempty_users(per_user):
    return {r['user_id'] for r in per_user if r['relevant_count'] > 0}


def subgroup_users(data_dir, users):
    from hw2 import starter
    assets, profiles, history, truth, end, excluded = starter.load_data(
        Path(data_dir), CUTOFF, HORIZON_DAYS)
    return {u for u in users if 1 <= len(history.get(u, {})) <= 3}, history, truth


def failure_summary(audit_path):
    path = Path(audit_path)
    if not path.exists():
        return {}
    rows = read_jsonl(path)
    prompts = read_jsonl(path.parent / 'retry_prompts.jsonl')
    valid = {r['asset_id'] for r in rows if r['retry_valid']}
    reasons = Counter(r['original_error'] for r in rows)
    return {
        'rejected_assets': len(rows),
        'unique_retry_prompts': len(prompts),
        'retry_valid': len(valid),
        'retry_fallback': len(rows) - len(valid),
        'asset_recovery_rate': len(valid) / len(rows) if rows else 0.0,
        'prompt_recovery_rate': (
            sum(any(a in valid for a in row['asset_ids']) for row in prompts) / len(prompts)
            if prompts else 0.0),
        'reasons': dict(reasons),
        'retry_error_counts': dict(Counter(r['retry_error'] for r in rows if r['retry_error'])),
        'recovery_by_reason': {
            reason: {'total': count,
                     'recovered': sum(1 for r in rows
                                      if r['original_error'] == reason and r['retry_valid']),
                     'rate': sum(1 for r in rows
                                 if r['original_error'] == reason and r['retry_valid']) / count}
            for reason, count in reasons.items()}}


def recommendation_changes(rankings, users, repaired):
    changed = overlap = entered = entered_items = 0
    for uid in users:
        old = rankings[A][uid]
        new = rankings[B][uid]
        changed += old != new
        overlap += len(set(old) & set(new)) / 10
        additions = set(new) - set(old)
        hits = len(additions & repaired)
        if hits:
            entered += 1
            entered_items += hits
    return {'users': len(users), 'changed_users': changed,
            'mean_top10_overlap': overlap / len(users) if users else 0.0,
            'users_with_repaired_asset_entering_top10': entered,
            'repaired_asset_top10_entries': entered_items}


def asset_failure_table(hw2_outputs, retry_views_path, audit_path, rankings,
                        users, history, truth):
    first = load_first_pass(hw2_outputs)
    retry_views = json.loads(Path(retry_views_path).read_text())
    views_a = build_views(first)
    views_b = build_views(first, retry_views)
    audit = {r['asset_id']: r for r in read_jsonl(audit_path)}
    top10_a = {u: set(rankings[A][u]) for u in users}
    top10_b = {u: set(rankings[B][u]) for u in users}
    rows = []
    for aid in sorted(first['sources']):
        token_a = set(views_a[aid]['view'].split())
        token_b = set(views_b[aid]['view'].split())
        union = token_a | token_b
        record = audit.get(aid)
        rows.append({
            'asset_id': aid,
            'prompt_sha256': sha256_text(first['prompts'][aid]),
            'retry_prompt_sha256': (record['retry_prompt_sha256'] if record else ''),
            'attempt1_valid': not first['replay'][aid]['fallback'],
            'attempt1_error': first['replay'][aid]['error'],
            'attempt2_valid': bool(record and record['retry_valid']),
            'attempt2_error': (record['retry_error'] if record and record['retry_error'] else ''),
            'view_source': views_b[aid]['source'],
            'fallback_in_A': views_a[aid]['fallback'],
            'fallback_in_B': views_b[aid]['fallback'],
            'token_jaccard_A_B': len(token_a & token_b) / len(union) if union else 1.0,
            'exposure_history_users': sum(aid in history.get(u, {}) for u in users),
            'exposure_truth_users': sum(aid in truth.get(u, set()) for u in users),
            'exposure_top10_A_users': sum(aid in top10_a[u] for u in users),
            'exposure_top10_B_users': sum(aid in top10_b[u] for u in users),
        })
    buckets = defaultdict(lambda: {'assets': 0, 'recovered': 0, 'exposed_recovered': 0})
    repaired_exposed = 0
    for row in rows:
        bucket = buckets[row['attempt1_error']]
        bucket['assets'] += 1
        if row['attempt2_valid']:
            bucket['recovered'] += 1
            exposed = any(row[k] for k in ('exposure_history_users', 'exposure_truth_users',
                                           'exposure_top10_A_users', 'exposure_top10_B_users'))
            if exposed:
                repaired_exposed += 1
                bucket['exposed_recovered'] += 1
        bucket['recovery_rate'] = bucket['recovered'] / bucket['assets']
    return {'rows': rows,
            'aggregate_by_error': {k: dict(v) for k, v in sorted(
                buckets.items(), key=lambda item: -item[1]['assets'])},
            'recovered_assets': sum(r['attempt2_valid'] for r in rows),
            'recovered_assets_with_any_exposure': repaired_exposed}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--audit', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--hw2-outputs', type=Path)
    p.add_argument('--retry-views', type=Path)
    p.add_argument('--data-dir', type=Path)
    args = p.parse_args()

    per_user, rankings = read_run(args.run)
    users = sorted({row['user_id'] for row in per_user})
    subsets = {'all_users': users}
    nonempty = sorted(nonempty_users(per_user))
    subsets['nonempty_truth_users'] = nonempty
    if args.data_dir:
        subgroup, history, truth = subgroup_users(args.data_dir, users)
        subsets['subgroup_1_3_buys'] = sorted(subgroup)
    else:
        history, truth = {}, {}

    bootstrap = {}
    for label, members in subsets.items():
        for treatment, control in BOOTSTRAP_PAIRS:
            if label == 'subgroup_1_3_buys' and (treatment, control) != (B, A):
                continue
            key = f'{label}:{treatment}_minus_{control}'
            bootstrap[key] = paired_by_method(per_user, members, treatment, control)
            bootstrap[key]['top10'] = top10_change(rankings, members, treatment, control)

    baseline_deltas = {}
    for label, members in subsets.items():
        baseline_deltas[label] = {
            f'{treatment}_minus_{control}': mean_delta(per_user, members, treatment, control)
            for control in BASELINES for treatment in (A, B)}

    repairs = ({r['asset_id'] for r in read_jsonl(args.audit) if r['retry_valid']}
               if args.audit and Path(args.audit).exists() else set())
    report = {
        'seed': SEED, 'draws': DRAWS,
        'runtime_scope': {'cutoff': CUTOFF, 'end_exclusive': '2021-07-01',
                          'horizon_days': HORIZON_DAYS, 'repeat_purchases_allowed': True,
                          'assets': 767, 'candidate_count': 50,
                          'empty_truth_policy': 'zero in all-user mean; nonempty mean also reported',
                          'teaching_settings_not_official_test': True},
        'subset_sizes': {label: len(members) for label, members in subsets.items()},
        'bootstrap': bootstrap,
        'baseline_deltas': baseline_deltas,
        'recommendation_changes': {
            label: recommendation_changes(rankings, members, repairs)
            for label, members in subsets.items()},
        'failures': failure_summary(args.audit) if args.audit else {},
    }
    if args.hw2_outputs and args.retry_views and args.audit and args.data_dir:
        report['asset_failure_analysis'] = asset_failure_table(
            args.hw2_outputs, args.retry_views, args.audit, rankings, users, history, truth)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'subset_sizes': report['subset_sizes'],
                      'primary': bootstrap['all_users:structured_retry_once_minus_structured_encoder_v1'],
                      'recovered_exposed': report.get('asset_failure_analysis', {}).get(
                          'recovered_assets_with_any_exposure')}, indent=2))


if __name__ == '__main__':
    main()
