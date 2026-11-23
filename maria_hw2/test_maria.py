import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

class TestMariaAnalysis(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.run_dir = self.temp_dir / 'run'
        self.run_dir.mkdir()

        self.assets = {
            'A1': {'name': 'Asset1', 'sector': 'Fin', 'industry': 'Bank', 'timestamp': '2021-01-01'},
            'A2': {'name': 'Asset2', 'sector': '', 'industry': '', 'timestamp': '2021-02-01'},
            'A3': {'name': 'Asset3', 'sector': 'Tech', 'industry': 'unknown', 'timestamp': '2021-03-01'},
            'A4': {'name': 'Asset4', 'sector': 'Fin', 'industry': 'Bank', 'timestamp': '2021-04-01'},
        }

        self.history = {f"U{i}": {'A1': 1} for i in range(4, 101)}
        self.history['U1'] = {'A1': 1, 'A2': 1}
        self.history['U2'] = {'A2': 1}
        self.history['U3'] = {'A1': 1, 'A3': 1, 'A4': 1}

        self.truth = {}

        class MockEncoder:
            @staticmethod
            def source_text(meta):
                return f"SOURCE_{meta['name']}"
            @staticmethod
            def paraphrase_prompt(source):
                return f"PROMPT_{source.replace('SOURCE_', '')}"
        self.mock_encoder = MockEncoder()

        prompts_data = []
        for aid, meta in self.assets.items():
            source = self.mock_encoder.source_text(meta)
            prompt = self.mock_encoder.paraphrase_prompt(source)
            prompts_data.append({"asset_id": aid, "prompt": prompt})
        with open(self.run_dir / 'encoder_prompts.jsonl', 'w') as f:
            for p in prompts_data:
                f.write(json.dumps(p) + '\n')

        all_users = [f"U{i}" for i in range(1, 101)]
        self.manifest = {"users": all_users}
        with open(self.run_dir / 'run_manifest.json', 'w') as f:
            json.dump(self.manifest, f)

        self.per_user_data = []
        for i in range(1, 101):
            uid = f"U{i}"
            if uid == 'U1':
                self.per_user_data.append({"user_id": uid, "method": "original_text_cbf", "relevant_count": 1, "ndcg_at_10": 0.1})
                self.per_user_data.append({"user_id": uid, "method": "llmrec_encoder", "relevant_count": 1, "ndcg_at_10": 0.2})
            elif uid == 'U2':
                self.per_user_data.append({"user_id": uid, "method": "original_text_cbf", "relevant_count": 0, "ndcg_at_10": 0.0})
                self.per_user_data.append({"user_id": uid, "method": "llmrec_encoder", "relevant_count": 0, "ndcg_at_10": 0.0})
            elif uid == 'U3':
                self.per_user_data.append({"user_id": uid, "method": "original_text_cbf", "relevant_count": 1, "ndcg_at_10": 0.3})
                self.per_user_data.append({"user_id": uid, "method": "llmrec_encoder", "relevant_count": 1, "ndcg_at_10": 0.4})
            else:
                self.per_user_data.append({"user_id": uid, "method": "original_text_cbf", "relevant_count": 0, "ndcg_at_10": 0.0})
                self.per_user_data.append({"user_id": uid, "method": "llmrec_encoder", "relevant_count": 0, "ndcg_at_10": 0.0})
        with open(self.run_dir / 'per_user.json', 'w') as f:
            json.dump(self.per_user_data, f)

    @patch('analyze_maria.load_course_data')
    @patch('analyze_maria.load_encoder_module')
    def test_subgroup_aggregation(self, mock_load_encoder, mock_load_data):
        from analyze_maria import analyze_subgroups

        mock_load_data.return_value = (self.assets, {}, self.history, self.truth, None, [])
        mock_load_encoder.return_value = self.mock_encoder

        results_md = analyze_subgroups('/fake/data', '/fake/course', str(self.run_dir), '2021-06-01')

        self.assertIn("Total target users evaluated: 100", results_md)
        self.assertIn("Users with non-empty ground truth: 2", results_md)

        self.assertIn("| len_1 | 98 | 0 | original_text_cbf |", results_md)
        self.assertIn("| len_2_3 | 2 | 2 | original_text_cbf | 0.2000 | 0.2000 |", results_md)
        self.assertIn("| len_2_3 | 2 | 2 | **llmrec_encoder** | 0.3000 | 0.3000 |", results_md)

        self.assertIn("| meta_both | 97 | 0 | original_text_cbf |", results_md)
        self.assertIn("| meta_none | 1 | 0 | original_text_cbf | 0.0000 | 0.0000 |", results_md)
        self.assertIn("| meta_mixed | 2 | 2 | original_text_cbf | 0.2000 | 0.2000 |", results_md)

        self.assertIn("✅ PASSED", results_md)

    @patch('analyze_maria.load_course_data')
    @patch('analyze_maria.load_encoder_module')
    def test_missing_method_raises_error(self, mock_load_encoder, mock_load_data):
        from analyze_maria import analyze_subgroups

        mock_load_data.return_value = (self.assets, {}, self.history, self.truth, None, [])
        mock_load_encoder.return_value = self.mock_encoder

        bad_per_user = [e for e in self.per_user_data if not (e['user_id'] == 'U1' and e['method'] == 'llmrec_encoder')]
        with open(self.run_dir / 'per_user.json', 'w') as f:
            json.dump(bad_per_user, f)

        with self.assertRaises(ValueError) as ctx:
            analyze_subgroups('/fake/data', '/fake/course', str(self.run_dir), '2021-06-01')
        self.assertIn("U1", str(ctx.exception))
        self.assertIn("llmrec_encoder", str(ctx.exception))

    @patch('analyze_maria.load_course_data')
    @patch('analyze_maria.load_encoder_module')
    def test_user_outside_manifest_excluded(self, mock_load_encoder, mock_load_data):
        from analyze_maria import analyze_subgroups

        mock_load_data.return_value = (self.assets, {}, self.history, self.truth, None, [])
        mock_load_encoder.return_value = self.mock_encoder

        self.history['U999'] = {'A1': 1}
        self.per_user_data.append({"user_id": "U999", "method": "original_text_cbf", "relevant_count": 1, "ndcg_at_10": 0.5})
        self.per_user_data.append({"user_id": "U999", "method": "llmrec_encoder", "relevant_count": 1, "ndcg_at_10": 0.6})
        with open(self.run_dir / 'per_user.json', 'w') as f:
            json.dump(self.per_user_data, f)

        results_md = analyze_subgroups('/fake/data', '/fake/course', str(self.run_dir), '2021-06-01')

        self.assertIn("Total target users evaluated: 100", results_md)
        self.assertIn("| len_1 | 98 | 0 | original_text_cbf |", results_md)

if __name__ == '__main__':
    unittest.main()