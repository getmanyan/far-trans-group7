"""Independently reconstruct binary nDCG from transactions and stored rankings."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hw2', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    data = args.hw2 / 'FAR-Trans'
    manifest = json.loads((args.run / 'run_manifest.json').read_text())
    scores = json.loads((args.run / 'metrics.json').read_text())
    cutoff = manifest['cutoff']
    end = manifest['end_exclusive']
    users = set(manifest['users'])
    with (data / 'asset_information.csv').open(newline='') as file:
        as_of = {row['ISIN'] for row in csv.DictReader(file)
                 if row['timestamp'][:10] < cutoff}
    with (data / 'close_prices.csv').open(newline='') as file:
        eligible = {row['ISIN'] for row in csv.DictReader(file)
                    if row['timestamp'][:10] < cutoff and float(row['closePrice']) > 0
                    and row['ISIN'] in as_of}
    truth = defaultdict(set)
    with (data / 'transactions.csv').open(newline='') as file:
        for row in csv.DictReader(file):
            user = row['customerID']
            if (user in users and row['transactionType'] == 'Buy'
                    and int(row['transactionID']) >= 0 and row['ISIN'] in eligible
                    and cutoff <= row['timestamp'][:10] < end):
                truth[user].add(row['ISIN'])

    ranked = defaultdict(list)
    with (args.run / 'predictions.csv').open(newline='') as file:
        for row in csv.DictReader(file):
            key = (row['method'], row['user_id'])
            ranked[key].append((int(row['rank']), row['ISIN']))

    discount = [1 / math.log2(rank + 1) for rank in range(1, 11)]
    expected_keys = {(method, user) for method in scores for user in users}
    if set(ranked) != expected_keys:
        raise ValueError('Prediction coverage differs from the manifest')
    for method, expected in scores.items():
        all_scores = []
        buyer_scores = []
        for user in manifest['users']:
            rows = sorted(ranked[method, user])
            items = [asset for _, asset in rows]
            if ([rank for rank, _ in rows] != list(range(1, 11))
                    or len(set(items)) != 10 or not set(items) <= eligible):
                raise ValueError(f'Invalid Top-10 in {method}')
            relevant = truth.get(user, set())
            value = 0.0
            if relevant:
                value = sum(d for d, asset in zip(discount, items) if asset in relevant)
                value /= sum(discount[:min(len(relevant), 10)])
                buyer_scores.append(value)
            all_scores.append(value)
        for sample, mean, count in [
                (all_scores, 'ndcg_at_10', 'users'),
                (buyer_scores, 'ndcg_at_10_nonempty', 'nonempty_truth_users')]:
            if len(sample) != expected[count] or not math.isclose(
                    sum(sample) / len(sample), expected[mean], abs_tol=1e-12):
                raise ValueError(f'Independent check failed for {method}, {mean}')
    print(f'Independently verified {len(ranked):,} Top-10 lists, {len(eligible)} eligible '
          f'assets, {len(truth):,} users with purchases and {len(scores)} metric entries.')


if __name__ == '__main__':
    main()
