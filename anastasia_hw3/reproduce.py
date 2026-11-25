"""Replay FAR-Trans HW2 and evaluate a weak attribute view without model inference."""
import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hw2', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--cohort', choices=('D100', 'DW'), default='D100')
    args = parser.parse_args()
    root = args.hw2.resolve()
    out = args.out.resolve()
    course = root / 'RecSys-LLMs/project'
    saved = root / 'outputs/attr_encoder'
    inputs = [saved / name for name in ('asset_attributes.jsonl', 'encoder_failures.jsonl',
                                       'run_manifest.json', 'predictions.csv', 'metrics.json')]
    sys.path[:0] = [str(root / 'getman/hw2'), str(course / 'far-trans-llm')]
    from attribute_encoder import attribute_text, predict, rule_attributes
    from data_adapter import arguments, load, save_results
    from encoder import combine_views, history_scores, source_text, tfidf

    old = json.loads(inputs[2].read_text())
    settings = arguments(__doc__).parse_args([
        '--data-dir', str(root / 'FAR-Trans'), '--output-dir', str(out),
        '--cutoff', old['cutoff'], '--candidate-count', str(old['candidate_count']),
        '--model', 'Qwen/Qwen3-1.7B', '--on-invalid', 'fallback',
        '--max-users', str(len(old['users']) if args.cohort == 'D100' else sys.maxsize),
    ])
    begin = time.perf_counter()
    bundle = load(settings)
    starter, assets, history, truth, contexts, _, _, popularity, manifest = bundle
    for key, value in manifest.items():
        reference = value[:len(old['users'])] if key == 'users' else value
        if old.get(key) != reference:
            raise ValueError(f'HW2 protocol mismatch for {key}')
    loaded = time.perf_counter()
    assets_used = sorted({asset for context in contexts.values()
                          for asset in context['eligible_asset_ids']})
    documents = {asset: source_text(assets[asset]) for asset in assets_used}
    records = read_jsonl(inputs[0])
    cached = {record['asset_id']: record for record in records}
    if set(cached) != set(documents) or len(cached) != len(records):
        raise ValueError('Cached assets do not match the evaluation universe')
    for asset, document in documents.items():
        source = json.loads(document)
        if cached[asset]['source'] != source or cached[asset]['rules'] != rule_attributes(source):
            raise ValueError(f'Metadata or rule mismatch for {asset}')
    failures = read_jsonl(inputs[1])
    failed = {item['asset_id'] for item in failures}
    llm_text = {asset: attribute_text(cached[asset]['llm']) for asset in assets_used}
    if not failed <= set(cached) or any(llm_text[asset] for asset in failed):
        raise ValueError('Invalid generations must have empty attribute views')
    raw = tfidf(documents)
    llm = tfidf(llm_text)
    rules = tfidf({asset: attribute_text(cached[asset]['rules']) for asset in assets_used})

    def weak(attributes):
        # TF-IDF views are already normalized. Keep their prefixes disjoint.
        from encoder import _normalize
        return {
            asset: _normalize({
                **{f'original:{token}': value for token, value in raw[asset].items()},
                **{f'generated:{token}': .25 * value for token, value in attributes[asset].items()},
            })
            for asset in assets_used
        }

    views = {
        'original_text_cbf': raw,
        'rule_attr_encoder': combine_views(raw, rules),
        'llm_attr_encoder': combine_views(raw, llm),
        'llm_attr_only': llm,
        'rule_attr_w025': weak(rules),
        'llm_attr_w025': weak(llm),
    }
    if args.cohort == 'DW':
        repaired = tfidf({asset: attribute_text(cached[asset]['rules'])
                          if asset in failed else llm_text[asset] for asset in assets_used})
        views['llm_w025_rule_fallback'] = weak(repaired)
    rankings = predict(contexts, history, views, popularity, history_scores)
    scored = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    save_results(settings, bundle, rankings, [], 'attribute_weight_replay', {
        'protocol_load_seconds': loaded - begin,
        'vectorization_and_scoring_seconds': scored - loaded,
        'original_generation_settings': old['runtime'],
        'reused_invalid_outputs': len(failures),
        'new_inference_calls': 0,
        'input_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in inputs},
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })

    reference_users = set(old['users'])

    def prediction_rows(path, allowed):
        with path.open(newline='') as file:
            return {(row['method'], row['user_id'], int(row['rank']), row['ISIN'])
                    for row in csv.DictReader(file) if row['method'] in allowed and row['user_id'] in reference_users}

    original_metrics = json.loads(inputs[4].read_text())
    metrics = json.loads((out / 'metrics.json').read_text())
    actual_rows = prediction_rows(out / 'predictions.csv', original_metrics)
    if actual_rows != prediction_rows(inputs[3], original_metrics):
        raise ValueError('HW2 ranking replay differs')
    selected_records = json.loads((out / 'per_user.json').read_text())
    for name in original_metrics:
        slice_records = [row for row in selected_records if row['method'] == name
                         and row['user_id'] in reference_users]
        if starter.aggregate(slice_records) != original_metrics[name]:
            raise ValueError(f'HW2 metric replay differs for {name}')
    if args.cohort == 'D100' and any(metrics[name] != row for name, row in original_metrics.items()):
        raise ValueError('HW2 metric replay differs')

    cases = []
    failed_counts = Counter()
    for index, (user, context) in enumerate(contexts.items(), 1):
        relevant = truth.get(user, set()) & set(context['eligible_asset_ids'])
        if not relevant:
            continue
        failed_counts['labeled_history'] += bool(failed.intersection(history[user]))
        failed_counts['labeled_truth'] += bool(failed & relevant)
        lists = rankings[user]
        scores = {name: starter.ndcg10(ranking, relevant) for name, ranking in lists.items()}
        if len(set(scores.values())) == 1:
            continue
        if args.cohort == 'DW':
            continue
        cases.append({
            'sample_index': index, 'relevant_count': len(relevant),
            'relevant_ranks': {
                name: sorted(rank for rank, asset in enumerate(ranking, 1) if asset in relevant)
                for name, ranking in lists.items()
            },
            'ndcg': scores,
            'failed_assets_in_history': len(failed.intersection(history[user])),
            'failed_assets_in_truth': len(failed & relevant),
        })
    summary = {
        'verified_hw2_prediction_rows': len(actual_rows),
        'verified_hw2_metric_tables': len(original_metrics),
        'eligible_assets': len(assets_used),
        'validation_errors': dict(Counter(record['error'] for record in failures)),
        'users_with_failed_assets': dict(failed_counts),
        'cases': cases,
    }
    (out / 'checks.json').write_text(json.dumps(summary, indent=2) + '\n')
    if args.cohort == 'DW':
        analyze_full(out, manifest['users'], selected_records, rankings, history, truth, failed)
    print(f"Verified {len(actual_rows)} HW2 ranking rows and {len(original_metrics)} metric entries.")


