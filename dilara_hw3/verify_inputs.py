"""CPU-only preflight checks; writes raw evidence, never changes any input file."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from hw2 import starter
from retry_encoder import build_retry_records, hash_tree, load_first_pass, read_jsonl
from run_hw3 import load_bundle

EXPECTED_DATA = {
    'transactions.csv': '358871fa1311a802799df86e56c3d633513566965b01412d058e0f8fbe6cd54b',
    'asset_information.csv': '33f9897b14087068fba53a0bc9e24a0031b096bd3ad3e977e534153f29b7a590',
    'customer_information.csv': 'c4ad52ebca90e32bf3df5eb64f362b7a3437b77d978b22627cc46927fe7064af',
    'close_prices.csv': '6ba1fe8390b31dfb3ab4e3e824910f9e8da4684cb6074cdb82eb6422a323656d',
}
PROTOCOL_HASH = '50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir', type=Path, required=True)
    p.add_argument('--hw2-outputs', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path('outputs/verify_inputs.json'))
    args = p.parse_args()

    before = hash_tree(args.hw2_outputs)
    data_hashes = {name: hashlib.sha256((args.data_dir / name).read_bytes()).hexdigest()
                   for name in EXPECTED_DATA}
    protocol = json.loads((args.hw2_outputs / 'protocol.json').read_text())
    first_pass = load_first_pass(args.hw2_outputs)
    bundle_d100 = load_bundle(args.data_dir, 100)
    bundle_dw = load_bundle(args.data_dir, 0)
    d100 = bundle_d100[-1]['users']
    dw = bundle_dw[-1]['users']
    truth = bundle_dw[3]
    history = bundle_dw[2]

    failed = sorted(first_pass['failures'])
    replay_failed = sorted(a for a, r in first_pass['replay'].items() if r['fallback'])
    retry_records, retry_groups = build_retry_records(first_pass)
    report = {
        'data_sha256': {k: {'expected': v, 'actual': data_hashes[k],
                            'match': data_hashes[k] == v} for k, v in EXPECTED_DATA.items()},
        'protocol_hash': {'expected': PROTOCOL_HASH,
                          'actual': protocol.get('protocol_hash'),
                          'match': protocol.get('protocol_hash') == PROTOCOL_HASH},
        'cutoff': protocol.get('cutoff'), 'end_exclusive': protocol.get('end_exclusive'),
        'assets': len(protocol.get('eligible_assets', [])),
        'prompts': len(first_pass['prompts']),
        'generation_rows': len(read_jsonl(args.hw2_outputs / 'generations.jsonl')),
        'unique_prompts': len(set(first_pass['prompts'].values())),
        'failures': len(failed), 'replay_failures': len(replay_failed),
        'failure_sets_match': failed == replay_failed,
        'all_failed_have_generation': all(a in first_pass['attempt1'] for a in failed),
        'rejected_assets': len(retry_records),
        'unique_retry_prompts': len(retry_groups),
        'd100_users': len(d100), 'dw_users': len(dw),
        'd100_is_prefix_of_dw': d100 == dw[:100],
        'dw_nonempty_truth': sum(1 for uid in dw if truth.get(uid)),
        'subgroup_dw_1_3_buys': sum(1 for uid in dw if 1 <= len(history.get(uid, {})) <= 3),
        'subgroup_d100_1_3_buys': sum(1 for uid in d100 if 1 <= len(history.get(uid, {})) <= 3),
        'hw2_outputs_unchanged': before == hash_tree(args.hw2_outputs),
    }
    ok = (all(v['match'] for v in report['data_sha256'].values())
          and report['protocol_hash']['match']
          and report['assets'] == 767 and report['prompts'] == 767
          and report['failures'] == 520 and report['replay_failures'] == 520
          and report['failure_sets_match'] and report['all_failed_have_generation']
          and report['rejected_assets'] == 520 and report['unique_retry_prompts'] == 480
          and report['d100_users'] == 100 and report['dw_users'] == 10404
          and report['d100_is_prefix_of_dw'] and report['dw_nonempty_truth'] == 1178
          and report['subgroup_dw_1_3_buys'] == 7360
          and report['subgroup_d100_1_3_buys'] == 63
          and report['hw2_outputs_unchanged'])
    report['all_checks_pass'] = bool(ok)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not ok:
        raise ValueError('Preflight checks failed; stop before any inference')


if __name__ == '__main__':
    main()
