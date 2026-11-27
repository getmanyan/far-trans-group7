"""Contract tests for the retry mechanism; fake generators, no model calls."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dilara_hw3'))

import retry_encoder  # noqa: E402
import retry_prompt  # noqa: E402
from hw2 import encoder  # noqa: E402

SOURCE = json.dumps({'category': 'Stock', 'industry': 'Insurance - Diversified',
                     'market': 'XHEL', 'name': 'Sampo Oyj', 'sector': 'Financial Services',
                     'subcategory': 'unknown'}, sort_keys=True, ensure_ascii=False)
VALID = {'name': ['sampo', 'oyj'], 'category': ['stock'], 'subcategory': ['unknown'],
         'sector': ['financial services'], 'industry': ['insurance - diversified'],
         'market': ['xhel']}
REJECTED = json.dumps(dict(VALID, name=['sampoyj']))
NAME_ERROR = 'name contains a term not supported by its source field'


class FakeGenerator:
    def __init__(self, responses, metadata=None):
        self.responses = list(responses)
        self.prompts = []
        self.metadata = metadata or {'model': 'fake', 'requested_revision': 'r',
                                     'resolved_revision': 'r', 'device': 'cpu',
                                     'dtype': 'fake', 'do_sample': False,
                                     'thinking': False, 'context_limit': 8192}

    def generate(self, prompt, max_new_tokens=160):
        self.prompts.append((prompt, max_new_tokens))
        return {'text': self.responses.pop(0), 'input_tokens': 10,
                'output_tokens': 10, 'seconds': 0.01}


def rejected_record(aid='FI0009003305', error=NAME_ERROR, response=REJECTED):
    prompt = retry_prompt.build_retry_prompt(SOURCE, error, response)
    return {'asset_id': aid, 'source': SOURCE, 'original_error': error,
            'original_response': response,
            'original_prompt_sha256': 'a' * 64, 'retry_prompt': prompt,
            'retry_prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}


class RetryValidationTests(unittest.TestCase):
    def test_valid_retry_is_selected(self):
        record = rejected_record()
        groups = {record['retry_prompt']: [record['asset_id']]}
        with tempfile.TemporaryDirectory() as tmp:
            generator = FakeGenerator([json.dumps(VALID)])
            result = retry_encoder.run_retries([record], groups, generator, tmp)
        audit = result['audit'][0]
        self.assertTrue(audit['retry_valid'])
        self.assertFalse(audit['fallback'])
        self.assertEqual(audit['final_attributes'], VALID)
        self.assertEqual(result['views']['FI0009003305']['source'], 'retry')

    def test_invalid_retry_uses_deterministic_fallback(self):
        record = rejected_record()
        bad = json.dumps(dict(VALID, name=['sampoyj']))
        groups = {record['retry_prompt']: [record['asset_id']]}
        with tempfile.TemporaryDirectory() as tmp:
            generator = FakeGenerator([bad])
            result = retry_encoder.run_retries([record], groups, generator, tmp)
        audit = result['audit'][0]
        self.assertFalse(audit['retry_valid'])
        self.assertTrue(audit['fallback'])
        self.assertEqual(audit['final_attributes'],
                         encoder.fallback_structured_attributes(SOURCE))
        self.assertEqual(result['views']['FI0009003305']['source'], 'fallback')

    def test_strict_schema_and_source_grounding_never_relaxed(self):
        cases = [
            (json.dumps(dict(VALID, extra=['x'])), 'exactly the six'),
            (json.dumps({k: v for k, v in VALID.items() if k != 'market'}), 'exactly the six'),
            (json.dumps(dict(VALID, name=['sampoyj'])), 'not supported'),
            (json.dumps(dict(VALID, name=['x'] * 9)), 'at most eight'),
            (json.dumps(dict(VALID, name=['sampo', 'sampo'])), 'duplicate terms'),
            ('not json', 'valid JSON'),
        ]
        for raw, needle in cases:
            with self.subTest(raw=raw):
                attrs, error, fallback = retry_encoder.parse_or_fallback(raw, SOURCE)
                self.assertTrue(fallback)
                self.assertIn(needle, error)
                self.assertEqual(attrs, encoder.fallback_structured_attributes(SOURCE))
        attrs, error, fallback = retry_encoder.parse_or_fallback(json.dumps(VALID), SOURCE)
        self.assertFalse(fallback)
        self.assertEqual(error, '')
        self.assertEqual(attrs, VALID)

    def test_exactly_one_retry_per_unique_prompt(self):
        a = rejected_record('A')
        b = rejected_record('B')
        groups = {a['retry_prompt']: ['A', 'B']}
        with tempfile.TemporaryDirectory() as tmp:
            generator = FakeGenerator(['not json'])
            result = retry_encoder.run_retries([a, b], groups, generator, tmp)
        self.assertEqual(len(generator.prompts), 1)
        self.assertEqual(generator.prompts[0][1], 160)
        self.assertEqual(result['manifest']['assets'], 2)
        self.assertEqual(result['manifest']['unique_retry_prompts'], 1)
        self.assertTrue(all(row['fallback'] for row in result['audit']))

    def test_shared_prompts_produce_identical_views(self):
        a = rejected_record('A')
        b = rejected_record('B')
        groups = {a['retry_prompt']: ['A', 'B']}
        with tempfile.TemporaryDirectory() as tmp:
            generator = FakeGenerator([json.dumps(VALID)])
            result = retry_encoder.run_retries([a, b], groups, generator, tmp)
        self.assertEqual(result['views']['A'], result['views']['B'])

    def test_fallback_is_deterministic(self):
        first = encoder.fallback_structured_attributes(SOURCE)
        second = encoder.fallback_structured_attributes(SOURCE)
        self.assertEqual(first, second)
        self.assertEqual(encoder.structured_text(first), encoder.structured_text(second))

    def test_retry_prompt_has_no_future_or_customer_information(self):
        prompt = retry_prompt.build_retry_prompt(SOURCE, NAME_ERROR, REJECTED)
        self.assertTrue(prompt.startswith(encoder.structured_prompt(SOURCE)))
        for term in retry_prompt.FORBIDDEN_PROMPT_TERMS:
            self.assertNotIn(term, prompt)
        self.assertEqual(retry_prompt.source_from_prompt(
            encoder.structured_prompt(SOURCE)), SOURCE)

    def test_original_evidence_files_are_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {'structured_attribute_prompts.jsonl': [
                {'asset_id': 'A', 'prompt': encoder.structured_prompt(SOURCE)}],
                'generations.jsonl': [
                    {'prompt': encoder.structured_prompt(SOURCE),
                     'response': {'text': '{"bad":[]}', 'seconds': 0.1}}],
                'encoder_failures.jsonl': [
                    {'asset_id': 'A', 'error': 'Structured response must have exactly the six allowlisted fields',
                     'response': '{"bad":[]}', 'fallback': True}]}
            for name, rows in files.items():
                retry_encoder.write_jsonl(root / name, rows)
            before = retry_encoder.hash_tree(root)
            first_pass = retry_encoder.load_first_pass(root)
            self.assertEqual(first_pass['attempt1']['A'], '{"bad":[]}')
            self.assertEqual(first_pass['failures']['A']['error'],
                             'Structured response must have exactly the six allowlisted fields')
            self.assertEqual(retry_encoder.hash_tree(root), before)

    def test_conflicting_saved_responses_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = encoder.structured_prompt(SOURCE)
            retry_encoder.write_jsonl(root / 'structured_attribute_prompts.jsonl',
                                      [{'asset_id': 'A', 'prompt': prompt}])
            retry_encoder.write_jsonl(root / 'generations.jsonl', [
                {'prompt': prompt, 'response': {'text': 'x'}},
                {'prompt': prompt, 'response': {'text': 'y'}}])
            with self.assertRaises(ValueError):
                retry_encoder.load_first_pass(root)


class ScoringIdentityTests(unittest.TestCase):
    def setUp(self):
        self.assets = {}
        self.sources = {}
        for aid, name in (('A1', 'Alpha'), ('A2', 'Beta'), ('A3', 'Gamma')):
            asset = {'assetName': name, 'assetCategory': 'Stock', 'assetSubCategory': '',
                     'sector': '', 'industry': '', 'marketID': 'XHEL', 'timestamp': '2018-01-02'}
            self.assets[aid] = asset
            self.sources[aid] = encoder.source_text(asset)
        self.pop = {'A1': 0.5, 'A2': 0.3, 'A3': 0.2}
        self.contexts = {'U': {'eligible_asset_ids': ['A1', 'A2', 'A3']}}
        self.history = {'U': Counter({'A1': 2})}
        self.bundle = (object(), self.assets, self.history, {}, self.contexts,
                       {'U': {}}, {}, self.pop, {'users': ['U']})

    def first_pass(self):
        replay = {}
        for aid, source in self.sources.items():
            facts = json.loads(source)
            generated = {}
            for field in encoder.STRUCTURED_FIELDS:
                value = str(facts[field]).casefold()
                generated[field] = ['unknown'] if value == 'unknown' else [value]
            attrs, error, fallback = retry_encoder.parse_or_fallback(
                json.dumps(generated), source)
            self.assertFalse(fallback, error)
            replay[aid] = {'attributes': attrs, 'fallback': False}
        return {'sources': self.sources, 'prompts': {}, 'attempt1': {},
                'failures': {}, 'replay': replay}

    def test_scoring_matches_unchanged_encoder_predict(self):
        from run_hw3 import score_all
        first_pass = self.first_pass()
        views = retry_encoder.build_views(first_pass)
        predictions = score_all(self.bundle, first_pass, views)
        documents = {i: encoder.source_text(a) for i, a in self.assets.items()}
        original = encoder.tfidf(documents)
        combined = encoder.combine_structured_view(
            original, encoder.tfidf({i: views[i]['view'] for i in views}))
        expected = encoder.predict(self.contexts, self.history, original, combined, self.pop,
                                   method_name='structured_encoder_v1')
        self.assertEqual(predictions, expected)

    def test_retry_changes_only_the_retry_method(self):
        from run_hw3 import score_all
        first_pass = self.first_pass()
        views_a = retry_encoder.build_views(first_pass)
        views_b = dict(views_a)
        changed = dict(views_a['A1'])
        changed.update({'view': 'field_name_zeta field_category_stock',
                        'attributes': dict(VALID), 'source': 'retry', 'fallback': False})
        views_b['A1'] = changed
        without = score_all(self.bundle, first_pass, views_a)
        with_retry = score_all(self.bundle, first_pass, views_a, views_b)
        self.assertEqual(with_retry['U']['structured_encoder_v1'],
                         without['U']['structured_encoder_v1'])
        self.assertIn('structured_retry_once', with_retry['U'])
        self.assertNotIn('structured_retry_once', without['U'])


if __name__ == '__main__':
    unittest.main()
