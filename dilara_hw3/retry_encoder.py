"""Replay saved HW2 first-pass outputs and add at most one validation-aware retry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hw2 import encoder
from retry_prompt import build_retry_prompt, source_from_prompt

ATTR_FIELDS = tuple(encoder.STRUCTURED_FIELDS)


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')


def hash_tree(root):
    root = Path(root)
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def parse_or_fallback(text, source):
    """Return (attributes, error, used_fallback); never relaxes the HW2 validator."""
    try:
        return encoder.parse_structured_attributes(text, source), '', False
    except (ValueError, TypeError, KeyError) as error:
        return encoder.fallback_structured_attributes(source), str(error), True


def load_first_pass(hw2_outputs):
    """Load saved prompts, raw attempt-1 responses and validation failures."""
    root = Path(hw2_outputs)
    prompts = {row['asset_id']: row['prompt']
               for row in read_jsonl(root / 'structured_attribute_prompts.jsonl')}
    sources = {aid: source_from_prompt(prompt) for aid, prompt in prompts.items()}
    by_prompt = {}
    for row in read_jsonl(root / 'generations.jsonl'):
        prompt = row['prompt']
        text = row['response']['text']
        if prompt in by_prompt and by_prompt[prompt] != text:
            raise ValueError('Saved generation log has conflicting responses for one prompt')
        by_prompt[prompt] = text
    if set(by_prompt) != set(prompts.values()):
        raise ValueError('Saved generation log does not cover exactly the saved prompts')
    attempt1 = {aid: by_prompt[prompts[aid]] for aid in prompts}
    failures = {row['asset_id']: row for row in read_jsonl(root / 'encoder_failures.jsonl')}

    replay = {}
    for aid in sorted(prompts):
        attrs, error, used_fallback = parse_or_fallback(attempt1[aid], sources[aid])
        replay[aid] = {'attributes': attrs, 'error': error, 'fallback': used_fallback}
        recorded = failures.get(aid)
        if used_fallback:
            if recorded is None or recorded['error'] != error:
                raise ValueError(f'{aid}: saved failure reason does not match replay validation')
        elif recorded is not None:
            raise ValueError(f'{aid}: valid replay but a saved failure exists')
    if len(failures) != sum(1 for r in replay.values() if r['fallback']):
        raise ValueError('Saved failure count does not match replay validation')
    return {'prompts': prompts, 'sources': sources, 'attempt1': attempt1,
            'failures': failures, 'replay': replay}


def build_retry_records(first_pass):
    """One record per rejected asset; unique retry prompts are deduplicated."""
    records, groups = [], {}
    for aid in sorted(first_pass['failures']):
        source = first_pass['sources'][aid]
        error = first_pass['failures'][aid]['error']
        rejected = first_pass['attempt1'][aid]
        prompt = build_retry_prompt(source, error, rejected)
        record = {'asset_id': aid, 'source': source, 'original_error': error,
                  'original_response': rejected, 'retry_prompt': prompt,
                  'original_prompt_sha256': sha256_text(first_pass['prompts'][aid]),
                  'retry_prompt_sha256': sha256_text(prompt)}
        records.append(record)
        groups.setdefault(prompt, []).append(aid)
    return records, groups


def select_smoke_assets(records, count=3):
    """Deterministic 3-asset smoke sample covering distinct failure reasons."""
    needles = ('exactly the six allowlisted fields', 'name contains a term',
               'name must be a non-empty array', 'market contains a term',
               'must be valid JSON')
    chosen = []
    for needle in needles:
        for record in records:
            if needle in record['original_error']:
                chosen.append(record)
                break
        if len(chosen) == count:
            break
    if len(chosen) != count:
        raise ValueError('Cannot find three distinct failure types for smoke test')
    return chosen


def run_retries(records, groups, generator, output_dir=None, selected_asset_ids=None):
    """Generate at most one retry per unique prompt and log all evidence."""
    if selected_asset_ids is not None:
        wanted = set(selected_asset_ids)
        records = [r for r in records if r['asset_id'] in wanted]
        groups = {}
        for record in records:
            groups.setdefault(record['retry_prompt'], []).append(record['asset_id'])
    out = Path(output_dir) if output_dir else Path('outputs/retry')
    out.mkdir(parents=True, exist_ok=True)

    write_jsonl(out / 'attempt1_responses.jsonl', [
        {'asset_id': r['asset_id'], 'prompt_sha256': r['original_prompt_sha256'],
         'original_error': r['original_error'], 'response': r['original_response']}
        for r in records])
    write_jsonl(out / 'retry_prompts.jsonl', [
        {'prompt_sha256': sha256_text(prompt), 'asset_ids': aids, 'prompt': prompt}
        for prompt, aids in sorted(groups.items())])

    responses = []
    for prompt in sorted(groups):
        response = generator.generate(prompt, max_new_tokens=160)
        responses.append({'prompt_sha256': sha256_text(prompt), 'asset_ids': groups[prompt],
                          'response': response})
    write_jsonl(out / 'retry_responses.jsonl', responses)

    response_by_prompt = {r['prompt_sha256']: r['response'] for r in responses}
    by_asset = {r['asset_id']: r for r in records}
    audit, views = [], {}
    for aid in sorted(by_asset):
        record = by_asset[aid]
        source = record['source']
        text = response_by_prompt[sha256_text(record['retry_prompt'])]['text']
        retry_attrs, retry_error, retry_fallback = parse_or_fallback(text, source)
        original_attrs, original_error, original_fallback = parse_or_fallback(
            record['original_response'], source)
        if not original_fallback or original_error != record['original_error']:
            raise ValueError(f'{aid}: original validation changed unexpectedly')
        selected = retry_attrs if not retry_fallback else encoder.fallback_structured_attributes(source)
        used_fallback = retry_fallback
        views[aid] = {'view': encoder.structured_text(selected),
                      'attributes': selected,
                      'source': 'fallback' if used_fallback else 'retry',
                      'fallback': used_fallback}
        audit.append({'asset_id': aid, 'original_error': original_error,
                      'original_prompt_sha256': record['original_prompt_sha256'],
                      'retry_prompt_sha256': record['retry_prompt_sha256'],
                      'retry_response': text, 'retry_error': retry_error,
                      'retry_valid': not retry_fallback,
                      'final_attributes': selected, 'fallback': used_fallback})
    write_jsonl(out / 'retry_audit.jsonl', audit)
    (out / 'retry_views.json').write_text(json.dumps(views, ensure_ascii=False, indent=2) + '\n',
                                          encoding='utf-8')
    manifest = {'assets': len(records), 'unique_retry_prompts': len(groups),
                'generator_metadata': generator.metadata,
                'max_new_tokens': 160,
                'protocol_reference': 'd644f56 PROTOCOL.md section 5'}
    (out / 'retry_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                              encoding='utf-8')
    return {'audit': audit, 'views': views, 'manifest': manifest, 'groups': groups}


def build_views(first_pass, retry_views=None):
    """Return per-asset final view records for A (no retry) or B (with retry)."""
    views = {}
    for aid, replay in first_pass['replay'].items():
        source = first_pass['sources'][aid]
        views[aid] = {'view': encoder.structured_text(replay['attributes']),
                      'attributes': replay['attributes'],
                      'source': 'fallback' if replay['fallback'] else 'first_pass',
                      'fallback': replay['fallback']}
    if retry_views:
        for aid, record in retry_views.items():
            if aid not in views:
                raise ValueError(f'Retry view for unknown asset {aid}')
            views[aid] = record
    return views


def fallback_views(first_pass):
    views = {}
    for aid, source in first_pass['sources'].items():
        attrs = encoder.fallback_structured_attributes(source)
        views[aid] = {'view': encoder.structured_text(attrs), 'attributes': attrs,
                      'source': 'fallback', 'fallback': True}
    return views
