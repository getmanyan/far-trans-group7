"""Build the HW2 results table from completed runs and check that protocols match.

Usage:
  python analyze.py --data-dir DATA --baseline outputs/baseline \
      --runs outputs/attr_encoder [outputs/paraphrase_encoder] [--out results.md]

Reads only aggregate/per-user outputs plus past history (for the subgroup split by the
number of distinct assets bought before the cutoff). Prints four-decimal values; the
JSON outputs keep full precision.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ['popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell', 'original_text_cbf',
         'rule_attr_encoder', 'llmrec_encoder', 'llm_attr_encoder', 'llm_attr_only']
LABEL = {'popularity': 'Popularity', 'cbf': 'CBF', 'latest_buy': 'Latest buy',
         'latest_buy_or_sell': 'Latest buy or sell',
         'original_text_cbf': 'Original-text TF-IDF CBF (control)',
         'rule_attr_encoder': 'Rule attributes, no LLM (same-info control)',
         'llmrec_encoder': 'LLM paraphrase encoder (course)',
         'llm_attr_encoder': 'LLM attribute encoder (mine)',
         'llm_attr_only': 'LLM attributes only (ablation)'}


def f4(x):
    return '—' if x is None else f'{x:.4f}'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data-dir', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True, help='starter.py output dir')
    p.add_argument('--runs', type=Path, nargs='+', required=True)
    p.add_argument('--baseline-seconds', type=float, help='Measured whole starter run time')
    p.add_argument('--course-dir', type=Path, default=HERE / 'RecSys-LLMs' / 'project')
    p.add_argument('--out', type=Path)
    a = p.parse_args()

    protocol = json.loads((a.baseline / 'protocol.json').read_text())
    lines, checks, rows, seen = [], [], {}, {}
    for run in a.runs:
        manifest = json.loads((run / 'run_manifest.json').read_text())
        checks.append((run.name, manifest['users'] == protocol['users'],
                       manifest['data_sha256'] == protocol['source_sha256'],
                       manifest['cutoff'] == protocol['cutoff'],
                       manifest['end_exclusive'] == protocol['end_exclusive'],
                       manifest['candidate_count'] == protocol['candidate_count']))
        metrics = json.loads((run / 'metrics.json').read_text())
        per_user = json.loads((run / 'per_user.json').read_text())
        rt = manifest['runtime']
        failed = len(manifest.get('failures', []))
        secs = rt.get('end_to_end_seconds')
        if secs is None:  # course encoder.py: sum of its recorded stages
            secs = sum(rt.get(k, 0) for k in ('preparation_seconds', 'backend_load_seconds',
                                               'inference_seconds', 'feature_seconds',
                                               'scoring_seconds'))
        for name, m in metrics.items():
            if name in rows:  # methods repeated across runs (baselines, control) must agree
                checks.append((f'{name} identical in {run.name}',
                               abs(rows[name][0]['ndcg_at_10'] - m['ndcg_at_10']) < 1e-12))
                continue
            if name in ('popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell'):
                rows[name] = (m, None, 0)
            else:
                rows[name] = (m, (secs, rt.get('cache_hits'), run.name),
                              failed if name.startswith('llm') else 0)
            seen[name] = [r for r in per_user if r['method'] == name]

    # Starter's own baseline metrics must equal the baselines recomputed in each run.
    base = json.loads((a.baseline / 'metrics.json').read_text())
    base = base.get('methods', base)
    for name in ('popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell'):
        if name in base and isinstance(base[name], dict) and 'ndcg_at_10' in base[name]:
            checks.append((f'starter {name}', abs(base[name]['ndcg_at_10'] - rows[name][0]['ndcg_at_10']) < 1e-12))

    sys.path.insert(0, str(a.course_dir / 'far-trans'))
    import starter
    _, profiles, history, _, _, _ = starter.load_data(a.data_dir, protocol['cutoff'], 30)
    distinct = {u: len(history.get(u, {})) for u in protocol['users']}

    lines.append('| Method | Users | Users with future purchases | nDCG@10: all users | '
                 'nDCG@10: nonempty truth | Runtime | Failed cases |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|')
    for name in [n for n in ORDER if n in rows] + sorted(set(rows) - set(ORDER)):
        m, rt, failed = rows[name]
        if rt is None:
            runtime = (f'{a.baseline_seconds:.1f} s (whole starter run)'
                       if a.baseline_seconds else 'whole starter run')
        else:
            runtime = f'{rt[0]:.0f} s (whole {rt[2]} run' + (
                f', {rt[1]} cache hits)' if rt[1] else ')')
        lines.append(f'| {LABEL.get(name, name)} | {m["users"]} | {m["nonempty_truth_users"]} | '
                     f'{f4(m["ndcg_at_10"])} | {f4(m["ndcg_at_10_nonempty"])} | {runtime} | '
                     f'{failed} |')

    lines.append('\nSubgroup by distinct past-bought assets (mean nDCG@10 over nonempty-truth users):\n')
    lines.append('| Method | 1–3 distinct: n | 1–3 distinct | 4+ distinct: n | 4+ distinct |')
    lines.append('|---|---:|---:|---:|---:|')
    for name in [n for n in ORDER if n in seen]:
        recs = [r for r in seen[name] if r['relevant_count']]
        small = [r['ndcg_at_10'] for r in recs if 1 <= distinct[r['user_id']] <= 3]
        large = [r['ndcg_at_10'] for r in recs if distinct[r['user_id']] >= 4]
        mean = lambda v: sum(v) / len(v) if v else None
        lines.append(f'| {LABEL.get(name, name)} | {len(small)} | {f4(mean(small))} | '
                     f'{len(large)} | {f4(mean(large))} |')

    lines.append('\nProtocol checks (True = matches starter protocol.json):')
    for c in checks:
        lines.append('- ' + ' '.join(map(str, c)))
    text = '\n'.join(lines)
    print(text)
    if a.out:
        a.out.write_text(text + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
