"""Bounded non-evaluation diagnostic for 1-3 structured asset generations."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from encoder import generate_structured_views, source_text
from runtime import LocalGenerator, LoggedGenerator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-json', type=Path, required=True,
                        help='JSON object mapping at most three IDs to allowlisted asset rows')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--device', choices=['auto', 'cpu', 'mps', 'cuda'], default='auto')
    parser.add_argument('--allow-download', action='store_true')
    parser.add_argument('--on-invalid', choices=['error', 'fallback'], default='fallback')
    args = parser.parse_args()
    assets = json.loads(args.assets_json.read_text(encoding='utf-8'))
    if type(assets) is not dict or not 1 <= len(assets) <= 3:
        raise ValueError('--assets-json must contain one to three assets')
    documents = {asset_id: source_text(asset) for asset_id, asset in sorted(assets.items())}
    load_started = time.perf_counter()
    backend = LocalGenerator(args.model, args.revision, args.device, args.allow_download)
    load_seconds = time.perf_counter() - load_started
    logged = LoggedGenerator(backend, args.output_dir)

    class TimedGenerator:
        output_dir = logged.output_dir

        def __init__(self):
            self.seconds = []

        def generate(self, prompt, max_new_tokens):
            started = time.perf_counter()
            result = logged.generate(prompt, max_new_tokens)
            self.seconds.append(time.perf_counter() - started)
            return result

    generator = TimedGenerator()
    structured, failures = generate_structured_views(documents, generator, args.on_invalid)
    (args.output_dir / 'smoke_result.json').write_text(json.dumps({
        'diagnostic_only': True, 'evaluation_completed': False,
        'asset_count': len(documents), 'failures': failures,
        'structured_views': structured, 'model': logged.metadata,
        'model_load_seconds': load_seconds,
        'generation_seconds': generator.seconds,
        'median_generation_seconds_per_asset': statistics.median(generator.seconds),
        'total_generation_seconds': sum(generator.seconds),
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
