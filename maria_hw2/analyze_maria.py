"""
Subgroup Analysis for Maria's HW2 Experiment.
Uses official starter.load_data, validates per_user.json format, and performs strict data leakage checks.
"""
import argparse
import json
import sys
import pandas as pd
from pathlib import Path

def get_missing_state(val):
    if val is None:
        return True
    v = str(val).strip().lower()
    return v in ('', 'not_available', 'nan', 'unknown')

def load_course_data(data_dir, course_dir, cutoff):
    """Wrapper to allow mocking in tests."""
    sys.path.insert(0, str(Path(course_dir) / 'far-trans'))
    from starter import load_data as official_load_data
    return official_load_data(Path(data_dir), cutoff, 30)

def load_encoder_module(course_dir):
    """Load official encoder module for prompt reconstruction."""
    sys.path.insert(0, str(Path(course_dir) / 'far-trans-llm'))
    import encoder
    return encoder

def check_data_leakage(run_dir, course_dir, assets, cutoff_str):
    """Strict data leakage check: prompt reconstruction, timestamp validation, no duplicates."""
    encoder = load_encoder_module(course_dir)
    cutoff_dt = pd.to_datetime(cutoff_str)

    prompts_file = Path(run_dir) / 'encoder_prompts.jsonl'
    if not prompts_file.exists():
        raise FileNotFoundError(f"Cannot find {prompts_file}")

    prompts = []
    seen_ids = set()
    with open(prompts_file, 'r', encoding='utf-8') as f:
        for line in f:
            p = json.loads(line)
            aid = str(p['asset_id'])
            if aid in seen_ids:
                raise ValueError(f"Duplicate asset_id in prompts: {aid}")
            seen_ids.add(aid)
            prompts.append(p)

    eligible_ids = set(str(a) for a in assets.keys())
    if seen_ids != eligible_ids:
        missing = eligible_ids - seen_ids
        extra = seen_ids - eligible_ids
        raise ValueError(f"Prompt asset IDs mismatch. Missing: {missing}, Extra: {extra}")

    for p in prompts:
        aid = str(p['asset_id'])
        meta = assets[aid]

        asset_ts = pd.to_datetime(meta['timestamp'])
        if asset_ts >= cutoff_dt:
            raise ValueError(f"Asset {aid} timestamp {asset_ts} is not before cutoff {cutoff_dt}")

        expected_source = encoder.source_text(meta)
        expected_prompt = encoder.paraphrase_prompt(expected_source)
        if p['prompt'] != expected_prompt:
            raise ValueError(f"Prompt mismatch for asset {aid}")

    return True

