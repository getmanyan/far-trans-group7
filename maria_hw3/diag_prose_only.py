#!/usr/bin/env python3
"""Post-hoc diagnostic (PROTOCOL.md, Amendment 1), not the pre-registered ablation.

Half of the saved "paraphrases" are copies of the input JSON. This run keeps the
generated view only for assets whose output is prose (does not start with '{'),
everything else as in run_hw3.py, and compares with the control and full encoder
on the same users. Also splits the full encoder's per-user effect by whether the
user's history contains any prose-paraphrased asset.

  python diag_prose_only.py --course-dir ... --data-dir ... \
      --generations inputs/hw2_generations.jsonl --run-dir outputs/DW
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--course-dir', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--generations', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    run = load_module('run_hw3', here / 'run_hw3.py')
    sys.path.insert(0, str(args.course_dir / 'far-trans-llm'))
    starter = load_module('st', args.course_dir / 'far-trans' / 'starter.py')
    encoder = load_module('enc', args.course_dir / 'far-trans-llm' / 'encoder.py')

    assets, profiles, history, truth, end, _ = starter.load_data(args.data_dir, run.CUTOFF, run.HORIZON)
    users = (args.run_dir / 'users.txt').read_text().split()
    eligible = sorted(assets)
    documents = {i: encoder.source_text(assets[i]) for i in eligible}
    generated, failures = encoder.generate_views(documents, run.ReplayGenerator(args.generations),
                                                 on_invalid='fallback')
    original = encoder.tfidf(documents)
    gvec = encoder.tfidf(generated)
    prose = sorted(i for i in eligible if not generated[i].lstrip().startswith('{'))
    views = {'original_text_cbf': original,
             'llmrec_encoder': encoder.combine_views(original, gvec),
             'diag_prose_only': encoder.combine_views(original, {i: gvec[i] for i in prose})}
    pop = starter.popularity_scores(history, assets)
    scores = {m: [] for m in views}
    has_prose = []
    for uid in users:
        relevant = truth.get(uid, set()) & set(eligible)
        has_prose.append(any(i in set(prose) for i in history[uid]))
        for m, vectors in views.items():
            s = encoder.history_scores(history.get(uid, {}), vectors)
            if not any(s.values()):
                s = pop
            ranking = sorted(eligible, key=lambda i: (-s.get(i, 0.0), i))[:10]
            scores[m].append((starter.ndcg10(ranking, relevant), bool(relevant)))

    def summary(m):
        v = [x for x, _ in scores[m]]
        ne = [x for x, r in scores[m] if r]
        return {'all': sum(v) / len(v), 'nonempty': sum(ne) / len(ne), 'nonempty_users': len(ne)}

    def paired(m, mask=None):
        d = [a[0] - b[0] for k, (a, b) in enumerate(zip(scores[m], scores['original_text_cbf']))
             if mask is None or mask[k]]
        rng = random.Random(42)
        boot = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(2000))
        return {'users': len(d), 'mean_diff': sum(d) / len(d), 'ci95': [boot[49], boot[1949]],
                'up': sum(x > 1e-12 for x in d), 'down': sum(x < -1e-12 for x in d)}

    out = {'prose_assets': len(prose), 'json_copy_assets': len(eligible) - len(prose),
           'invalid_outputs': len(failures), 'users': len(users),
           'metrics': {m: summary(m) for m in views},
           'paired_vs_control': {m: paired(m) for m in ('llmrec_encoder', 'diag_prose_only')},
           'full_encoder_by_history': {
               'history_has_prose_asset': paired('llmrec_encoder', has_prose),
               'history_only_json_copies': paired('llmrec_encoder', [not h for h in has_prose])}}
    (args.run_dir / 'diag_prose_only.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
