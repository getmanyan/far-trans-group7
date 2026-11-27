"""Final offline robustness checks for the completed FAR-Trans Encoder run."""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import random
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'outputs/structured_full_mps'
ABLATION = ROOT / 'outputs/offline_analysis_v2'
DATA = ROOT / 'data/FAR-Trans'
OUT = ROOT / 'outputs/robustness_analysis'
EXPECTED_HASH = '50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417'
SEED = 20261120
DRAW_COUNT = 10_000


def load_starter():
    path = ROOT / 'far-trans/starter.py'
    spec = importlib.util.spec_from_file_location('robustness_starter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap(differences):
    rng = random.Random(SEED)
    samples = []
    for _ in range(DRAW_COUNT):
        samples.append(sum(rng.choice(differences) for _ in differences) / len(differences))
    return {
        'draws': DRAW_COUNT,
        'seed': SEED,
        'percentile_2_5': percentile(samples, 0.025),
        'percentile_97_5': percentile(samples, 0.975),
    }


def read_per_user(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_predictions(path):
    result = {}
    for row in csv.DictReader(path.open(encoding='utf-8')):
        result.setdefault(row['method'], {}).setdefault(row['user_id'], []).append(row['ISIN'])
    return result


def paired(records, users, treatment, control):
    values = {(row['user_id'], row['method']): row['ndcg_at_10'] for row in records}
    differences = [values[(uid, treatment)] - values[(uid, control)] for uid in users]
    improved = sum(value > 0 for value in differences)
    worsened = sum(value < 0 for value in differences)
    unchanged = sum(value == 0 for value in differences)
    assert improved + worsened + unchanged == len(users)
    result = {
        'treatment': treatment,
        'control': control,
        'n_users': len(users),
        'mean_paired_difference': sum(differences) / len(differences),
        'improved_users': improved,
        'worsened_users': worsened,
        'unchanged_users': unchanged,
        'bootstrap': bootstrap(differences),
    }
    return result, differences


def leakage_check(prompt_path, cutoff, asof_assets):
    records = [json.loads(line) for line in prompt_path.read_text(encoding='utf-8').splitlines()
               if line.strip()]
    forbidden = ('2021-07', 'transactionID', 'transactionType', 'closePrice', 'truth', 'ISIN')
    forbidden_counts = {term: sum(term in row['prompt'] for row in records) for term in forbidden}
    source_keys = []
    for row in records:
        source = json.loads(row['prompt'].split('Source: ', 1)[1])
        source_keys.append(sorted(source))
        asset = asof_assets[row['asset_id']]
        expected_source = {
            'name': asset.get('assetName', '').strip(),
            'category': asset.get('assetCategory', '').strip(),
            'subcategory': asset.get('assetSubCategory', '').strip(),
            'sector': asset.get('sector', '').strip(),
            'industry': asset.get('industry', '').strip(),
            'market': asset.get('marketID', '').strip(),
        }
        expected_source = {key: (value if value not in ('', 'Not_Available', 'nan')
                                 else 'unknown')
                           for key, value in expected_source.items()}
        assert source == expected_source
    expected = sorted(('name', 'category', 'subcategory', 'sector', 'industry', 'market'))
    assert all(keys == expected for keys in source_keys)
    assert all(count == 0 for count in forbidden_counts.values())
    return {
        'prompt_records': len(records),
        'allowlisted_source_keys': expected,
        'forbidden_term_counts': forbidden_counts,
        'all_source_rows_match_latest_metadata_strictly_before_cutoff': True,
        'cutoff': cutoff,
    }


def main():
    if OUT.exists() and not (OUT / 'analysis_manifest.json').is_file():
        raise SystemExit(f'Refusing to use non-analysis output directory: {OUT}')
    for required in (RUN / 'per_user.json', RUN / 'predictions.csv', RUN / 'protocol.json',
                     RUN / 'structured_attribute_prompts.jsonl',
                     ABLATION / 'per_user.json', ABLATION / 'protocol.json'):
        if not required.is_file():
            raise SystemExit(f'Missing required artifact: {required}')

    run_protocol = json.loads((RUN / 'protocol.json').read_text())
    ablation_protocol = json.loads((ABLATION / 'protocol.json').read_text())
    assert run_protocol['protocol_hash'] == EXPECTED_HASH
    assert ablation_protocol['protocol_hash'] == EXPECTED_HASH
    assert run_protocol['protocol_hash'] == ablation_protocol['protocol_hash']
    assert run_protocol['cutoff'] == '2021-06-01'
    assert run_protocol['end_exclusive'] == '2021-07-01'
    assert len(run_protocol['users']) == 100

    starter = load_starter()
    assets, profiles, history, truth, end, excluded = starter.load_data(DATA, '2021-06-01', 30)
    users = starter.select_users(profiles, history, 'warm', 100, None)
    assert users == run_protocol['users']
    assert len(assets) == 767
    assert end == '2021-07-01'

    records = read_per_user(ABLATION / 'per_user.json')
    source_records = read_per_user(RUN / 'per_user.json')
    source_map = {(row['user_id'], row['method']): row['ndcg_at_10'] for row in source_records}
    for row in records:
        if row['method'] in {'structured_attribute_encoder', 'original_text_cbf', 'popularity'}:
            assert row['ndcg_at_10'] == source_map[(row['user_id'], row['method'])]
    methods = {row['method'] for row in records}
    required_methods = {'structured_attribute_encoder', 'all_fallback_structured',
                        'original_text_cbf', 'popularity'}
    assert required_methods <= methods

    comparisons = []
    differences = {}
    controls = ('all_fallback_structured', 'original_text_cbf', 'popularity')
    nonempty_users = [uid for uid in users if truth.get(uid)]
    for sample_name, sample_users in (('all_100_users', users),
                                      ('nonempty_truth_11_users', nonempty_users)):
        assert len(sample_users) == (100 if sample_name == 'all_100_users' else 11)
        for control in controls:
            result, values = paired(records, sample_users,
                                    'structured_attribute_encoder', control)
            result['sample'] = sample_name
            comparisons.append(result)
            differences[(sample_name, control)] = values

    predictions = read_predictions(ABLATION / 'predictions.csv')
    candidate_users = sorted(
        uid for uid in nonempty_users
        if source_map[(uid, 'structured_attribute_encoder')] > 0
    )
    if not candidate_users:
        raise SystemExit('No suitable manual-verification user found')
    selected_uid = min(
        candidate_users,
        key=lambda uid: (len(truth[uid]),
                         -source_map[(uid, 'structured_attribute_encoder')], uid),
    )
    ranking = predictions['structured_attribute_encoder'][selected_uid]
    relevant = sorted(truth[selected_uid] & set(assets))
    relevant_positions = []
    dcg_terms = []
    for rank, isin in enumerate(ranking, 1):
        if isin in relevant:
            contribution = 1 / math.log2(rank + 1)
            relevant_positions.append({'rank': rank, 'asset_id': isin,
                                       'contribution': contribution})
            dcg_terms.append(contribution)
    ideal_dcg = sum(1 / math.log2(rank + 1)
                    for rank in range(1, min(10, len(relevant)) + 1))
    dcg = sum(dcg_terms)
    verification = {
        'internal_user_id': selected_uid,
        'selection_rule': 'fewest relevant assets, then highest positive structured nDCG, then user ID',
        'relevant_asset_ids': relevant,
        'ranked_top_10_asset_ids': ranking,
        'relevant_positions': relevant_positions,
        'dcg': dcg,
        'ideal_dcg_at_10': ideal_dcg,
        'ndcg_computation': f'{dcg:.16f} / {ideal_dcg:.16f} = {dcg / ideal_dcg:.16f}',
        'saved_per_user_result': next(row for row in records
                                      if row['user_id'] == selected_uid
                                      and row['method'] == 'structured_attribute_encoder'),
    }
    assert verification['saved_per_user_result']['ndcg_at_10'] == dcg / ideal_dcg

    leakage = leakage_check(RUN / 'structured_attribute_prompts.jsonl', '2021-06-01', assets)
    out = OUT
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ABLATION / 'protocol.json', out / 'protocol.json')
    (out / 'paired_robustness.json').write_text(json.dumps({
        'protocol_hash': EXPECTED_HASH, 'comparisons': comparisons,
        'excluded_rows': excluded,
    }, indent=2) + '\n')
    with (out / 'paired_robustness.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['sample', 'control', 'n_users', 'mean_paired_difference',
                  'improved_users', 'worsened_users', 'unchanged_users',
                  'bootstrap_low', 'bootstrap_high']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in comparisons:
            writer.writerow({
                'sample': row['sample'], 'control': row['control'],
                'n_users': row['n_users'],
                'mean_paired_difference': row['mean_paired_difference'],
                'improved_users': row['improved_users'],
                'worsened_users': row['worsened_users'],
                'unchanged_users': row['unchanged_users'],
                'bootstrap_low': row['bootstrap']['percentile_2_5'],
                'bootstrap_high': row['bootstrap']['percentile_97_5'],
            })
    (out / 'manual_verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    worksheet = [
        '# Manual Verification Worksheet', '',
        f'- Protocol hash: `{EXPECTED_HASH}`',
        f'- Internal evaluation user ID: `{selected_uid}`',
        '- This is a real user from the fixed 100-user evaluation cohort.', '',
        '## Relevant Assets',
        *[f'- `{isin}`' for isin in relevant], '',
        '## Structured Encoder Top 10',
        *[f'{rank}. `{isin}`' for rank, isin in enumerate(ranking, 1)], '',
        '## Relevant Positions and DCG Contributions',
        *[f'- Rank {item["rank"]}, `{item["asset_id"]}`: '
          f'`1/log2({item["rank"]}+1) = {item["contribution"]:.16f}`'
          for item in relevant_positions], '',
        f'- DCG@10 = `{dcg:.16f}`',
        f'- Ideal DCG@10 = `{ideal_dcg:.16f}`',
        f'- nDCG@10 = `{dcg:.16f} / {ideal_dcg:.16f} = {dcg / ideal_dcg:.16f}`',
        f'- Saved per-user nDCG@10: `{verification["saved_per_user_result"]["ndcg_at_10"]:.16f}`',
    ]
    (out / 'manual_verification.md').write_text('\n'.join(worksheet) + '\n')
    (out / 'leakage_check.json').write_text(json.dumps(leakage, indent=2) + '\n')
    (out / 'analysis_manifest.json').write_text(json.dumps({
        'analysis_only': True, 'model_inference_invoked': False,
        'network_access_requested': False, 'python_version': __import__('sys').version,
        'source_files': [str(RUN / 'per_user.json'), str(RUN / 'predictions.csv'),
                         str(RUN / 'protocol.json'), str(ABLATION / 'per_user.json'),
                         str(ABLATION / 'predictions.csv'), str(ABLATION / 'protocol.json'),
                         str(RUN / 'structured_attribute_prompts.jsonl'),
                         str(DATA / 'transactions.csv'), str(DATA / 'asset_information.csv'),
                         str(DATA / 'customer_information.csv'), str(DATA / 'close_prices.csv')],
        'protocol_hash': EXPECTED_HASH, 'seed': SEED, 'bootstrap_draws': DRAW_COUNT,
        'output_dir': str(out), 'manual_user_id': selected_uid,
    }, indent=2) + '\n')
    print(json.dumps({'output_dir': str(out), 'protocol_hash': EXPECTED_HASH,
                      'all_users': len(users), 'nonempty_users': len(nonempty_users),
                      'manual_user_id': selected_uid}, indent=2))


if __name__ == '__main__':
    main()