def analyze_subgroups(data_dir, course_dir, run_dir, cutoff_str='2021-06-01'):
    data_dir = Path(data_dir)

    assets, profiles, history, truth, end, excluded = load_course_data(data_dir, course_dir, cutoff_str)
    check_data_leakage(run_dir, course_dir, assets, cutoff_str)

    manifest_path = Path(run_dir) / 'run_manifest.json'
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    target_users = [str(u) for u in manifest['users']]
    if len(target_users) != 100 or len(set(target_users)) != 100:
        raise ValueError(f"Manifest must contain exactly 100 unique users, got {len(target_users)} with {len(set(target_users))} unique")

    per_user_path = Path(run_dir) / 'per_user.json'
    with open(per_user_path, 'r', encoding='utf-8') as f:
        per_user_list = json.load(f)

    metrics = {}
    for entry in per_user_list:
        uid = str(entry['user_id'])
        method = entry['method']
        metrics[(uid, method)] = {
            'ndcg': float(entry['ndcg_at_10']),
            'relevant': int(entry['relevant_count'])
        }

    methods_required = {'original_text_cbf', 'llmrec_encoder'}
    for uid in target_users:
        for method in methods_required:
            if (uid, method) not in metrics:
                raise ValueError(f"Missing per_user entry for user {uid}, method {method}")

        rel_orig = metrics[(uid, 'original_text_cbf')]['relevant']
        rel_llm = metrics[(uid, 'llmrec_encoder')]['relevant']
        if rel_orig != rel_llm:
            raise ValueError(f"relevant_count mismatch for user {uid}: {rel_orig} vs {rel_llm}")

    groups = {
        'len_1': {'users': [], 'ne_users': [], 'ndcg_all': {'original_text_cbf': [], 'llmrec_encoder': []}, 'ndcg_ne': {'original_text_cbf': [], 'llmrec_encoder': []}},
        'len_2_3': {'users': [], 'ne_users': [], 'ndcg_all': {'original_text_cbf': [], 'llmrec_encoder': []}, 'ndcg_ne': {'original_text_cbf': [], 'llmrec_encoder': []}},
        'len_4_plus': {'users': [], 'ne_users': [], 'ndcg_all': {'original_text_cbf': [], 'llmrec_encoder': []}, 'ndcg_ne': {'original_text_cbf': [], 'llmrec_encoder': []}},
        'meta_both': {'users': [], 'ne_users': [], 'ndcg_all': {'original_text_cbf': [], 'llmrec_encoder': []}, 'ndcg_ne': {'original_text_cbf': [], 'llmrec_encoder': []}},
        'meta_none': {'users': [], 'ne_users': [], 'ndcg_all': {'original_text_cbf': [], 'llmrec_encoder': []}, 'ndcg_ne': {'original_text_cbf': [], 'llmrec_encoder': []}},
        'meta_mixed': {'users': [], 'ne_users': [], 'ndcg_all': {'original_text_cbf': [], 'llmrec_encoder': []}, 'ndcg_ne': {'original_text_cbf': [], 'llmrec_encoder': []}}
    }

    processed_users = set()
    for uid in target_users:
        hist_dict = history.get(uid, {})
        if not hist_dict:
            raise ValueError(f"Warm user {uid} has no history")
        hist_assets = list(hist_dict.keys())
        hist_len = len(hist_assets)

        if hist_len == 1:
            len_grp = 'len_1'
        elif hist_len in (2, 3):
            len_grp = 'len_2_3'
        else:
            len_grp = 'len_4_plus'

        meta_states = []
        for aid in hist_assets:
            meta = assets.get(str(aid), {})
            s_miss = get_missing_state(meta.get('sector'))
            i_miss = get_missing_state(meta.get('industry'))
            if not s_miss and not i_miss:
                meta_states.append('both')
            elif s_miss and i_miss:
                meta_states.append('none')
            else:
                meta_states.append('one')

        if all(s == 'both' for s in meta_states):
            meta_grp = 'meta_both'
        elif all(s == 'none' for s in meta_states):
            meta_grp = 'meta_none'
        else:
            meta_grp = 'meta_mixed'

        relevant = metrics[(uid, 'original_text_cbf')]['relevant']
        has_truth = relevant > 0

        groups[len_grp]['users'].append(uid)
        groups[meta_grp]['users'].append(uid)
        if has_truth:
            groups[len_grp]['ne_users'].append(uid)
            groups[meta_grp]['ne_users'].append(uid)

        for method in methods_required:
            ndcg_val = metrics[(uid, method)]['ndcg']
            groups[len_grp]['ndcg_all'][method].append(ndcg_val)
            groups[meta_grp]['ndcg_all'][method].append(ndcg_val)
            if has_truth:
                groups[len_grp]['ndcg_ne'][method].append(ndcg_val)
                groups[meta_grp]['ndcg_ne'][method].append(ndcg_val)

        processed_users.add(uid)

    if len(processed_users) != 100:
        raise ValueError(f"Expected 100 users processed, got {len(processed_users)}")

    len_counts = {g: len(groups[g]['users']) for g in ['len_1', 'len_2_3', 'len_4_plus']}
    meta_counts = {g: len(groups[g]['users']) for g in ['meta_both', 'meta_none', 'meta_mixed']}
    if sum(len_counts.values()) != 100:
        raise ValueError(f"Length groups sum to {sum(len_counts.values())}, expected 100")
    if sum(meta_counts.values()) != 100:
        raise ValueError(f"Metadata groups sum to {sum(meta_counts.values())}, expected 100")

    lines = ["# Maria's HW2 Subgroup Analysis Results\n"]
    lines.append(f"Total target users evaluated: {len(processed_users)}")
    total_ne = sum(1 for uid in target_users if metrics[(uid, 'original_text_cbf')]['relevant'] > 0)
    lines.append(f"Users with non-empty ground truth: {total_ne}\n")

    lines.append("### Validation")
    lines.append(f"- Length groups: {len_counts}")
    lines.append(f"- Metadata groups: {meta_counts}")
    lines.append(f"- Data leakage check: ✅ PASSED\n")

    def fmt_avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    lines.append("### 1. History Length Subgroups")
    lines.append("| Group | Total | Non-Empty | Method | nDCG@10 All | nDCG@10 Non-Empty |")
    lines.append("|---|---:|---:|---|---:|---:|")
    for grp in ['len_1', 'len_2_3', 'len_4_plus']:
        n_total = len(groups[grp]['users'])
        n_ne = len(groups[grp]['ne_users'])
        for method in ['original_text_cbf', 'llmrec_encoder']:
            avg_all = fmt_avg(groups[grp]['ndcg_all'][method])
            avg_ne = fmt_avg(groups[grp]['ndcg_ne'][method])
            method_str = f"**{method}**" if method == 'llmrec_encoder' else method
            lines.append(f"| {grp} | {n_total} | {n_ne} | {method_str} | {avg_all:.4f} | {avg_ne:.4f} |")

    lines.append("\n### 2. Metadata Completeness Subgroups")
    lines.append("| Group | Total | Non-Empty | Method | nDCG@10 All | nDCG@10 Non-Empty |")
    lines.append("|---|---:|---:|---|---:|---:|")
    for grp in ['meta_both', 'meta_none', 'meta_mixed']:
        n_total = len(groups[grp]['users'])
        n_ne = len(groups[grp]['ne_users'])
        for method in ['original_text_cbf', 'llmrec_encoder']:
            avg_all = fmt_avg(groups[grp]['ndcg_all'][method])
            avg_ne = fmt_avg(groups[grp]['ndcg_ne'][method])
            method_str = f"**{method}**" if method == 'llmrec_encoder' else method
            lines.append(f"| {grp} | {n_total} | {n_ne} | {method_str} | {avg_all:.4f} | {avg_ne:.4f} |")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=str, required=True)
    parser.add_argument('--course-dir', type=str, required=True)
    parser.add_argument('--run-dir', type=str, required=True)
    parser.add_argument('--cutoff', type=str, default='2021-06-01')
    parser.add_argument('--out', type=str, required=True)
    args = parser.parse_args()

    results_md = analyze_subgroups(args.data_dir, args.course_dir, args.run_dir, args.cutoff)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(results_md)

    print(f"Analysis complete. Results saved to {args.out}")
    print(results_md)

if __name__ == '__main__':
    main()