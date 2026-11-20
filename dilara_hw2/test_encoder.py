"""Encoder arithmetic and injected-generator tests; not LLM experiments."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from encoder import (tfidf, combine_views, combine_structured_view,
                     history_scores, source_text, paraphrase_prompt,
                     structured_prompt, parse_structured_attributes,
                     fallback_structured_attributes, structured_text,
                     generate_views, generate_structured_views, predict)


class EncoderTests(unittest.TestCase):
    def assertSparse(self, actual, expected, tolerance=1e-12):
        self.assertEqual(set(actual), set(expected))
        for key in expected:
            self.assertAlmostEqual(actual[key], expected[key], delta=tolerance)

    def test_all_five_ledger_vectors(self):
        spec = Path(__file__).resolve().parents[2] / 'docs/research/math-ledger/far-trans-llm-baselines.md'
        if spec.is_file():
            vectors = json.loads(spec.read_text().split('```json\n')[1].split('```')[0])
        else:
            # Standalone distribution: the same independently specified E701–E703
            # vectors, without depending on the course repository's docs tree.
            vectors = [
                dict(id='TV1', equation='E701', input={'documents': ['alpha', 'alpha']},
                     expected=[{'alpha': 1.0}, {'alpha': 1.0}], tolerance={'atol': 1e-12}),
                dict(id='TV2', equation='E701', input={'documents': ['', '']},
                     expected=[{}, {}], tolerance={'atol': 0}),
                dict(id='TV3', equation='E702', input={'original': {'x': 1.0}, 'generated': {'y': 1.0}},
                     expected={'original:x': 0.7071067811865476, 'generated:y': 0.7071067811865476}),
                dict(id='TV4', equation='E703', input={'vectors': {'A': {'x': 1.0}, 'B': {'y': 1.0}},
                     'counts': {'A': 2, 'B': 1}}, expected={'A': 0.8944271909999159, 'B': 0.4472135954999579}),
                dict(id='TV5', equation='E703', input={'vectors': {'A': {'x': 1.0}}, 'counts': {}},
                     expected={'A': 0.0}),
            ]
        self.assertEqual(len(vectors), 5)
        for tv in vectors:
            with self.subTest(vector=tv['id']):
                data = tv['input']
                if tv['equation'] == 'E701':
                    actual = list(tfidf(dict(enumerate(data['documents']))).values())
                    for a, e in zip(actual, tv['expected']):
                        self.assertSparse(a, e, tv['tolerance']['atol'])
                elif tv['equation'] == 'E702':
                    actual = combine_views({'A': data['original']}, {'A': data['generated']})['A']
                    self.assertSparse(actual, tv['expected'])
                else:
                    self.assertSparse(history_scores(data['counts'], data['vectors']), tv['expected'])

    def test_nontrivial_df_and_raw_counts(self):
        # beta appears once in two docs: IDF = 1 + ln(3/2); alpha IDF = 1.
        idf = 1.4054651081081644
        norm = math.sqrt(4 + idf * idf)
        actual = tfidf({'A': 'ALPHA alpha beta', 'B': 'alpha'})
        self.assertSparse(actual['A'], {'alpha': 2 / norm, 'beta': idf / norm})
        self.assertSparse(actual['B'], {'alpha': 1})
        self.assertEqual(tfidf({}), {})
        self.assertEqual(tfidf({'A': ''}), {'A': {}})

    def test_namespaces_and_missing_view(self):
        self.assertSparse(combine_views({'A': {'x': 4}}, {'A': {'x': 2}})['A'],
                          {'original:x': 1 / math.sqrt(2), 'generated:x': 1 / math.sqrt(2)})
        self.assertEqual(combine_views({'A': {}}, {'B': {'x': 1}}),
                         {'A': {}, 'B': {'generated:x': 1}})

    def test_count_validation(self):
        for count in (-1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                history_scores({'A': count}, {'A': {'x': 1}})
        self.assertEqual(history_scores({'missing': 2}, {'A': {}}), {'A': 0})

    def test_safe_canonical_source(self):
        text = source_text({'assetName': 'Alpha', 'sector': 'Energy', 'ISIN': 'SECRET',
                            'timestamp': '2099-01-01', 'future_returns': 'LEAK'})
        self.assertEqual(set(json.loads(text)), {'name', 'category', 'subcategory', 'sector', 'industry', 'market'})
        self.assertNotIn('SECRET', text)
        self.assertNotIn('LEAK', text)
        self.assertNotIn('2099', text)
        self.assertEqual(json.loads(text)['industry'], 'unknown')
        self.assertIn('<=40 words', paraphrase_prompt(text))
        self.assertEqual(text, source_text({'sector': 'Energy', 'assetName': 'Alpha'}))

    def test_structured_json_is_strict_and_source_grounded(self):
        source = source_text({'assetName': 'Alpha Growth', 'assetCategory': 'Stock',
                              'assetSubCategory': 'Common', 'sector': 'Energy',
                              'industry': 'Oil', 'marketID': 'EU'})
        valid = json.dumps({field: [value] for field, value in {
            'name': 'alpha', 'category': 'stock', 'subcategory': 'common',
            'sector': 'energy', 'industry': 'oil', 'market': 'eu'}.items()})
        parsed = parse_structured_attributes(valid, source)
        self.assertEqual(parsed['sector'], ['energy'])
        with self.assertRaises(ValueError):
            parse_structured_attributes(json.dumps({'sector': ['energy']}), source)
        invalid = json.loads(valid)
        invalid['sector'] = ['financials']
        with self.assertRaises(ValueError):
            parse_structured_attributes(json.dumps(invalid), source)

    def test_structured_unknown_and_prompt_leakage(self):
        source = source_text({'assetName': 'Alpha', 'assetCategory': 'Stock',
                              'assetSubCategory': '', 'sector': 'Not_Available',
                              'industry': '', 'marketID': 'EU'})
        fallback = fallback_structured_attributes(source)
        self.assertEqual(fallback['sector'], ['unknown'])
        self.assertEqual(fallback['industry'], ['unknown'])
        prompt = structured_prompt(source)
        self.assertNotIn('ISIN', prompt)
        self.assertNotIn('2099', prompt)
        self.assertIn('exactly these six keys', prompt)

    def test_structured_fallback_is_logged_and_deterministic(self):
        class Fake:
            def __init__(self):
                self.calls = []
            def generate(self, prompt, max_new_tokens):
                self.calls.append((prompt, max_new_tokens))
                return {'text': '{}'}
        source = source_text({'assetName': 'Alpha', 'assetCategory': 'Stock'})
        fake = Fake()
        first, failures = generate_structured_views({'A': source}, fake, 'fallback')
        second, _ = generate_structured_views({'A': source}, Fake(), 'fallback')
        self.assertEqual(first, second)
        self.assertEqual(len(failures), 1)
        self.assertTrue(failures[0]['fallback'])
        self.assertEqual(fake.calls[0][1], 160)

    def test_structured_view_changes_scores_and_predictions(self):
        original = tfidf({'A': 'shared', 'B': 'shared'})
        structured = tfidf({'A': structured_text({'name': ['alpha'], 'category': ['stock'],
                                                    'subcategory': ['unknown'], 'sector': ['energy'],
                                                    'industry': ['oil'], 'market': ['eu']}),
                            'B': structured_text({'name': ['beta'], 'category': ['stock'],
                                                    'subcategory': ['unknown'], 'sector': ['finance'],
                                                    'industry': ['bank'], 'market': ['us']})})
        combined = combine_structured_view(original, structured)
        self.assertGreater(history_scores({'A': 1}, combined)['A'],
                           history_scores({'A': 1}, combined)['B'])
        contexts = {'u': {'eligible_asset_ids': ['A', 'B']}}
        predictions = predict(contexts, {'u': {'A': 1}}, original, combined,
                              {'A': 0, 'B': 0}, method_name='structured_attribute_encoder')
        self.assertEqual(predictions['u']['structured_attribute_encoder'][0], 'A')

    def test_generation_once_per_asset_and_invalid(self):
        class Fake:
            def __init__(self, response):
                self.calls = []
                self.response = response
            def generate(self, prompt, max_new_tokens):
                self.calls.append(prompt)
                return {'text': self.response}
        fake = Fake('Known facts only.')
        generated, failures = generate_views({'B': 'beta', 'A': 'alpha'}, fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(set(generated), {'A', 'B'})
        self.assertEqual(failures, [])
        for response in ('', 'word ' * 41):
            with self.assertRaises(ValueError):
                generate_views({'A': 'alpha'}, Fake(response))
            generated, failures = generate_views({'A': 'alpha'}, Fake(response), 'fallback')
            self.assertEqual(generated, {'A': 'alpha'})
            self.assertEqual(failures[0]['asset_id'], 'A')
            self.assertTrue(failures[0]['fallback'])

    def test_user_coverage_cold_ties_same_full_universe(self):
        ids = [f'{i:02d}' for i in range(12)]
        contexts = {u: {'eligible_asset_ids': ids} for u in ('warm', 'cold')}
        vectors = tfidf({i: 'alpha' for i in ids})
        predictions = predict(contexts, {'warm': {'00': 3}}, vectors,
                              combine_views(vectors, vectors), {i: int(i) for i in ids})
        self.assertEqual(set(predictions), set(contexts))
        for methods in predictions.values():
            for ranking in methods.values():
                self.assertEqual(len(ranking), 10)
                self.assertEqual(len(set(ranking)), 10)
                self.assertTrue(set(ranking) <= set(ids))
        self.assertEqual(predictions['warm']['original_text_cbf'], ids[:10])
        self.assertEqual(predictions['cold']['llmrec_encoder'], list(reversed(ids))[:10])

    def test_adapter_excludes_future_metadata(self):
        import tempfile
        starter_path = Path(__file__).resolve().parent / 'far-trans/starter.py'
        spec = importlib.util.spec_from_file_location('encoder_test_starter', starter_path)
        starter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(starter)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'assets.csv'
            path.write_text('ISIN,timestamp,assetName\nA,2020-01-01,Past\nA,2022-01-01,Future\n')
            records = starter.latest_before(path, 'ISIN', '2021-06-01')
            self.assertIn('Past', source_text(records['A']))
            self.assertNotIn('Future', source_text(records['A']))


if __name__ == '__main__':
    unittest.main()
