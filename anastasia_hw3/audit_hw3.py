"""Audit cached prompt inputs and split nDCG contributions by purchase novelty."""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def jsonl(path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hw2', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    course = args.hw2 / 'RecSys-LLMs/project'
    sys.path[:0] = [str(course / 'far-trans'), str(course / 'far-trans-llm'),
                    str(args.hw2 / 'getman/hw2')]
    from attribute_encoder import SCHEMA, attribute_prompt
    from encoder import source_text
    from starter import load_data

    run = json.loads((args.run / 'run_manifest.json').read_text())
    cutoff = run['cutoff']
    manifest_metrics = json.loads((args.run / 'metrics.json').read_text())
    horizon = date.fromisoformat
    assets, _, history, truth, end, excluded = load_data(
        args.hw2 / 'FAR-Trans', cutoff, (horizon(run['end_exclusive']) - horizon(cutoff)).days)
    if end != run['end_exclusive'] or excluded != run['excluded_rows']:
        raise ValueError('Mismatched data protocol')
    saved = args.hw2 / 'outputs/attr_encoder'
    prompts = list(jsonl(saved / 'attribute_prompts.jsonl'))
    attributes = list(jsonl(saved / 'asset_attributes.jsonl'))
    for records in (prompts, attributes):
        if len(records) != len(assets) or {r['asset_id'] for r in records} != set(assets):
            raise ValueError('Saved input does not cover eligible assets')
    for item in prompts:
        asset = assets[item['asset_id']]
        if asset['timestamp'][:10] >= cutoff or item['prompt'] != attribute_prompt(source_text(asset)):
            raise ValueError('Prompt differs from expected as-of inputs')
    coverage = {}
    for field in SCHEMA:
        llm = [row['llm'][field] for row in attributes]
        rules = [row['rules'][field] for row in attributes]
        both = [(a, b) for a, b in zip(llm, rules) if a != 'unknown' and b != 'unknown']
        coverage[field] = {
            'llm_known': sum(a != 'unknown' for a in llm),
            'rules_known': sum(b != 'unknown' for b in rules),
            'both_known': len(both),
            'agree': sum(a == b for a, b in both),
        }
    repeat, new = {}, {}
    for user in run['users']:
        relevant = truth.get(user, set())
        if relevant:
            repeat[user] = relevant.intersection(history[user])
            new[user] = relevant - repeat[user]
    discount = [1 / math.log2(i + 2) for i in range(10)]
    denominators = {user: sum(discount[:min(len(truth[user]), 10)]) for user in repeat}
    sums = defaultdict(lambda: [0., 0.])
    with (args.run / 'predictions.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            user, asset = row['user_id'], row['ISIN']
            if user not in denominators:
                continue
            value = discount[int(row['rank']) - 1] / denominators[user]
            if asset in repeat[user]:
                sums[row['method']][0] += value
            elif asset in new[user]:
                sums[row['method']][1] += value
    means = {}
    for method, row in manifest_metrics.items():
        a, b = (value / len(denominators) for value in sums[method])
        if not math.isclose(a + b, row['ndcg_at_10_nonempty'], abs_tol=1e-12):
            raise ValueError(f'Decomposition does not reproduce {method}')
        means[method] = {'repeat': a, 'new_to_user': b}
    audit = {
        'prompt_count_verified': len(prompts),
        'source_fields': sorted(json.loads(source_text(next(iter(assets.values()))))),
        'attribute_coverage': coverage,
        'distinct_llm_label_sets': len({tuple(row['llm'][key] for key in SCHEMA) for row in attributes}),
        'distinct_rule_label_sets': len({tuple(row['rules'][key] for key in SCHEMA) for row in attributes}),
        'purchase_counts': {
            'repeat_pairs': sum(map(len, repeat.values())), 'new_to_user_pairs': sum(map(len, new.values())),
            'repeat_only_buyers': sum(not items for items in new.values()),
            'new_only_buyers': sum(not items for items in repeat.values()),
            'both_buyers': sum(bool(repeat[user] and new[user]) for user in repeat),
        },
        'buyers_mean_ndcg_contributions': means,
    }
    args.out.write_text(json.dumps(audit, indent=2) + '\n')
    print(f"Verified {len(prompts)} exact as-of prompts and additive nDCG for {len(means)} methods.")


if __name__ == '__main__':
    main()