def analyze_full(out, users, records, rankings, history, truth, failed):
    method = 'llm_attr_w025'
    comparisons = ('rule_attr_w025', 'original_text_cbf', 'llm_attr_encoder',
                   'llm_w025_rule_fallback')
    scores = {(row['user_id'], row['method']): row['ndcg_at_10'] for row in records}
    buyers = {row['user_id'] for row in records if row['relevant_count']}
    indices = {user: index for index, user in enumerate(users)}
    subgroup = {
        '1': [u for u in users if len(history[u]) == 1],
        '2-3': [u for u in users if 2 <= len(history[u]) <= 3],
        '4+': [u for u in users if len(history[u]) >= 4],
    }

    def paired(users_in_group, control):
        delta = [scores[u, method] - scores[u, control] for u in users_in_group]
        return dict(n=len(delta), delta=sum(delta) / len(delta) if delta else None,
                    improved=sum(x > 0 for x in delta), worsened=sum(x < 0 for x in delta),
                    equal=delta.count(0))

    deltas = [[scores[u, method] - scores[u, c] for u in users] for c in comparisons]
    rng = random.Random(42)
    samples = [[] for _ in comparisons]
    population = range(len(users))
    for _ in range(2000):
        draw = rng.choices(population, k=len(users))
        for values, output in zip(deltas, samples):
            output.append(sum(values[i] for i in draw) / len(draw))
    pairs = {}
    examples = {}
    for control, sample in zip(comparisons, samples):
        sample.sort()
        pairs[control] = {
            'all': paired(users, control),
            'buyers': paired([u for u in users if u in buyers], control),
            'bootstrap95_all': [sample[49], sample[1949]],
            'identical_top10': sum(rankings[u][method] == rankings[u][control] for u in users),
        }
        examples[control] = []
        for sign in (1, -1):
            changed = [u for u in users if sign * (scores[u, method] - scores[u, control]) > 0]
            if not changed:
                continue
            user = max(changed, key=lambda u: sign * (scores[u, method] - scores[u, control]))
            examples[control].append({
                'sample_index': indices[user] + 1,
                'history_assets': len(history[user]),
                'relevant_count': len(truth[user]),
                'hits': {name: [i for i, asset in enumerate(rankings[user][name], 1)
                                if asset in truth[user]] for name in (control, method)},
                'ndcg': {name: scores[user, name] for name in (control, method)},
            })
    summary = {
        'comparison_method': method,
        'comparisons': pairs,
        'by_distinct_history': {
            label: {c: {'all': paired(group, c),
                        'buyers': paired([u for u in group if u in buyers], c)}
                    for c in comparisons[:2]} for label, group in subgroup.items()
        },
        'fallback_exposure': {
            group: {'history': sum(bool(failed.intersection(history[u])) for u in members),
                    'truth': sum(bool(failed.intersection(truth.get(u, set()))) for u in members),
                    'top10': sum(bool(failed.intersection(rankings[u][method])) for u in members)}
            for group, members in [('all', users), ('buyers', buyers)]
        },
        'cases': examples,
    }
    (out / 'paired_analysis.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
