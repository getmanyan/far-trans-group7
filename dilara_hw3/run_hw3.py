"""HW3 runner: exact replay check, bounded retry inference, and cohort evaluation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from hw2 import data_adapter, encoder, runtime, starter
from retry_encoder import (build_retry_records, build_views, fallback_views, hash_tree,
                           load_first_pass, run_retries)

METHODS = ('structured_encoder_v1', 'structured_retry_once',
           'all_fallback_structured', 'original_text_cbf')


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cohort', choices=['D100', 'DW'], default='D100')
    p.add_argument('--method', choices=['replay_check', 'retry', 'all'], required=True)
    p.add_argument('--data-dir', type=Path, required=True)
    p.add_argument('--hw2-outputs', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--model', default='Qwen/Qwen3-1.7B')
    p.add_argument('--revision', default='70d244cc86ccca08cf5af4e1e306ecf908b1ad5e')
    p.add_argument('--device', choices=['auto', 'cpu', 'mps', 'cuda'], default='mps')
    p.add_argument('--allow-download', action='store_true')
    p.add_argument('--retry-views', type=Path)
    p.add_argument('--asset-ids', type=Path, help='JSON list of exactly three asset IDs for a smoke run')
    return p.parse_args()


def load_bundle(data_dir, limit, cutoff='2021-06-01', horizon_days=30, candidate_count=50):
    """Same starter policy as HW2, with limit=0 meaning all warm users."""
    assets, profiles, history, truth, end, excluded = starter.load_data(
        Path(data_dir), cutoff, horizon_days)
    users = starter.select_users(profiles, history, 'warm', limit, None)
    features = {isin: starter.tokens(asset) for isin, asset in assets.items()}
    pop = starter.popularity_scores(history, assets)
    contexts, baseline = starter.contexts_for(
        users, assets, profiles, history, features, pop, cutoff, candidate_count, False)
    events = starter.scan_recent_events(Path(data_dir), cutoff, assets)
    recent = starter.recency_rankings(contexts, pop, events, k=10)
    for uid in users:
        baseline[uid].update(recent[uid])
    manifest = {
        'teaching_settings_not_official_test': True,
        'cutoff': cutoff, 'end_exclusive': end, 'users': users,
        'repeat_allowed': True, 'candidate_count': candidate_count,
        'empty_truth_policy': 'zero in all-user mean; nonempty mean also reported',
        'excluded_rows': excluded,
        'data_sha256': {name: hashlib.sha256((Path(data_dir) / name).read_bytes()).hexdigest()
                        for name in ('transactions.csv', 'asset_information.csv',
                                     'customer_information.csv', 'close_prices.csv')},
    }
    return starter, assets, history, truth, contexts, baseline, events, pop, manifest


def score_all(bundle, first_pass, views_a, views_b=None, views_c=None,
              method_name='structured_encoder_v1'):
    starter_mod, assets, history, _, contexts, _, _, pop, _ = bundle
    documents = {i: encoder.source_text(assets[i]) for i in sorted(assets)}
    if set(documents) != set(first_pass['sources']):
        raise ValueError('Eligible asset universe differs from saved HW2 universe')
    for aid, source in first_pass['sources'].items():
        if documents[aid] != source:
            raise ValueError(f'{aid}: as-of source text differs from saved HW2 prompt')
    original = encoder.tfidf(documents)
    structured_a = encoder.tfidf({i: views_a[i]['view'] for i in sorted(views_a)})
    combined_a = encoder.combine_structured_view(original, structured_a)
    predictions = encoder.predict(contexts, history, original, combined_a, pop,
                                  method_name=method_name)
    if views_b is not None:
        structured_b = encoder.tfidf({i: views_b[i]['view'] for i in sorted(views_b)})
        combined_b = encoder.combine_structured_view(original, structured_b)
        ranked = encoder.predict(contexts, history, original, combined_b, pop,
                                 method_name='structured_retry_once')
        for uid, methods in ranked.items():
            predictions[uid]['structured_retry_once'] = methods['structured_retry_once']
    if views_c is not None:
        structured_c = encoder.tfidf({i: views_c[i]['view'] for i in sorted(views_c)})
        combined_c = encoder.combine_structured_view(original, structured_c)
        ranked = encoder.predict(contexts, history, original, combined_c, pop,
                                 method_name='all_fallback_structured')
        for uid, methods in ranked.items():
            predictions[uid]['all_fallback_structured'] = methods['all_fallback_structured']
    return predictions


def save(args, bundle, predictions, method, metadata, failures=None):
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if any((out / name).exists() for name in ('metrics.json', 'run_manifest.json', 'predictions.csv')):
        raise ValueError('Output directory already contains results; use a fresh directory')
    data_adapter.save_results(SimpleNamespace(output_dir=out), bundle, predictions,
                              failures or [], method, metadata)


def compare_with_saved(args, out):
    saved = Path(args.hw2_outputs)
    checks = {}
    for name in ('metrics.json', 'predictions.csv', 'per_user.json'):
        expected = (saved / name).read_bytes()
        actual = (Path(out) / name).read_bytes()
        checks[name] = {'exact_bytes': expected == actual,
                        'expected_sha256': hashlib.sha256(expected).hexdigest(),
                        'actual_sha256': hashlib.sha256(actual).hexdigest()}

    def rows(path):
        result = {}
        with Path(path).open(newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream):
                result.setdefault((row['method'], row['user_id']), []).append(row['ISIN'])
        return result

    expected_rows = rows(saved / 'predictions.csv')
    actual_rows = rows(Path(out) / 'predictions.csv')
    differing = {}
    for key in expected_rows:
        if expected_rows[key] != actual_rows[key]:
            differing.setdefault(key[0], []).append(key[1])
    tie_noise = sorted(differing.pop('cbf', []))
    blocking = {method: sorted(users) for method, users in differing.items()}
    report = {'cohort': args.cohort, 'files': checks,
              'metrics_exact': checks['metrics.json']['exact_bytes'],
              'per_user_exact': checks['per_user.json']['exact_bytes'],
              'ranked_ids_differing_users_by_method': blocking,
              'official_cbf_tie_reordering_users': tie_noise,
              'cbf_tie_reordering_note': (
                  'starter.tokens uses set iteration; floating-point summation order can '
                  'flip ties in the official cbf baseline across Python processes'),
              'all_non_cbf_rankings_exact': not blocking,
              'accepted': (checks['metrics.json']['exact_bytes']
                           and checks['per_user.json']['exact_bytes'] and not blocking)}
    (Path(out) / 'replay_comparison.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['accepted']:
        raise ValueError('HW2 replay differs beyond documented cbf tie noise; stop')


def main():
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError('Output directory must be empty or absent')
    before = hash_tree(args.hw2_outputs)
    first_pass = load_first_pass(args.hw2_outputs)
    limit = 100 if args.cohort == 'D100' else 0
    bundle = load_bundle(args.data_dir, limit)
    starter_mod, assets, history, _, contexts, _, _, pop, manifest = bundle
    metadata = {'protocol_hash': '50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417',
                'cohort': args.cohort, 'users': len(manifest['users']),
                'hw2_outputs_sha256': hashlib.sha256(
                    json.dumps(before, sort_keys=True).encode()).hexdigest(),
                'method': args.method,
                'pythonhashseed': os.environ.get('PYTHONHASHSEED', 'unset')}

    if args.method == 'replay_check':
        views = build_views(first_pass)
        predictions = score_all(bundle, first_pass, views,
                                method_name='structured_attribute_encoder')
        save(args, bundle, predictions, 'structured_attribute_encoder', metadata)
        compare_with_saved(args, args.output_dir)

    elif args.method == 'retry':
        records, groups = build_retry_records(first_pass)
        if args.asset_ids:
            selected = json.loads(args.asset_ids.read_text())
            if len(selected) != 3:
                raise ValueError('Smoke runs must use exactly three asset IDs')
            records = [r for r in records if r['asset_id'] in selected]
            if len(records) != 3:
                raise ValueError('Some selected assets were not rejected in HW2')
        else:
            selected = None
        started = time.perf_counter()
        backend = runtime.LocalGenerator(args.model, args.revision, args.device, args.allow_download)
        load_seconds = time.perf_counter() - started
        generator = runtime.LoggedGenerator(backend, args.output_dir)
        result = run_retries(records, groups, generator, args.output_dir, selected)
        result['manifest']['backend_load_seconds'] = load_seconds
        result['manifest']['total_seconds'] = time.perf_counter() - started
        print(json.dumps({'assets': result['manifest']['assets'],
                          'unique_retry_prompts': result['manifest']['unique_retry_prompts'],
                          'valid_retries': sum(a['retry_valid'] for a in result['audit']),
                          'device': backend.device, 'revision': backend.metadata['resolved_revision'],
                          'total_seconds': result['manifest']['total_seconds']}, indent=2))

    elif args.method == 'all':
        if not args.retry_views:
            raise ValueError('--retry-views is required for method all')
        retry_views = json.loads(args.retry_views.read_text())
        views_a = build_views(first_pass)
        views_b = build_views(first_pass, retry_views)
        views_c = fallback_views(first_pass)
        predictions = score_all(bundle, first_pass, views_a, views_b, views_c)
        metadata['retry_views_sha256'] = hashlib.sha256(
            args.retry_views.read_bytes()).hexdigest()
        save(args, bundle, predictions, 'structured_retry_once', metadata)

    after = hash_tree(args.hw2_outputs)
    if before != after:
        raise ValueError('HW2 output directory changed during this run')


if __name__ == '__main__':
    main()
