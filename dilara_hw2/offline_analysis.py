"""Offline ablation, subgroup, and invalid-output audit for the completed run.

This module never imports runtime.py, never constructs a model, and never makes
network calls. It recomputes only deterministic scoring from the saved dataset
and completed run artifacts.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import random
import shutil
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STARTER_PATH = ROOT / 'far-trans/starter.py'
ENCODER_PATH = ROOT / 'encoder.py'
DEFAULT_DATA = ROOT / 'data/FAR-Trans'
DEFAULT_RUN = ROOT / 'outputs/structured_full_mps'
DEFAULT_BASELINE = ROOT / 'outputs/baseline_100'
DEFAULT_OUT = ROOT / 'outputs/offline_analysis'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip()]


def read_rankings(path):
    result = {}
    for row in csv.DictReader(path.open(encoding='utf-8')):
        result.setdefault(row['method'], {}).setdefault(row['user_id'], []).append(row['ISIN'])
    return result


def ranking_metrics(starter, users, truth, rankings):
    rows = []
    for method, by_user in rankings.items():
        for uid in users:
            ranking = by_user[uid]
            relevant = truth.get(uid, set())
            rows.append({'user_id': uid, 'method': method,
                         'relevant_count': len(relevant),
                         'ndcg_at_10': starter.ndcg10(ranking, relevant)})
    metrics = {}
    for method in rankings:
        values = [row['ndcg_at_10'] for row in rows if row['method'] == method]
        nonempty = [row['ndcg_at_10'] for row in rows
                    if row['method'] == method and row['relevant_count']]
        metrics[method] = {
            'users': len(values),
            'nonempty_truth_users': len(nonempty),
            'empty_truth_users': len(values) - len(nonempty),
            'ndcg_at_10': sum(values) / len(values),
            'ndcg_at_10_nonempty': sum(nonempty) / len(nonempty) if nonempty else None,
        }
    return rows, metrics


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_difference(per_user, left, right, users, seed=20261120, draws=10000):
    differences = [per_user[(uid, left)] - per_user[(uid, right)] for uid in users]
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        samples.append(sum(rng.choice(differences) for _ in differences) / len(differences))
    return {
        'n_users': len(users),
        'mean_difference': sum(differences) / len(differences),
        'bootstrap_draws': draws,
        'seed': seed,
        'percentile_2_5': percentile(samples, 0.025),
        'percentile_97_5': percentile(samples, 0.975),
    }


def compare_rankings(rankings, left, right, users):
    overlaps = []
    top1_changed = 0
    changed = 0
    for uid in users:
        a, b = rankings[left][uid], rankings[right][uid]
        overlaps.append(len(set(a) & set(b)) / 10)
        changed += a != b
        top1_changed += a[0] != b[0]
    return {
        'users': len(users),
        'changed_top10_users': changed,
        'changed_top10_fraction': changed / len(users),
        'top1_changed_users': top1_changed,
        'mean_top10_overlap': sum(overlaps) / len(overlaps),
    }


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    run_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_RUN
    baseline_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_BASELINE
    out_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_OUT
    if out_dir.exists():
        raise SystemExit(f'Refusing to overwrite existing analysis directory: {out_dir}')
    required = [run_dir / 'predictions.csv', run_dir / 'per_user.json',
                run_dir / 'encoder_failures.jsonl', run_dir / 'generations.jsonl',
                run_dir / 'protocol.json', baseline_dir / 'protocol.json']
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit('Missing completed-run artifacts: ' + ', '.join(missing))

    starter = load_module('offline_starter', STARTER_PATH)
    encoder = load_module('offline_encoder', ENCODER_PATH)
    assets, profiles, history, truth, end, excluded = starter.load_data(
        data_dir, '2021-06-01', 30)
    users = starter.select_users(profiles, history, 'warm', 100, None)
    if len(users) != 100:
        raise SystemExit(f'Expected 100 users, got {len(users)}')
    baseline_protocol = json.loads((baseline_dir / 'protocol.json').read_text())
    run_protocol = json.loads((run_dir / 'protocol.json').read_text())
    if baseline_protocol['protocol_hash'] != run_protocol['protocol_hash']:
        raise SystemExit('Protocol hash mismatch between completed run and baseline')

    saved = read_rankings(run_dir / 'predictions.csv')
    needed = {'popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell',
              'original_text_cbf', 'structured_attribute_encoder'}
    if not needed <= set(saved):
        raise SystemExit(f'Missing saved methods: {sorted(needed - set(saved))}')

    features = {isin: starter.tokens(row) for isin, row in assets.items()}
    popularity = starter.popularity_scores(history, assets)
    original_docs = {isin: encoder.source_text(row) for isin, row in assets.items()}
    original_vectors = encoder.tfidf(original_docs)
    fallback_docs = {
        isin: encoder.structured_text(encoder.fallback_structured_attributes(text))
        for isin, text in original_docs.items()
    }
    fallback_vectors = encoder.tfidf(fallback_docs)
    fallback_combined = encoder.combine_structured_view(original_vectors, fallback_vectors)
    fallback_rankings = {}
    for uid in users:
        scores = encoder.history_scores(history.get(uid, {}), fallback_combined)
        if not any(scores.values()):
            scores = popularity
        eligible = sorted(assets)
        fallback_rankings[uid] = sorted(eligible,
                                        key=lambda isin: (-scores.get(isin, 0.0), isin))[:10]

    rankings = {name: saved[name] for name in
                ('popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell',
                 'original_text_cbf', 'structured_attribute_encoder')}
    rankings['all_fallback_structured'] = fallback_rankings
    rows, metrics = ranking_metrics(starter, users, truth, rankings)

    out_dir.mkdir(parents=True)
    shutil.copyfile(baseline_dir / 'protocol.json', out_dir / 'protocol.json')
    with (out_dir / 'predictions.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['method', 'user_id', 'rank', 'ISIN'])
        for method in rankings:
            for uid in users:
                writer.writerows((method, uid, rank, isin)
                                 for rank, isin in enumerate(rankings[method][uid], 1))
    (out_dir / 'per_user.json').write_text(json.dumps(rows, indent=2) + '\n')
    (out_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')

    subgroup = [uid for uid in users if 1 <= len(history.get(uid, {})) <= 3]
    subgroup_rows = [row for row in rows if row['user_id'] in subgroup]
    subgroup_metrics = {}
    for method in rankings:
        values = [row['ndcg_at_10'] for row in subgroup_rows if row['method'] == method]
        nonempty = [row['ndcg_at_10'] for row in subgroup_rows
                    if row['method'] == method and row['relevant_count']]
        subgroup_metrics[method] = {
            'users': len(values),
            'nonempty_truth_users': len(nonempty),
            'empty_truth_users': len(values) - len(nonempty),
            'ndcg_at_10': sum(values) / len(values),
            'ndcg_at_10_nonempty': sum(nonempty) / len(nonempty) if nonempty else None,
        }
    per_user_values = {(row['user_id'], row['method']): row['ndcg_at_10'] for row in rows}
    controls = ('original_text_cbf', 'all_fallback_structured', 'cbf', 'popularity')
    bootstrap = {control: bootstrap_difference(
        per_user_values, 'structured_attribute_encoder', control, subgroup)
        for control in controls}
    with (out_dir / 'subgroup_paired_differences.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['user_id', 'distinct_history_assets', 'future_truth_count',
                         'structured_ndcg', 'original_text_cbf_ndcg',
                         'all_fallback_structured_ndcg', 'structured_minus_original',
                         'structured_minus_fallback'])
        for uid in subgroup:
            structured_value = per_user_values[(uid, 'structured_attribute_encoder')]
            original_value = per_user_values[(uid, 'original_text_cbf')]
            fallback_value = per_user_values[(uid, 'all_fallback_structured')]
            writer.writerow([uid, len(history.get(uid, {})), len(truth.get(uid, set())),
                             structured_value, original_value, fallback_value,
                             structured_value - original_value,
                             structured_value - fallback_value])
    (out_dir / 'subgroup_metrics.json').write_text(json.dumps({
        'exploratory': True, 'criterion': '1-3 distinct historical Buy assets before cutoff',
        'metrics': subgroup_metrics, 'paired_bootstrap_differences': bootstrap,
    }, indent=2) + '\n')

    failures = read_jsonl(run_dir / 'encoder_failures.jsonl')
    failure_counts = Counter(row['error'] for row in failures)
    audit = {
        'total_invalid': len(failures),
        'valid_responses': 767 - len(failures),
        'reasons': [
            {'reason': reason, 'count': count, 'percentage': count / len(failures) * 100,
             'examples': [row['response'][:240] for row in failures if row['error'] == reason][:3]}
            for reason, count in failure_counts.most_common()
        ],
        'ranking_changes': {
            'structured_vs_original_text': compare_rankings(
                rankings, 'structured_attribute_encoder', 'original_text_cbf', users),
            'structured_vs_all_fallback': compare_rankings(
                rankings, 'structured_attribute_encoder', 'all_fallback_structured', users),
        },
    }

    summary = {
        'analysis_only': True,
        'model_inference_invoked': False,
        'source_run': str(run_dir),
        'protocol_hash': baseline_protocol['protocol_hash'],
        'cutoff': baseline_protocol['cutoff'],
        'end_exclusive': baseline_protocol['end_exclusive'],
        'users': len(users),
        'nonempty_truth_users': sum(bool(truth.get(uid)) for uid in users),
        'eligible_assets': len(assets),
        'excluded_rows': excluded,
        'methods': metrics,
        'subgroup': {
            'exploratory': True,
            'criterion': '1-3 distinct historical Buy assets before cutoff',
            'users': subgroup,
            'metrics': subgroup_metrics,
            'paired_bootstrap_differences': bootstrap,
        },
        'invalid_audit': audit,
    }
    (out_dir / 'analysis_summary.json').write_text(json.dumps(summary, indent=2,
                                                              ensure_ascii=False) + '\n')
    (out_dir / 'invalid_audit.json').write_text(json.dumps(audit, indent=2,
                                                           ensure_ascii=False) + '\n')
    (out_dir / 'analysis_manifest.json').write_text(json.dumps({
        'model_inference_invoked': False,
        'saved_generations_read': len(read_jsonl(run_dir / 'generations.jsonl')),
        'saved_failures_read': len(failures),
        'protocol_hash': baseline_protocol['protocol_hash'],
        'run_protocol_hash': run_protocol['protocol_hash'],
        'output_dir': str(out_dir),
    }, indent=2) + '\n')
    print(json.dumps({'output_dir': str(out_dir), 'protocol_hash': baseline_protocol['protocol_hash'],
                      'subgroup_users': len(subgroup), 'invalid': len(failures)}, indent=2))


if __name__ == '__main__':
    main()
