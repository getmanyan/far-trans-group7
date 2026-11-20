"""Pure-function tests for attribute_encoder.py (no model, no dataset)."""
import json
import unittest

import attribute_encoder as ae


class ParseTests(unittest.TestCase):
    good = {'asset_class': 'equity', 'sector': 'financials', 'region': 'greece',
            'currency': 'eur'}

    def test_valid_json_with_surrounding_text(self):
        raw = 'Here it is:\n```json\n' + json.dumps(self.good) + '\n```'
        self.assertEqual(ae.parse_attributes(raw), self.good)

    def test_case_and_spaces_are_normalized(self):
        raw = json.dumps(dict(self.good, sector='Health Care', region='North-America'))
        parsed = ae.parse_attributes(raw)
        self.assertEqual(parsed['sector'], 'health_care')
        self.assertEqual(parsed['region'], 'north_america')

    def test_value_outside_vocabulary_is_invalid(self):
        with self.assertRaises(ValueError):
            ae.parse_attributes(json.dumps(dict(self.good, sector='banking')))

    def test_missing_or_extra_key_is_invalid(self):
        missing = {k: v for k, v in self.good.items() if k != 'currency'}
        with self.assertRaises(ValueError):
            ae.parse_attributes(json.dumps(missing))
        with self.assertRaises(ValueError):
            ae.parse_attributes(json.dumps(dict(self.good, risk='low')))

    def test_no_json_is_invalid(self):
        with self.assertRaises(ValueError):
            ae.parse_attributes('equity, financials')


class TextTests(unittest.TestCase):
    def test_unknown_values_add_no_tokens(self):
        attrs = {'asset_class': 'fixed_income', 'sector': 'unknown', 'region': 'europe',
                 'currency': 'unknown'}
        self.assertEqual(ae.attribute_text(attrs), 'asset_class_fixed_income region_europe')

    def test_prompt_contains_schema_and_no_identifier(self):
        prompt = ae.attribute_prompt('{"name": "X"}')
        for key in ae.SCHEMA:
            self.assertIn(key, prompt)
        self.assertNotIn('ISIN', prompt)
        self.assertTrue(prompt.endswith('Asset: {"name": "X"}'))


class FallbackTests(unittest.TestCase):
    class Stub:
        def __init__(self, answers):
            self.answers = answers

        def generate(self, prompt, max_new_tokens):
            return {'text': self.answers.pop(0)}

    def test_fallback_keeps_asset_with_empty_attribute_view(self):
        good = json.dumps({'asset_class': 'equity', 'sector': 'energy', 'region': 'global',
                           'currency': 'usd'})
        attrs, texts, failures = ae.extract_attributes(
            {'A': '{}', 'B': '{}'}, self.Stub([good, 'not json']), on_invalid='fallback')
        self.assertEqual(texts['B'], '')
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]['asset_id'], 'B')

    def test_error_policy_raises(self):
        with self.assertRaises(ValueError):
            ae.extract_attributes({'A': '{}'}, self.Stub(['bad']), on_invalid='error')


class RuleTests(unittest.TestCase):
    def test_greek_stock(self):
        src = {'category': 'Stock', 'subcategory': 'unknown', 'sector': 'Consumer Cyclical',
               'industry': 'Textile Manufacturing', 'market': 'XATH', 'name': 'A S.A. (CR)'}
        self.assertEqual(ae.rule_attributes(src), {'asset_class': 'equity',
                         'sector': 'consumer_discretionary', 'region': 'greece',
                         'currency': 'unknown'})

    def test_fund_region_unknown_and_currency_from_name(self):
        src = {'category': 'MTF', 'subcategory': 'Bond', 'sector': 'unknown',
               'industry': 'unknown', 'market': 'CCLX', 'name': 'X Fund - Yield USD'}
        r = ae.rule_attributes(src)
        self.assertEqual((r['asset_class'], r['region'], r['currency']),
                         ('fixed_income', 'unknown', 'usd'))

    def test_rule_values_are_in_schema(self):
        src = {'category': 'Bond', 'subcategory': 'Government', 'sector': 'Sovereign',
               'industry': 'unknown', 'market': 'HDAT', 'name': 'Hellenic Republic'}
        r = ae.rule_attributes(src)
        self.assertEqual(r['sector'], 'government')
        for key, value in r.items():
            self.assertIn(value, ae.SCHEMA[key])


if __name__ == '__main__':
    unittest.main()
