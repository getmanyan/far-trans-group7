#!/usr/bin/env python3
"""HW3 development run (Maria, Group 7): course encoder vs matched control, one ablation.

Uses the course starter and encoder functions unchanged (dryjins/RecSys-LLMs 799e54c).
The LLM is not re-run: a replay backend returns the saved HW2 Qwen3-1.7B response for
the exact prompt (see PROTOCOL.md). Standard library only.

Example:
  python run_hw3.py --course-dir ../RecSys-LLMs/project --data-dir FAR-Trans \
      --generations inputs/hw2_generations.jsonl --output-dir outputs/DW --max-users 0
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

CUTOFF, HORIZON, CANDIDATES = '2021-06-01', 30, 50
DATA_FILES = ('transactions.csv', 'asset_information.csv',
              'customer_information.csv', 'close_prices.csv')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def is_missing(value):
    """Same rule as maria_hw2/analyze_maria.py get_missing_state."""
    return value is None or str(value).strip().lower() in ('', 'not_available', 'nan', 'unknown')


def meta_state(asset):
    s, i = is_missing(asset.get('sector')), is_missing(asset.get('industry'))
    return 'both' if not s and not i else ('none' if s and i else 'one')


def user_groups(counts, assets):
    n = len(counts)
    length = 'len_1' if n == 1 else ('len_2_3' if n <= 3 else 'len_4_plus')
    states = [meta_state(assets[i]) for i in counts]
    meta = ('meta_both' if all(s == 'both' for s in states)
            else 'meta_none' if all(s == 'none' for s in states) else 'meta_mixed')
    return length, meta


class ReplayGenerator:
    """Return the saved response for an exact prompt; missing prompts are errors."""

    def __init__(self, path):
        self.responses, settings = {}, set()
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            record = json.loads(line)
            if record['max_new_tokens'] != 160:
                raise ValueError('Unexpected generation budget in log')
            previous = self.responses.get(record['prompt'])
            if previous is not None and previous['text'] != record['response']['text']:
                raise ValueError('Same prompt with different saved responses')
            self.responses[record['prompt']] = record['response']
            settings.add(json.dumps(record['settings'], sort_keys=True))
        if len(settings) != 1:
            raise ValueError('Generation log mixes model settings')
        self.metadata = dict(json.loads(settings.pop()), backend='replay of saved HW2 log',
                             log_sha256=sha256(path))
        self.calls = 0

    def generate(self, prompt, max_new_tokens=160):
        if max_new_tokens != 160:
            raise ValueError('Replay only covers max_new_tokens=160')
        if prompt not in self.responses:
            raise KeyError('Prompt not in saved generation log')
        self.calls += 1
        return self.responses[prompt]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--course-dir', type=Path, required=True,
                        help='RecSys-LLMs/project (contains far-trans and far-trans-llm)')
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--generations', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-users', type=int, required=True, help='100 = D100, 0 = all warm users')
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError('Use a fresh output directory')
    args.output_dir.mkdir(parents=True)

    sys.path.insert(0, str(args.course_dir / 'far-trans-llm'))
    starter = load_module('provided_far_trans_starter', args.course_dir / 'far-trans' / 'starter.py')
    encoder = load_module('provided_encoder', args.course_dir / 'far-trans-llm' / 'encoder.py')

    # ---- preparation (data, users, contexts, baselines) ----
    t0 = time.perf_counter()
    assets, profiles, history, truth, end, excluded = starter.load_data(args.data_dir, CUTOFF, HORIZON)
    users = starter.select_users(profiles, history, 'warm', args.max_users, None)
    features = {isin: starter.tokens(a) for isin, a in assets.items()}
    pop = starter.popularity_scores(history, assets)
    contexts, baseline = starter.contexts_for(users, assets, profiles, history, features,
                                              pop, CUTOFF, CANDIDATES, False)
    events = starter.scan_recent_events(args.data_dir, CUTOFF, assets)
    recent = starter.recency_rankings(contexts, pop, events, k=10)
    for uid in users:
        baseline[uid].update(recent[uid])
    preparation_seconds = time.perf_counter() - t0

    # ---- encoder views (LLM output replayed from the saved HW2 log) ----
    t0 = time.perf_counter()
    eligible = sorted({i for c in contexts.values() for i in c['eligible_asset_ids']})
    documents = {i: encoder.source_text(assets[i]) for i in eligible}
    generator = ReplayGenerator(args.generations)
    generated, failures = encoder.generate_views(documents, generator, on_invalid='fallback')
    generation_replay_seconds = time.perf_counter() - t0

    t0 = time.perf_counter()
    original = encoder.tfidf(documents)
    generated_vectors = encoder.tfidf(generated)
    combined = encoder.combine_views(original, generated_vectors)
    meta_none_assets = sorted(i for i in eligible if meta_state(assets[i]) == 'none')
    ablation = encoder.combine_views(original, {i: generated_vectors[i] for i in meta_none_assets})
    feature_seconds = time.perf_counter() - t0

    # ---- scoring (same rule as encoder.predict) ----
    views = (('original_text_cbf', original), ('llmrec_encoder', combined),
             ('llmrec_meta_none_only', ablation))
    scoring_seconds, predictions, popularity_fallback = {}, {uid: {} for uid in users}, {}
    for name, vectors in views:
        t0 = time.perf_counter()
        popularity_fallback[name] = 0
        for uid in users:
            scores = encoder.history_scores(history.get(uid, {}), vectors)
            if not any(scores.values()):
                scores = pop
                popularity_fallback[name] += 1
            ranking = sorted(contexts[uid]['eligible_asset_ids'],
                             key=lambda i: (-scores.get(i, 0.0), i))[:10]
            predictions[uid][name] = ranking
        scoring_seconds[name] = time.perf_counter() - t0

    # ---- evaluation (starter.ndcg10 / starter.aggregate) ----
    t0 = time.perf_counter()
    records = []
    with (args.output_dir / 'predictions.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['method', 'user_id', 'rank', 'ISIN'])
        for uid in users:
            relevant = truth.get(uid, set()) & set(contexts[uid]['eligible_asset_ids'])
            length, meta = user_groups(history[uid], assets)
            for name, ranking in {**baseline[uid], **predictions[uid]}.items():
                starter.validate_ranking(ranking, contexts[uid]['eligible_asset_ids'])
                records.append({'user_id': uid, 'method': name, 'relevant_count': len(relevant),
                                'ndcg_at_10': starter.ndcg10(ranking, relevant),
                                'len_group': length, 'meta_group': meta,
                                'history_assets': len(history[uid])})
                writer.writerows((name, uid, r, i) for r, i in enumerate(ranking, 1))
    methods = ['popularity', 'cbf', 'latest_buy', 'latest_buy_or_sell',
               'original_text_cbf', 'llmrec_encoder', 'llmrec_meta_none_only']
    metrics = {m: starter.aggregate([r for r in records if r['method'] == m]) for m in methods}
    evaluation_seconds = time.perf_counter() - t0

    with (args.output_dir / 'paraphrases.jsonl').open('w', encoding='utf-8') as stream:
        for i in eligible:
            stream.write(json.dumps({'asset_id': i, 'meta_state': meta_state(assets[i]),
                                     'source': documents[i], 'paraphrase': generated[i]},
                                    ensure_ascii=False) + '\n')
    hw2_manifest = args.generations.with_name('hw2_run_manifest.json')
    hw2_runtime = None
    if hw2_manifest.exists():
        runtime = json.loads(hw2_manifest.read_text(encoding='utf-8'))['runtime']
        hw2_runtime = {k: runtime[k] for k in ('backend_load_seconds', 'inference_seconds',
                                               'new_calls', 'cache_hits', 'gpu', 'dtype')}
    users_text = '\n'.join(users) + '\n'
    (args.output_dir / 'users.txt').write_text(users_text, encoding='utf-8')
    manifest = {
        'development_results_not_official_benchmark': True,
        'protocol_sha256': sha256(Path(__file__).with_name('PROTOCOL.md')),
        'script_sha256': sha256(__file__),
        'course_starter_sha256': sha256(args.course_dir / 'far-trans' / 'starter.py'),
        'course_encoder_sha256': sha256(args.course_dir / 'far-trans-llm' / 'encoder.py'),
        'data_sha256': {f: sha256(args.data_dir / f) for f in DATA_FILES},
        'users_sha256': hashlib.sha256(users_text.encode()).hexdigest(),
        'cutoff': CUTOFF, 'end_exclusive': end, 'horizon_days': HORIZON,
        'repeat_allowed': True, 'cohort': 'warm', 'max_users': args.max_users,
        'users': len(users), 'eligible_assets': len(eligible),
        'meta_none_assets': len(meta_none_assets), 'excluded_rows': excluded,
        'llm': generator.metadata, 'replayed_responses': generator.calls,
        'invalid_outputs': len(failures), 'failures': failures,
        'fallback_to_source_text': sum(f['fallback'] for f in failures),
        'popularity_fallback_users': popularity_fallback,
        'timing_seconds': {'preparation': preparation_seconds,
                           'generation_replay': generation_replay_seconds,
                           'hw2_original_run_on_T4': hw2_runtime,
                           'features': feature_seconds, 'scoring': scoring_seconds,
                           'evaluation': evaluation_seconds},
        'hardware': {'platform': platform.platform(), 'python': platform.python_version(),
                     'machine': platform.machine()},
    }
    for name, data in (('metrics.json', metrics), ('per_user.json', records),
                       ('run_manifest.json', manifest)):
        (args.output_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n',
                                            encoding='utf-8')
    for m in methods:
        v = metrics[m]
        print(f"{m:24s} all={v['ndcg_at_10']:.4f} nonempty={v['ndcg_at_10_nonempty']:.4f} "
              f"(n={v['nonempty_truth_users']}/{v['users']})")


if __name__ == '__main__':
    main()
